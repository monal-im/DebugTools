import qdarkstyle

from LogViewer.storage import SettingsSingleton

import logging
logger = logging.getLogger(__name__)

class StyleManager:
    @staticmethod
    def getAvailableStyles():
        return (
            "default",
            "dark"
        )
    
    @staticmethod
    def updateStyle(ui):
        style = SettingsSingleton()["uiStyle"]
        if style == "dark":
            ui.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        elif style == "default":
            ui.setStyleSheet("")
        else:
            raise RuntimeError("Unknown UI style: '%s'!" % style)
    
    @classmethod
    def styleDecorator(cls, class_to_decorate):
        orig_init = class_to_decorate.__init__
        
        def __init__(self, *args, **kwargs):
            # call original __init__
            orig_init(self, *args, **kwargs)
            
            # apply the correct style
            cls.updateStyle(self)
        
        class_to_decorate.__init__ = __init__       # monkeypatch: replace init
        return class_to_decorate
