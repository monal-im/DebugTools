from PyQt5 import QtWidgets
import logging
from shared.utils import catch_exceptions

logger = logging.getLogger(__name__)

# Qt only holds weak references to us -> store our strong reference here to not get garbage collected
instances = []

class MagicLineEdit:
    def __init__(self, combobox):
        instances.append(self) # don't garbage collect us
        self.combobox = combobox
        self.state = {"start": 0, "length": 0}
        combobox.lineEdit().selectionChanged.connect(self.comboboxSelectionChangedEvent)
        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)

    @catch_exceptions(logger=logger)
    def focusChangedEvent(self, oldWidget, newWidget):
        if newWidget == self.combobox and self.state["length"] > 0:
            logger.debug("focusChangedEvent: oldWidget: %s, newWidget: %s" % (oldWidget, newWidget))
            logger.debug("focusChangedEvent: self.state: %s" % str(self.state))
            logger.debug("focusChangedEvent: Combobox matching and length in selection state > 0")
            self.combobox.lineEdit().setSelection(self.state["start"], self.state["length"])

    @catch_exceptions(logger=logger)
    def comboboxSelectionChangedEvent(self):
        # don't save selection loss on focused changed
        if not self.combobox.hasFocus():
            return
        if self.combobox.lineEdit().hasSelectedText() == True:
            start = self.combobox.lineEdit().selectionStart()
            length = self.combobox.lineEdit().selectionLength()
            logger.debug("comboboxSelectionChangedEvent: Selection start: %s, length: %s " % (start, length))
            self.state = {"start": start, "length": length}
        else: 
            logger.debug("comboboxSelectionChangedEvent: Selection removed")
            self.state = {"start": 0, "length": 0}