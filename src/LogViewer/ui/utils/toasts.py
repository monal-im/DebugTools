from PyQt5 import QtGui, QtWidgets, QtCore

import logging
logger = logging.getLogger(__name__)

class Toast(QtWidgets.QWidget):
    def __init__(self, window, text, time=4000):
        super().__init__()
        logger.debug("Create toast...")

        self.createLabel(window, text)

        # hide toast
        self.timerTimer = QtCore.QTimer(self)
        self.timerTimer.setSingleShot(True)
        self.timerTimer.timeout.connect(self.hideLabel)
        self.timerTimer.start(time)

    def createLabel(self, window, text):
        logger.debug("Create label...")
        self.toastLabel = QtWidgets.QLabel(
                                        window, 
                                        wordWrap=True, 
                                        alignment=QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop
                                    )
        self.toastLabel.setText(text)
        self.toastLabel.setStyleSheet(f"border-radius: 5px; background-color: #5a2bdbee;")
        self.toastLabel.move(QtGui.QCursor.pos().x(), QtGui.QCursor.pos().y())
        self.toastLabel.adjustSize()
        self.toastLabel.show()

    def hideLabel(self):
        logger.debug("Hide toast...")
        self.toastLabel.hide()
        