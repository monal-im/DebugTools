from PyQt5 import QtWidgets

from .proxy_model import ProxyModel

import logging
logger = logging.getLogger(__name__)

LAZY_DISTANCE = 400
LAZY_LOADING = 200

class LazyItemModel(ProxyModel):
    class ChangeTriggeredFlag:
        def __init__(self, model):
            self.model = model
        def __enter__(self):
            self.model.triggeredProgramatically = True
        def __exit__(self, type, value, traceback):
            self.model.triggeredProgramatically = False
            
    def __init__(self, baseModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(baseModel)
        self.triggeredProgramatically = False

    def setVisible(self, start, end):
        logger.debug(f"{start = } {end = }")
        self.beginInsertRows(self.index(start, 1), start, end);
        self.proxyData.setVisible(start, end)
        self.endInsertRows();

    def scrollbarMoved(self, scrollValue):
        # If triggeredProgramatically is True the scrollbar wasn't moved by the user and shouldn't load anymore rows
        # This is used for example by goToLastRow, which scrolls to the bottom 
        if self.triggeredProgramatically != False:
            return
        
        logger.debug(f"---- {scrollValue = }")

        topIndex     = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().topLeft()))
        bottomIndex  = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().bottomLeft()))

        with self.triggerScrollChanges():
            previousIndex = self.proxyData.getPreviousIndexWithState(topIndex, False)
            logger.debug(f"+++ {topIndex.row() = } {(topIndex.row() - previousIndex if previousIndex != None else 'end') = } {previousIndex = }")
            if previousIndex != None and topIndex.row() - previousIndex <= LAZY_DISTANCE:
                self.setVisible(max(previousIndex - LAZY_LOADING, 0), topIndex.row())
                #self.listView().scrollTo(, hint=QtWidgets.QAbstractItemView.PositionAtCenter)
                QtWidgets.QApplication.processEvents()
                self.listView().scrollContentsBy(scrollValue - self.listView().verticalScrollBar().value(), 0)
                return

            nextIndex = self.proxyData.getNextIndexWithState(bottomIndex, False)          
            if nextIndex != None and nextIndex - bottomIndex.row() <= LAZY_DISTANCE:
                self.setVisible(bottomIndex.row(), min(nextIndex + LAZY_LOADING, self.sourceModel().rowCount(None)))

    def triggerScrollChanges(self):
        return self.ChangeTriggeredFlag(self)

    def clear(self):
        self.beginRemoveRows(self.index(0, 1), 0, self.sourceModel().rowCount(None));
        self.proxyData.clear(False)
        self.endRemoveRows()