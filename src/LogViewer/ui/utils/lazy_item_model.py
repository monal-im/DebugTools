from PyQt5 import QtWidgets, QtCore

class LazyItemModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        QtCore.QAbstractListModel.__init__(self, parent)
        self.list = parent or []

    def rowCount(self, index):
        return 1000

    def paint(self, painter, option, index):
        text = index.model().data(index, QtCore.Qt.DisplayRole).toString()

        label = QtWidgets.QLabel()
        label.setText(text)
        label.setGeometry(option.rect)

        painter.save()
        painter.translate(option.rect.x(), option.rect.y())

        label.render(painter)
        painter.restore()

    def columnCount(self, index):
        pass