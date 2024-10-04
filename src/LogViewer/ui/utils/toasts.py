from PyQt5 import QtGui, QtWidgets, QtCore

import logging
logger = logging.getLogger(__name__)

class Toast(QtWidgets.QWidget):
    def __init__(self, window):
        super().__init__()
        logger.debug("Create toast...")
        self._createLabel(window)
        
    def displayToast(self, text, time=4000):
        logger.debug("Display label...")
        self.toastLabel.move(QtGui.QCursor.pos().x(), QtGui.QCursor.pos().y())
        self.toastLabel.setText(text)
        self.toastLabel.adjustSize()
        self.toastLabel.show()

        # hide toast
        self.timerTimer = QtCore.QTimer(self)
        self.timerTimer.setSingleShot(True)
        self.timerTimer.timeout.connect(self._hideLabel)
        self.timerTimer.start(time)

    def _createLabel(self, window):
        logger.debug("Create label...")
        self.toastLabel = QtWidgets.QLabel(
                                        window, 
                                        wordWrap=True, 
                                        alignment=QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop
                                    )
        self.toastLabel.setStyleSheet(f"border-radius: 5px; background-color: #5a2bdbee;")
        self.toastLabel.hide()

    def _hideLabel(self):
        logger.debug("Hide toast...")
        self.toastLabel.hide()
        