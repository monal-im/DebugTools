from PyQt5 import QtCore, QtWidgets
import logging

logger = logging.getLogger(__name__)

class Statusbar():
    def __init__(self, statusbar):
        self.statusbarText = {"static": "", "dynamic": []}
        self.statusbar = statusbar
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update)

    def setText(self, text):
        self.statusbarText["static"] = str(text)
        if not self.timer.isActive():
            self._update()

    def showDynamicText(self, text, time=3000):
        self.statusbarText["dynamic"].append((text, time))
        if not self.timer.isActive():
            self._update()

    def clear(self):
        self.statusbarText["dynamic"].clear()
        self.statusbarText["static"] = ""

    def _update(self):
        static = self.statusbarText["static"]
        dynamic = self.statusbarText["dynamic"]
        if len(dynamic) > 0:
            text, time = dynamic.pop()
            self.statusbar.showMessage(text)
            self.timer.stop()
            self.timer.start(time)
        else:
            self.timer.stop()
            self.statusbar.showMessage(static)

        QtWidgets.QApplication.processEvents()