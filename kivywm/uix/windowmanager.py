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
from kivy.properties import DictProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock

import array
import weakref
import select
import subprocess
import sys
import os

os.environ['SDL_VIDEO_X11_LEGACY_FULLSCREEN'] = '0'

try:
    import Xlib.display
    import Xlib.error
    import Xlib.protocol.event
    import Xlib.X
    import Xlib.Xatom
    from Xlib.ext.composite import RedirectAutomatic
    from Xlib.ext import randr
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
    invalidate_pixmap = BooleanProperty(False)
    pixmap = ObjectProperty(None, allownone=True)
    refresh_rate = NumericProperty()
    texture = ObjectProperty(None, allownone=True)

    def __init__(self, manager, window=None, **kwargs):
        super(XWindow, self).__init__(**kwargs)

        self.manager = manager

        if window:
            self._window = window
        else:
            self._window = manager.root_win.create_window(
                x=0, y=0,
                width=self.width, height=self.height,
                depth=24, border_width=0
            )

        with self.canvas:
            self.rect = Rectangle(size=self.size, pos=self.pos)

        refresh_hz = int(os.environ.get('KIVYWM_REFRESH_HZ', 60))
        self.refresh_rate = 1 / refresh_hz if refresh_hz > 0 else 0

    def __repr__(self):
        if hasattr(self, '_window') and self._window is not None:
            return f'<{self.__class__.__name__} id: {hex(self.id)} name: "{self.name}">'
        else:
            return f'<{self.__class__.__name__} (No Window Bound)>'

    def focus(self):
        self._win.set_input_focus(
            revert_to=Xlib.X.RevertToParent, time=Xlib.X.CurrentTime)

    def redraw(self, *args):
        self.canvas.ask_update()
        return self.active

    def on_invalidate_pixmap(self, *args):
        if not self.invalidate_pixmap:
            return

        try:
            self.release_texture()
            self.release_pixmap()
            self.create_pixmap()
            self.create_texture()
        except (Xlib.error.BadDrawable, Xlib.error.BadWindow, KeyboardInterrupt):
            self.active = False

        self.invalidate_pixmap = False

    def on_active(self, *args):
        if self.active:
            Clock.schedule_interval(self.redraw, self.refresh_rate)
        else:
            self.release_texture()
            self.release_pixmap()

    def on_pos(self, instance, value):
        self.rect.pos = value

    def start(self, *args):
        self.active = True

    def stop(self, *args):
        self.active = False

    def destroy(self, *args):
        self._window.destroy()

    @property
    def id(self):
        try:
            return self._window.id
        except AttributeError:
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

        self.invalidate_pixmap = True

    def on_parent(self, *args):
        Logger.trace(f'WindowMgr: {self}: on_parent: {self.parent}')
        if self.parent:
            self._window.map()
            self.invalidate_pixmap = True
            self.start()
        else:
            self.stop()

    def on_window_map(self):
        Logger.trace(f'WindowMgr: {self}: on_window_map')
        self.invalidate_pixmap = True

    def on_window_resize(self):
        Logger.trace(f'WindowMgr: {self}: on_window_resize')
        self.invalidate_pixmap = True

    def on_window_unmap(self):
        Logger.trace(f'WindowMgr: {self}: on_window_unmap')
        self.stop()

    def on_window_destroy(self):
        Logger.trace(f'WindowMgr: {self}: on_window_destroy')
        self.stop()
        self.canvas.clear()
        self._window = None

    def create_pixmap(self):
        ec = Xlib.error.CatchError(Xlib.error.BadMatch)

        if not self.pixmap:
            self.pixmap = self._window.composite_name_window_pixmap(onerror=ec)
            self.manager.display.sync()
            Logger.trace(f'WindowMgr: {self}: created pixmap')

        if ec.get_error():
            self.pixmap = None

    def release_pixmap(self):
        if self.pixmap:
            self.pixmap.free()
            self.pixmap = None
            Logger.trace(f'WindowMgr: {self}: released pixmap')

    def create_texture(self):
        from kivywm.graphics.texture import Texture

        if self.pixmap and not self.texture:
            geom = self._window.get_geometry()
            self.texture = Texture.create_from_pixmap(self.pixmap.id, (geom.width, geom.height))
            self.rect.texture = self.texture
            self.rect.size = self.texture.size

    def release_texture(self):
        if self.texture:
            self.texture.release_pixmap()
            self.texture = None

class BaseWindowManager(EventDispatcher):
    event_mapping = {
            'KeyPress': 'on_key_press',
            'KeyRelease': 'on_key_release',
            'MotionNotify': 'on_motion',
            'ButtonPress': 'on_button_press',
            'ButtonRelease': 'on_button_release',
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
            # RandR Events
            'ScreenChangeNotify': 'on_screen_change_notify',
            'CrtcChangeNotify': 'on_crtc_change_notify',
            'OutputChangeNotify': 'on_output_change_notify',
            'OutputPropertyNotify': 'on_output_property_notify',
        }

    display = None
    is_active = None

    app_window = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super(BaseWindowManager, self).__init__(*args, **kwargs)
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
        self.poll_events()
        self.setup_wm()

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

        self.set_cursor()

        event_mask = Xlib.X.SubstructureNotifyMask \
                   | Xlib.X.SubstructureRedirectMask

        ec = Xlib.error.CatchError(Xlib.error.BadAccess)
        self.root_win.change_attributes(event_mask=event_mask, onerror=ec)

        self.root_win.xrandr_select_input(
            randr.RRScreenChangeNotifyMask
            | randr.RRCrtcChangeNotifyMask
            | randr.RROutputChangeNotifyMask
            | randr.RROutputPropertyNotifyMask
        )

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

    def get_screen_sizes(self):
        return self.root_win.xrandr_get_screen_info().sizes

    def set_screen_size(self, size_id, rotation='preserve'):
        if rotation == 'normal':
            rotation = 1
        elif rotation == 'right':
            rotation = 2
        elif rotation == 'inverted':
            rotation = 4
        elif rotation == 'left':
            rotation = 8
        else:
            rotation = None

        screen_info = self.root_win.xrandr_get_screen_info()
        if not rotation:
            rotation = screen_info.rotation

        res = self.root_win.xrandr_1_0set_screen_config(
            size_id=size_id,
            rotation=rotation,
            config_timestamp=screen_info.config_timestamp,
        )

        app_window_info = self.app_window_info()
        app_window = self.display.create_resource_object(
                'window', app_window_info.window)

        size = screen_info.sizes[size_id]

        # update the app window size immediately
        app_window.configure(
            width=size['width_in_pixels'], height=size['height_in_pixels'])

    def set_cursor(self, name='left_ptr'):
        p = subprocess.Popen(['xsetroot', '-cursor_name', name])
        p.communicate()

    def show_cursor(self, show=True):
        from kivy.core.window import Window
        Window.show_cursor = show

    poll_before_frame = False
    def poll_events(self, *args):
        if self.is_active:
            readable, w, e = select.select([self.display], [], [], 0)

            if readable and self.display in readable:
                num_events = self.display.pending_events()
                for i in range(num_events):
                    self.handle_event(self.display.next_event())

        self.poll_before_frame = not self.poll_before_frame
        Clock.schedule_once(self.poll_events, -1 if self.poll_before_frame else 0)

    def handle_event(self, event):
        handler = self.event_mapping.get(event.__class__.__name__)
        if not handler:
            Logger.warning(f'WindowMgr: received event for which there is no handler <{event.__class__.__name__}> ({event.type})')
            return
        try:
            self.dispatch(handler, event)
        except Xlib.error.BadWindow:
            # TODO: Handle BadWindow
            pass

    def on_key_press(self, event):
        event.window.send_event(event)

    def on_key_release(self, event):
        event.window.send_event(event)

    def on_motion(self, event):
        event.window.send_event(event)

    def on_button_press(self, event):
        event.window.send_event(event)

    def on_button_release(self, event):
        event.window.send_event(event)

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

    # RandR Events
    def on_screen_change_notify(self, event):
        pass

    def on_crtc_change_notify(self, event):
        pass

    def on_output_change_notify(self, event):
        pass

    def on_output_property_notify(self, event):
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

        kivy_win.map()
        self.display.sync()

        status = kivy_win.grab_keyboard(
            owner_events=False,
            pointer_mode=Xlib.X.GrabModeAsync,
            keyboard_mode=Xlib.X.GrabModeAsync,
            time=Xlib.X.CurrentTime
        )

    def on_screen_change_notify(self, event):
        super(CompositingWindowManager, self).on_screen_change_notify(event)
        app_window_info = self.app_window_info()
        app_window = self.display.create_resource_object(
                'window', app_window_info.window)

        screen_info = self.root_win.xrandr_get_screen_info()
        size = screen_info.sizes[screen_info.size_id]

        app_window.configure(
            width=size['width_in_pixels'], height=size['height_in_pixels'])

class KivyWindowManager(CompositingWindowManager):
    __events__ = ('on_window_create',)

    window_refs = DictProperty({})

    def stop(self):
        for id, ref in self.window_refs.items():
            window = ref()
            if window:
                window.active = False

    def _add_child(self, window):
        ''' Creates an XWindow object that can be retrieved and used as a widget by the main app
        '''
        if window.id not in self.window_refs:
            window_widget = XWindow(self, window)
            self.window_refs[window.id] = weakref.ref(window_widget)
            self.dispatch('on_window_create', window_widget)

    def on_window_create(self, window):
        pass

    def get_window(self, name=None, id=None):
        if name:
            for id, ref in self.window_refs.items():
                window = ref()
                if not window:
                    continue

                if window.get_wm_name() == name:
                    return window

        if id:
            window = self.window_refs.get(id)
            if window:
                return window()

    def create_window(self):
        window = XWindow(self)
        self.window_refs[window.id] = weakref.ref(window)
        return window

    def on_client_message(self, event):
        Logger.trace(f'WindowMgr: client message: {event}, atom: {self.display.get_atom_name(event.type)},\
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

        Logger.trace(f'WindowMgr: window created: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_create_notify(event)

    def on_destroy_notify(self, event):
        Logger.trace(f'WindowMgr: window destroyed: {event}')
        ref = self.window_refs.pop(event.window.id, None)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_destroy')
        super(KivyWindowManager, self).on_destroy_notify(event)

    def on_unmap_notify(self, event):
        Logger.trace(f'WindowMgr: window unmapped: {event}')
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

        Logger.trace(f'WindowMgr: window mapped: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_notify(event)

    def on_mapping_notify(self, event):
        Logger.trace(f'WindowMgr: mapping notify: {event}')

    def on_map_request(self, event):
        Logger.trace(f'WindowMgr: map request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_map_request(event)

    def on_reparent_notify(self, event):
        Logger.trace(f'WindowMgr: window reparented: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_notify(event)

    def on_reparent_request(self, event):
        Logger.trace(f'WindowMgr: reparent request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_reparent_request(event)

    def on_configure_notify(self, event):
        # TODO: Check if the window was actually resized
        ref = self.window_refs.get(event.window.id)
        window = ref() if ref else None
        if window:
            window.dispatch('on_window_resize')

        Logger.trace(f'WindowMgr: window configured: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_notify(event)

    def on_configure_request(self, event):
        Logger.trace(f'WindowMgr: configure request: {event}, name: {event.window.get_wm_name()}')
        super(KivyWindowManager, self).on_configure_request(event)

    def on_screen_change_notify(self, event):
        Logger.trace('WindowMgr: screen changed: {event}')
        super(KivyWindowManager, self).on_screen_change_notify(event)

    def on_crtc_change_notify(self, event):
        Logger.trace('WindowMgr: CRTC changed: {event}')
        super(KivyWindowManager, self).on_crtc_change_notify(event)

    def on_output_change_notify(self, event):
        Logger.trace('WindowMgr: output changed: {event}')
        super(KivyWindowManager, self).on_output_change_notify(event)

    def on_output_property_notify(self, event):
        Logger.trace('WindowMgr: output property changed: {event}')
        super(KivyWindowManager, self).on_output_property_notify(event)

