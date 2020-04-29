from kivy.app import App
from kivywm.uix.windowmanager import KivyWindowManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.clock import Clock

import cProfile
import subprocess
import time

class WindowManagerApp(App):
    def build(self):
        layout = BoxLayout()
        return layout

    def add_window(self, manager, window):
        self.root.add_widget(window)

    def on_start(self):
        self.window_manager = KivyWindowManager()
        self.window_manager.bind(on_window_create=self.add_window)
        self.p = subprocess.Popen('glxgears')
        self.profile = cProfile.Profile()
        self.profile.enable()

    def on_stop(self):
        self.p.kill()
        self.profile.disable()
        self.profile.dump_stats('kivywm.dump')

if __name__ == '__main__':
    app = WindowManagerApp()
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()

