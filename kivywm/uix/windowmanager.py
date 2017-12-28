'''
Window manager
==============

The kivy window manager is a compositing window manager that exposes an
interface for creating Kivy widgets from X windows, which can be sized and
positioned according to kivy layouts.

'''

from kivy.graphics import Color, Rectangle
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.properties import DictProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock

import select
import sys

try:
    import Xlib.display
    import Xlib.error
    import Xlib.protocol.event
    import Xlib.X
    from Xlib.ext.composite import RedirectAutomatic
except ModuleNotFoundError:
    Logger.warning('WindowMgr: Unable to import Xlib, please install it with "pip install python-xlib"')

SUPPORTED_WINDOW_PROVIDERS = ['WindowX11', 'WindowSDL']
X_EVENT_POLL_RATE = 15

class XWindow(Widget):
    __events__ = [
        'on_window_map',
        'on_window_resize',
        'on_window_unmap',
        'on_window_destroy',
    ]

    def __init__(self, manager, window, **kwargs):
        super(XWindow, self).__init__(**kwargs)

        self.manager = manager

        self.texture = None
        self.pixmap = None
        self._window = window

        self.render_loop = None

        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

    @property
    def name(self):
        return self._window.get_wm_name()

    def on_size(self, *args):
        Logger.info(f'Resized window: {self.name}, size: {self.size}')
        self._window.configure(
            width=round(self.width),
            height=round(self.height),
        )

        self.invalidate_pixmap()

    def on_parent(self, *args):
        if self.parent:
            self._window.map()
            self.invalidate_pixmap()
            self.start_render_loop()
        else:
            self.stop_render_loop()
            self._window.unmap()

    def on_window_map(self):
        self.invalidate_pixmap()

    def on_window_resize(self):
        self.invalidate_pixmap()

    def on_window_unmap(self):
        Logger.debug(f'{self.name}: Window unmapped')
        self.stop_render_loop()

    def on_window_destroy(self):
        self.stop_render_loop()
        self.release_texture()
        self.release_pixmap()

    def create_pixmap(self):
        if not self.pixmap:
            self.pixmap = self._window.composite_name_window_pixmap()
            self.manager.display.sync()

    def release_pixmap(self):
        if self.pixmap:
            self.pixmap.free()
            self.pixmap = None

    def create_texture(self):
        self.create_pixmap()

        from kivywm.graphics.texture import Texture

        if not self.texture:
            geom = self._window.get_geometry()
            self.texture = Texture.create_from_pixmap(self.pixmap.id, (geom.width, geom.height))

    def release_texture(self):
        if self.texture:
            self.texture.release_pixmap()
            del self.texture
            self.texture = None

    def invalidate_pixmap(self):
        rendering = self.render_loop is not None
        self.stop_render_loop()

        self.release_texture()
        self.release_pixmap()
        self.create_texture()

        if rendering:
            self.start_render_loop()

    def redraw(self, *args):
        self.rect.texture = self.texture
        self.rect.size = self.texture.size
        self.rect.pos = self.pos

    def start_render_loop(self):
        self.render_loop = Clock.schedule_interval(
            lambda dt: self.redraw(), 0
        )

    def stop_render_loop(self):
        if self.render_loop:
            self.render_loop.cancel()
            self.render_loop = None

class BaseWindowManager(EventDispatcher):
    event_mapping = {
            'CreateNotify': 'on_create_notify',
            'DestroyNotify': 'on_destroy_notify',
            'UnmapNotify': 'on_unmap_notify',
            'MapNotify': 'on_map_notify',
            'UnmapNotify': 'on_unmap_notify',
            'MappingNotify': 'on_mapping_notify',
            'MapRequest': 'on_map_request',
            'ReparentNotify': 'on_reparent_notify',
            'ConfigureNotify': 'on_configure_notify',
            'ConfigureRequest': 'on_configure_request',
        }

    display = None
    is_active = None

    root_window = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super(BaseWindowManager, self).__init__(*args, **kwargs)

        # Convert event strings to X protocol values
        self.event_mapping = {
            getattr(Xlib.X, event): handler
            for event, handler in self.event_mapping.items()
        }

        [self.register_event_type(event)
            for event in self.event_mapping.values()]

        self.connect()
        self._set_root_window()

    def connect(self):
        try:
            self.display = Xlib.display.Display()
        except Xlib.error.DisplayConnectionError:
            Logger.error('WindowMgr: Unable to connect to X server')
            raise

    def _set_root_window(self):
        from kivy.app import App
        app = App.get_running_app()

        window = app.root_window

        if window.__class__.__name__ not in SUPPORTED_WINDOW_PROVIDERS:
            Logger.error(f'WindowMgr: Unsupported window provider: {window.__class__.__name__}')
            return

        self.root_window = window

    def on_root_window(self, instance, window):
        self.setup_wm()
        self.event_handler = Clock.schedule_interval(
            lambda dt: self.poll_events(),
            1.0 / X_EVENT_POLL_RATE
        )

    def is_kivy_win(self, window):
        window_info = self.root_window.get_window_info()

        if sys.platform == 'linux':
            from kivy.core.window.window_info import WindowInfoX11
            if isinstance(window_info, WindowInfoX11):
                return window_info.window == window.id

        return False

    def setup_wm(self, *args):
        self.root_win = self.display.screen().root

        event_mask = Xlib.X.SubstructureNotifyMask \
                   | Xlib.X.SubstructureRedirectMask

        ec = Xlib.error.CatchError(Xlib.error.BadAccess)
        self.root_win.change_attributes(event_mask=event_mask, onerror=ec)
        self.display.sync()

        self.is_active = not ec.get_error()
        if not self.is_active:
            Logger.warning('WindowMgr: Unable to create window manager, another one is running')

    def poll_events(self):
        if self.is_active is not None and not self.is_active:
            return False

        readable, w, e = select.select([self.display], [], [], 0)

        if not readable:
            return
        elif self.display in readable:
            num_events = self.display.pending_events()
            for i in range(num_events):
                self.handle_event(self.display.next_event())

    def handle_event(self, event):
        handler = self.event_mapping.get(event.type)
        if not handler:
            Logger.warning(f'WindowMgr: received event for which there is no handler ({event.type})')
            return
        try:
            self.dispatch(handler, event)
        except Xlib.error.BadWindow:
            # TODO: Handle BadWindow
            pass

    def on_create_notify(self, event):
        pass

    def on_destroy_notify(self, event):
        pass

    def on_unmap_notify(self, event):
        pass

    def on_map_notify(self, event):
        pass

    def on_mapping_notify(self, event):
        pass

    def on_map_request(self, event):
        pass

    def on_reparent_notify(self, event):
        pass

    def on_configure_notify(self, event):
        pass

    def on_configure_request(self, event):
        pass


class CompositingWindowManager(BaseWindowManager):
    required_extensions = ['Composite']

    def check_extensions(self, extensions):
        for extension in extensions:
            if self.display.has_extension(extension):
                Logger.info('WindowMgr: has extension {}'.format(extension))
            else:
                Logger.error('WindowMgr: no support for extension {}'.format(extension))

    def setup_wm(self, *args):
        self.check_extensions(self.required_extensions)

        super(CompositingWindowManager, self).setup_wm()

        if not self.is_active:
            return

        self.root_win.composite_redirect_subwindows(RedirectAutomatic)
        self.overlay_win = self.root_win.composite_get_overlay_window().overlay_window
        self.display.sync()

        for window in self.root_win.query_tree().children:
            if self.is_kivy_win(window):
                Logger.info('WindowMgr: Found kivy window')
                window.reparent(self.overlay_win, x=0, y=0)
                window.map()
                self.display.sync()
                break


class KivyWindowManager(CompositingWindowManager):
    windows = DictProperty([])
    window_callbacks = DictProperty({'name': {}, 'id': {}})

    def _add_child(self, window):
        ''' Creates an XWindow object that can be retrieved and used as a widget by the main app
        '''
        if window.id not in self.windows:
            self.windows[window.id] = XWindow(self, window)

        default_window_callback = self.window_callbacks.get(None)
        if default_window_callback:
            default_window_callback(self.windows[window.id])

        id_callback = self.window_callbacks['id'].get(window.id)
        if id_callback:
            id_callback(self.windows[window.id])

        name_callback = self.window_callbacks['name'].get(window.get_wm_name())
        if name_callback:
            name_callback(self.windows[window.id])

    def _remove_child(self, window):
        ''' Remove a child window
        '''
        if window.id in self.windows:
            del self.windows[window.id]

    def add_window_callback(self, cb, name=None, id=None):
        if name:
            self.window_callbacks['name'][name] = cb
        elif id:
            self.window_callbacks['id'][id] = cb
        else:
            self.window_callbacks[None] = cb

    def get_window_by_name(self, name):
        for xid, window in self.windows.items():
            if window.get_wm_name() == name:
                return window
        return None

    def get_window_by_xid(self, xid):
        return self.windows.get(xid)

    def on_create_notify(self, event):
        # Don't create a child for the Kivy window
        if self.is_kivy_win(event.window):
            return

        self._add_child(event.window)

        Logger.info(f'Created window: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_create_notify(event)

    def on_destroy_notify(self, event):
        Logger.info(f'Destroyed window: {event}')
        if event.window.id in self.windows:
            window = self.windows.pop(event.window.id)
            window.dispatch('on_window_destroy')
        super(KivyWindowManager, self).on_destroy_notify(event)

    def on_unmap_notify(self, event):
        Logger.info(f'Unmap notify: {event}')
        if event.window.id in self.windows:
            self.windows[event.window.id].dispatch('on_window_unmap')
        super(KivyWindowManager, self).on_unmap_notify(event)

    def on_map_notify(self, event):
        if event.window.id in self.windows:
            self.windows[event.window.id].dispatch('on_window_map')

        Logger.info(f'Map notify: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_notify(event)

    def on_mapping_notify(self, event):
        Logger.info(f'Mapping notify: {event}')

    def on_map_request(self, event):
        Logger.info(f'Map request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_request(event)

    def on_reparent_notify(self, event):
        Logger.info(f'Reparented window: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_notify(event)

    def on_reparent_request(self, event):
        Logger.info(f'Reparent request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_request(event)

    def on_configure_notify(self, event):
        if event.window.id in self.windows:
            # TODO: Check if the window was actually resized
            self.windows[event.window.id].dispatch('on_window_resize')

        Logger.info(f'Configure notify: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_notify(event)

    def on_configure_request(self, event):
        Logger.info(f'Configure request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_request(event)

