from kivy.app import App
from kivywm.uix.windowmanager import KivyWindowManager
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.clock import Clock

import subprocess
import time

class WindowManagerApp(App):
    def build(self):
        layout = GridLayout(cols=6)
        layout.add_widget(Label(text='Kivy Window Manager'))
        return layout

    def add_window(self, window):
        self.root.add_widget(window)

    def on_start(self):
        self.window_manager = KivyWindowManager()
        self.window_manager.add_window_callback(self.add_window, name='glxgears')

        for i in range(23):
            p = subprocess.Popen('glxgears')

if __name__ == '__main__':
    WindowManagerApp().run()

