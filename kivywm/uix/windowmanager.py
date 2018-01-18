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
from kivy.properties import DictProperty, ObjectProperty, BooleanProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock

import array
import weakref
import select
import sys

try:
    import Xlib.display
    import Xlib.error
    import Xlib.protocol.event
    import Xlib.X
    import Xlib.Xatom
    from Xlib.ext.composite import RedirectAutomatic
except ModuleNotFoundError:
    Logger.warning('WindowMgr: Unable to import Xlib, please install it with "pip install python-xlib"')

SUPPORTED_WINDOW_PROVIDERS = ['WindowX11', 'WindowSDL']

class XWindow(Widget):
    __events__ = [
        'on_window_map',
        'on_window_resize',
        'on_window_unmap',
        'on_window_destroy',
    ]

    active = BooleanProperty(False)

    def __init__(self, manager, window, **kwargs):
        super(XWindow, self).__init__(**kwargs)

        self.manager = manager

        self.texture = None
        self.pixmap = None
        self._window = window

        self.draw_event = None

        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

    def __repr__(self):
        if hasattr(self, '_window') and self._window is not None:
            return f'<{self.__class__.__name__} id: {hex(self.xid)} name: "{self.name}">'
        else:
            return f'<{self.__class__.__name__} (No Window Bound)>'

    def on_active(self, *args):
        if self.active:
            if not self.draw_event:
                self.draw_event = Clock.schedule_interval(lambda dt: self.canvas.ask_update(), 1 / 60)
        else:
            if self.draw_event:
                self.draw_event.cancel()
            self.draw_event = None

    @property
    def xid(self):
        if self._window:
            return self._window.id
        else:
            return None

    @property
    def name(self):
        if self._window:
            return self._window.get_wm_name()
        else:
            return None

    def on_size(self, *args):
        Logger.trace(f'WindowMgr: {self}: on_size: {self.size}')
        self._window.configure(
            width=round(self.width),
            height=round(self.height),
        )

        self.invalidate_pixmap()

    def on_parent(self, *args):
        Logger.trace(f'WindowMgr: {self}: on_parent: {self.parent}')
        if self.parent:
            self._window.map()
            self.invalidate_pixmap()
            self.active = True
        else:
            self.active = False
            self._window.unmap()
            self.release_pixmap()
            self.release_texture()
            self.canvas.clear()
            self.rect = None

    def on_window_map(self):
        Logger.trace(f'WindowMgr: {self}: on_window_map')
        self.invalidate_pixmap()

    def on_window_resize(self):
        Logger.trace(f'WindowMgr: {self}: on_window_resize')
        self.invalidate_pixmap()

    def on_window_unmap(self):
        Logger.trace(f'WindowMgr: {self}: on_window_unmap')
        self.active = False

    def on_window_destroy(self):
        Logger.trace(f'WindowMgr: {self}: on_window_destroy')
        self.active = False
        self.release_texture()
        self.release_pixmap()
        self._window = None

    def create_pixmap(self):
        if not self.pixmap:
            self.pixmap = self._window.composite_name_window_pixmap()
            self.manager.display.sync()
            Logger.trace(f'WindowMgr: {self}: created pixmap')

    def release_pixmap(self):
        if self.pixmap:
            self.pixmap.free()
            self.pixmap = None
            Logger.trace(f'WindowMgr: {self}: released pixmap')

    def create_texture(self):
        self.create_pixmap()

        from kivywm.graphics.texture import Texture

        if not self.texture:
            geom = self._window.get_geometry()
            self.texture = Texture.create_from_pixmap(self.pixmap.id, (geom.width, geom.height))
            self.rect.texture = self.texture
            self.rect.size = self.texture.size
            self.rect.pos = self.pos
            Logger.trace(f'WindowMgr: {self}: created texture')

    def release_texture(self):
        if self.texture:
            self.texture.release_pixmap()
            del self.texture
            self.texture = None
            Logger.trace(f'{self}: WindowMgr: released texture')

    def invalidate_pixmap(self):
        Logger.trace(f'WindowMgr: {self}: invalidate pixmap')
        self.active = False

        self.release_texture()
        self.release_pixmap()
        self.create_texture()

        self.active = True

class BaseWindowManager(EventDispatcher):
    event_mapping = {
            'ClientMessage': 'on_client_message',
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

    app_window = ObjectProperty(None)

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
        self._set_app_window()

    def connect(self):
        try:
            self.display = Xlib.display.Display()
            Logger.info(f'WindowMgr: Connected to display: {self.display.get_display_name()}')
        except Xlib.error.DisplayConnectionError:
            Logger.error('WindowMgr: Unable to connect to X server')
            raise

    def _set_app_window(self):
        from kivy.app import App
        app = App.get_running_app()

        window = app.root_window

        if window.__class__.__name__ not in SUPPORTED_WINDOW_PROVIDERS:
            Logger.error(f'WindowMgr: Unsupported window provider: {window.__class__.__name__}')
            return

        self.app_window = window

    def on_app_window(self, instance, window):
        self.event_handler = Clock.schedule_interval(
            lambda dt: self.poll_events(), 0)

        self.setup_wm()

        xwin = self.display.create_resource_object(
            'window', self.app_window_info().window
        )

        root_geom = self.root_win.get_geometry()
        xwin.configure(width=root_geom.width, height=root_geom.height)

    def app_window_info(self):
        if not self.app_window:
            return

        window_info = self.app_window.get_window_info()

        from kivy.core.window.window_info import WindowInfoX11
        if isinstance(window_info, WindowInfoX11):
            return window_info

    def setup_wm(self, *args):
        self.root_win = self.display.screen().root
        Logger.debug(f'WindowMgr: acquired root window: {self.root_win}')

        event_mask = Xlib.X.SubstructureNotifyMask \
                   | Xlib.X.SubstructureRedirectMask

        ec = Xlib.error.CatchError(Xlib.error.BadAccess)
        self.root_win.change_attributes(event_mask=event_mask, onerror=ec)
        self.display.sync()

        self.is_active = not ec.get_error()
        if not self.is_active:
            Logger.warning('WindowMgr: Unable to create window manager, another one is running')
            return

        app_window_info = self.app_window_info()
        app_window = self.display.create_resource_object('window', app_window_info.window)

        net_supporting_wm_check = self.display.intern_atom('_NET_SUPPORTING_WM_CHECK')
        self.root_win.change_property(net_supporting_wm_check, Xlib.Xatom.WINDOW, 32, array.array('I', [app_window.id]))
        app_window.change_property(net_supporting_wm_check, Xlib.Xatom.WINDOW, 32, array.array('I', [app_window.id]))

        net_supported = self.display.intern_atom('_NET_SUPPORTED')
        supported_hints = array.array('I',
            [self.display.intern_atom(atom) for atom in [
                '_NET_WM_STATE',
                '_NET_WM_STATE_FOCUSED',
                '_NET_WM_STATE_MAXIMIZED_VERT',
                '_NET_WM_STATE_MAXIMIZED_HORIZ',
                '_NET_WM_STATE_FULLSCREEN',
                '_NET_WM_STATE_ABOVE',
                '_NET_WM_STATE_SKIP_TASKBAR',
                '_NET_WM_STATE_SKIP_PAGER',
                '_NET_WM_STATE_MODAL',
                '_NET_WM_STATE_STICKY',
                '_NET_WM_STATE_HIDDEN',
            ]]
        )

        self.root_win.change_property(net_supported, Xlib.Xatom.ATOM, 32, supported_hints)

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

    def on_client_message(self, event):
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
                Logger.debug('WindowMgr: has extension {}'.format(extension))
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

        Logger.debug(f'WindowMgr: created composite overlay window: {self.overlay_win}')

        self.reparent_app_window()

    def reparent_app_window(self):
        window_info = self.app_window_info()
        if not window_info:
            Logger.error(f'WindowMgr: window_info is invalid: {window_info}')
            sys.exit(1)

        kivy_win = self.display.create_resource_object('window', window_info.window)
        Logger.debug(f'WindowMgr: app window: {kivy_win}')
        kivy_win.reparent(self.overlay_win, x=0, y=0)
        self.display.sync()

class KivyWindowManager(CompositingWindowManager):
    __events__ = ('on_window_create',)

    window_refs = DictProperty({})

    def _add_child(self, window):
        ''' Creates an XWindow object that can be retrieved and used as a widget by the main app
        '''
        if window.id not in self.window_refs:
            window_widget = XWindow(self, window)
            self.window_refs[window.id] = weakref.ref(window_widget)
            self.dispatch('on_window_create', window_widget)

    def on_window_create(self, window):
        pass

    def get_window(self, name=None, xid=None):
        if name:
            for xid, ref in self.window_refs.items():
                window = ref()
                if not window:
                    continue

                if window.get_wm_name() == name:
                    return window

        if xid:
            window = self.window_refs.get(xid)
            if window:
                return window()

    def on_client_message(self, event):
        Logger.debug(f'WindowMgr: client message: {event}, atom: {self.display.get_atom_name(event.type)},\
                client_type: {self.display.get_atom_name(event.client_type)}')
        super(KivyWindowManager, self).on_client_message(event)

    def on_create_notify(self, event):
        # Don't create a child for the Kivy window, or overlay
        window_info = self.app_window_info()
        if window_info and window_info.window == event.window.id:
            return

        if event.window == self.overlay_win:
            return

        self._add_child(event.window)

        Logger.debug(f'WindowMgr: window created: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_create_notify(event)

    def on_destroy_notify(self, event):
        Logger.debug(f'WindowMgr: window destroyed: {event}')
        ref = self.window_refs.pop(event.window.id, None)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_destroy')
        super(KivyWindowManager, self).on_destroy_notify(event)

    def on_unmap_notify(self, event):
        Logger.debug(f'WindowMgr: window unmapped: {event}')
        ref = self.window_refs.get(event.window.id)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_unmap')
        super(KivyWindowManager, self).on_unmap_notify(event)

    def on_map_notify(self, event):
        ref = self.window_refs.get(event.window.id)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_map')

        Logger.debug(f'WindowMgr: window mapped: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_notify(event)

    def on_mapping_notify(self, event):
        Logger.debug(f'WindowMgr: mapping notify: {event}')

    def on_map_request(self, event):
        Logger.debug(f'WindowMgr: map request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_request(event)

    def on_reparent_notify(self, event):
        Logger.debug(f'WindowMgr: window reparented: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_notify(event)

    def on_reparent_request(self, event):
        Logger.debug(f'WindowMgr: reparent request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_request(event)

    def on_configure_notify(self, event):
        # TODO: Check if the window was actually resized
        ref = self.window_refs.get(event.window.id)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_resize')

        Logger.debug(f'WindowMgr: window configured: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_notify(event)

    def on_configure_request(self, event):
        Logger.debug(f'WindowMgr: configure request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_request(event)

