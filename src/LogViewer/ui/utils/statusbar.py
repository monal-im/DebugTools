from PyQt5 import QtCore, QtWidgets, QtGui
from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

class Statusbar(QtCore.QObject):
    def __init__(self, statusbar, menu=None):
        super().__init__()
        self.statusbarText = {"static": "", "dynamic": []}
        self.statusbar = statusbar
        self.menu = menu
        self.dynamic_timer = QtCore.QTimer()
        self.dynamic_timer.stop()
        self.dynamic_timer.timeout.connect(self._dynamicTimedOut)
        if self.menu != None:
            self.menu.installEventFilter(self)
    
    def __del__(self):
        if self.menu != None:
            self.menu.removeEventFilter(self)
        self.dynamic_timer.stop()
    
    def setText(self, text):
        self.statusbarText["static"] = str(text)
        if not self.dynamic_timer.isActive():
            self._update()

    def showDynamicText(self, text, time=3000):
        self.statusbarText["dynamic"].append((text, time))
        if not self.dynamic_timer.isActive():
            self._update()
    
    def clear(self):
        self.statusbarText["dynamic"].clear()
        self.statusbarText["static"] = ""

    def _update(self):
        static = self.statusbarText["static"]
        dynamic = self.statusbarText["dynamic"]
        if len(dynamic) > 0:
            self.dynamic_timer.stop()
            # always display our messages in fifo order but don't pop them off the stack
            # this makes it possible to display them a second time if they got interrupted by displaying a menu entry description
            text, time = dynamic[0]
            self.statusbar.showMessage(text)
            self.dynamic_timer.start(time)
        else:
            self.dynamic_timer.stop()
            self.statusbar.showMessage(static)
        QtWidgets.QApplication.processEvents()
    
    @catch_exceptions(logger=logger)
    def _dynamicTimedOut(self):
        self.dynamic_timer.stop()
        del self.statusbarText["dynamic"][0]      # remove the first entry in our queue (that one did time out)
        self._update()
    
    @catch_exceptions(logger=logger)
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(event, QtGui.QStatusTipEvent):
            if len(event.tip()) > 0:
                if self.dynamic_timer.isActive():
                    assert len(self.statusbarText["dynamic"]) > 0, "Dynamic statusbar text list is empty but the dynamic timer is still running!"
                    # stop timer and update time of currently displayed dynamic entry to resume displaying later on
                    self.statusbarText["dynamic"][0] = (self.statusbarText["dynamic"][0][0], self.dynamic_timer.remainingTime())
                    self.dynamic_timer.stop()
            else:
                # don't show empty status tip, but show normal statusmessage (dynamic, static) instead
                self._update()
                return True
        return False
