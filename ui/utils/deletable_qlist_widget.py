from PyQt5 import QtWidgets, QtCore

class DeletableQListWidget(QtWidgets.QListWidget):
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.takeItem(self.selectedIndexes()[0].row())
        else:
            super().keyPressEvent(event)