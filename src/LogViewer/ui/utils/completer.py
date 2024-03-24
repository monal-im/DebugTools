from PyQt5 import QtWidgets, QtCore

#custom completer, see here for reference: https://stackoverflow.com/a/36296644
class Completer(QtWidgets.QCompleter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCompletionMode(Completer.PopupCompletion)

    # Add texts instead of replace
    def pathFromIndex(self, index):
        path = QtWidgets.QCompleter.pathFromIndex(self, index)
        current_parts = str(self.widget().lineEdit().text()).split(" ")
        if len(current_parts) > 1:
            path = '%s %s' % (" ".join(current_parts[:-1]), path)   # replace last part with selected completion
        return path

    # Add operator to separate between texts
    def splitPath(self, path):
        path = str(path.split(' ')[-1]).lstrip(' ')
        return [path]
