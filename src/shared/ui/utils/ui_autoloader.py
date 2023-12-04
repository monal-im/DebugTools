import os
import inspect
from PyQt5 import QtGui, uic
from shared.utils import Paths

import logging
logger = logging.getLogger(__name__)

def UiAutoloader(class_to_decorate):
    orig_init = class_to_decorate.__init__
    
    def __init__(self, *args, **kwargs):
        # first of all: call super __init__ (required by pyqt)
        super(class_to_decorate, self).__init__()
        
        # load the ui definition
        file = inspect.getfile(self.__class__)
        uifile = os.path.splitext(file)[0]+".ui"
        logger.info("Loading UI definition for '%s' from '%s'..." % (os.path.basename(file), uifile))
        uic.loadUi(Paths.get_ui_filepath(uifile), self)
        
        # load icon if existing
        iconfile = Paths.get_art_filepath("icon.png")
        if os.path.isfile(iconfile):
            self.setWindowIcon(QtGui.QIcon(iconfile))
        
        # call original __init__
        orig_init(self, *args, **kwargs)
    
    class_to_decorate.__init__ = __init__       # monkeypatch: replace init
    return class_to_decorate
