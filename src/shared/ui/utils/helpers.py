from PyQt5 import QtWidgets
import qdarkstyle

from shared.utils import catch_exceptions
from shared.ui.about_dialog import AboutDialog

import logging
logger = logging.getLogger(__name__)

@catch_exceptions(logger=logger)
def action_about(version, *args):
    logger.info("Showing About Dialog...")
    about = AboutDialog(version)
    about.show()
    return about.exec_()

def getAvailableStyles():
    return (
        "default",
        "dark"
    )

def applyStyle(style):
    if style == "dark":
        QtWidgets.QApplication.instance().setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    elif style == "default":
        QtWidgets.QApplication.instance().setStyleSheet("")
    else:
        raise RuntimeError("Unknown UI style: '%s'!" % style)
    
# see https://stackoverflow.com/a/3943023
def getCssContrastColor(*args):
    logger.debug("Got args: %s" % str(args))
    if len(args) == 1 and (type(args[0]) == list or type(args[0]) == tuple):
        r, g, b = args[0]
    elif len(args) == 3:
        r, g, b = args
    else:
        raise RuntimeError("Unexpected arguments: %s" % str(args))
    colors = []
    for c in (r, g, b):
        c = c / 255.0
        if c <= 0.04045:
            c = c/12.92
        else:
            c = ((c+0.055)/1.055) ** 2.4
        colors.append(c)
    if 0.2126 * colors[0] + 0.7152 * colors[1] + 0.0722 * colors[2] > 0.179:
        return "rgb(0, 0, 0)"
    return "rgb(255, 255, 255)"