from LogViewer.storage import SettingsSingleton
import qdarkstyle

class setStyle():
    def __init__(self, ui):
        currentStyle = SettingsSingleton().getCurrentStyle()
        if currentStyle == "dark":
            ui.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            ui.setStyleSheet("")