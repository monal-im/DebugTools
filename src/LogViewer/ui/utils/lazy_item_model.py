from PyQt5 import QtCore, QtWidgets

from .proxy_model import ProxyModel

import logging
logger = logging.getLogger(__name__)

LAZY_DISTANCE = 400
LAZY_LOADING = 100

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
        logger.debug(f"Setting visibility of rows in interval: {start = }, {end = }")
        self.beginInsertRows(self.createIndex(start, 1), start, end);
        self.proxyData.setVisible(start, end)
        self.endInsertRows();

    def scrollbarMoved(self, *args):
        # if triggeredProgramatically is True the scrollbar wasn't moved by the user and shouldn't load any more rows
        if self.triggeredProgramatically != False:
            return
        
        # the topIndex is needed to restore our scroll position after triggering a lazy loading by scrolling up
        topIndex     = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().topLeft()))
        bottomIndex  = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().bottomLeft()))

        previousIndex = self.proxyData.getPreviousIndexWithState(topIndex, False)
        if previousIndex != None and topIndex.row() - previousIndex <= LAZY_DISTANCE:
            # save current selected index, to be restored later on
            # use sourceModel indexes because they stay stable even when we insert rows in this model
            currentIndexBefore = self.mapToSource(self.listView().currentIndex())
            
            # don't use the context manager because we have to set it to false in the timer
            self.triggeredProgramatically = True
            
            # this is the actual loading and will move all indexes to other positions
            self.setVisible(max(previousIndex - LAZY_LOADING, 0), topIndex.row())
            
            # timer function to be called once the loading completed
            def correctIt():
                # select item that was selected *before* we inserted stuff
                if currentIndexBefore.isValid():
                    toProxyIndex = self.mapFromSource(currentIndexBefore)
                    logger.debug(f"Resetting selected index to correct one: {currentIndexBefore.row() = }, {toProxyIndex.row() = }")
                    self.listView().setCurrentIndex(toProxyIndex)
                
                # scroll to item that was at viewport top *before* we inserted stuff
                self.listView().scrollTo(self.mapFromSource(topIndex), hint=QtWidgets.QAbstractItemView.PositionAtTop)
                
                self.triggeredProgramatically = False
            
            # use a timer to add this event to the back of our event queue because it won't visibly select the item otherwise
            # this timer has to trigger the correct scrollTo() after setting the current index, to not jump to that index when
            # using the mouse to scroll
            # (even without a timer it still selects the correct item, just not visibly)
            # (calling QtWidgets.QApplication.processEvents() before calling setCurrentIndex() won't help)
            self.correctingTimer = QtCore.QTimer()
            self.correctingTimer.setSingleShot(True)
            self.correctingTimer.timeout.connect(correctIt)
            self.correctingTimer.start(0)
            
            # we don't need to check if we have to lazy load rows below us, if we already had to load rows above us --> just return
            return
        
        nextIndex = self.proxyData.getNextIndexWithState(bottomIndex, False)
        if nextIndex != None and nextIndex - bottomIndex.row() <= LAZY_DISTANCE:
            with self.triggerScrollChanges():
                self.setVisible(bottomIndex.row(), min(nextIndex + LAZY_LOADING, self.sourceModel().rowCount(None)))
    
    def triggerScrollChanges(self):
        return self.ChangeTriggeredFlag(self)

    def clear(self):
        self.beginRemoveRows(self.createIndex(0, 0), 0, self.sourceModel().rowCount(None));
        self.proxyData.clear(False)
        self.endRemoveRows()