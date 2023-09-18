from PyQt5 import QtCore

class Statusbar():
    def __init__(self, statusbar):
        self.statusbarText = {"static": [], "dynamic": []}
        self.statusbar = statusbar
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.dynamicStatusbar)
        self.timer.start(2000)

    def dynamicStatusbar(self):
        static = self.statusbarText["static"]
        dynamic = self.statusbarText["dynamic"]
        if dynamic != []:
            text = dynamic.pop()
            self.statusbar.showMessage(text)
        elif static != []:
            text = static.pop()
            self.statusbar.showMessage(text)
            static.insert(0, text)

    def showStaticStatusbarText(self, text):
        self.statusbarText["static"].append(text)

    def showDynamicStatusbarText(self, text):
        self.statusbarText["dynamic"].append(text)

    def clearDynamicStatusbar(self):
        self.statusbarText["dynamic"].clear()
        self.statusbarText["static"].clear()