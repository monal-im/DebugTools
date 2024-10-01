from PyQt5 import QtCore, QtWidgets
import functools

from .proxy_model import ProxyModel
from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(ProxyModel):
    class ChangeTriggeredFlag:
        def __init__(self, model):
            self.model = model
        def __enter__(self):
            self.model.triggeredProgramatically = True
        def __exit__(self, type, value, traceback):
            self.model.triggeredProgramatically = False
    
    @catch_exceptions(logger=logger)
    def __init__(self, sourceModel, loadContext, load_distance, load_count, parent=None):
        super().__init__(sourceModel, parent, handledSignals=[
            "layoutAboutToBeChanged",
            "layoutChanged",
            "rowsAboutToBeRemoved",
            "rowsRemoved",
            "rowsAboutToBeInserted",
            "rowsInserted"
        ])
        self.triggeredProgramatically = False
        self.loadContext = loadContext
        self.load_distance = load_distance
        self.load_count = load_count

        self.listView().verticalScrollBar().valueChanged.connect(self.scrollbarMovedHandler)
        self.sourceModel().layoutAboutToBeChanged.connect(self.layoutAboutToBeChangedHandler)
        self.sourceModel().layoutChanged.connect(self.layoutChangedHandler)
        self.sourceModel().rowsRemoved.connect(functools.partial(self._rowsChangedHandler, visibility=False))
        self.sourceModel().rowsInserted.connect(functools.partial(self._rowsChangedHandler, visibility=True))

        self.timerTimer = QtCore.QTimer()
        self.timerTimer.setSingleShot(True)
        self.timerTimer.timeout.connect(self.bla)
        self.timerTimer.start(8000)

        self.setVisible(0, self.loadContext)
    
    def bla(self, *args, **kwargs):
        logger.debug("BLAAA")
        self.beginRemoveRows(self.parent(), 6, 22)
        self.proxyData.removeRows(6, 22)
        self.endRemoveRows()
        logger.debug("BLUUUB")

    @catch_exceptions(logger=logger)
    def layoutAboutToBeChangedHandler(self, *args):
        # the topIndex is needed to restore our scroll position after triggering a lazy loading by scrolling up
        self.topIndex     = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().topLeft()))
        
        # save current selected index, to be restored later on
        # use sourceModel indexes because they stay stable even when we insert rows in this model
        self.currentIndexBefore = self.mapToSource(self.listView().currentIndex())
    
    @catch_exceptions(logger=logger)
    def layoutChangedHandler(self, *args):
        # timer function to be called once the loading completed
        def correctIt():
            # select item that was selected *before* we inserted stuff
            if self.currentIndexBefore.isValid():
                toProxyIndex = self.mapFromSource(self.currentIndexBefore)
                logger.debug(f"Resetting selected index to correct one: {self.currentIndexBefore.row() = }, {toProxyIndex.row() = }")
                self.listView().setCurrentIndex(toProxyIndex)
            
            # scroll to item that was at viewport top *before* we inserted stuff
            self.listView().scrollTo(self.mapFromSource(self.topIndex), hint=QtWidgets.QAbstractItemView.PositionAtTop)
            
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
    
    def setVisible(self, start, end):
        logger.debug(f"Setting visibility of rows in interval: {start = }, {end = }")
        self.beginInsertRows(self.parent(), start, end)
        self.proxyData.setVisible(start, end)
        self.endInsertRows()
    
    def setInvisible(self, start, end):
        self.beginRemoveRows(self.parent(), start, end)
        self.proxyData.setInvisible(start, end)
        self.endRemoveRows()

    @catch_exceptions(logger=logger)
    def scrollbarMovedHandler(self, *args):
        # if triggeredProgramatically is True the scrollbar wasn't moved by the user and shouldn't load any more rows
        if self.triggeredProgramatically != False:
            return
        
        topIndex     = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().topLeft()))
        bottomIndex  = self.mapToSource(self.listView().indexAt(self.listView().viewport().contentsRect().bottomLeft()))

        previousIndex = self.proxyData.getPreviousIndexWithState(topIndex, False)
        if previousIndex != None and topIndex.row() - previousIndex <= self.load_distance:
            # don't use the context manager because we have to set it to false in the timer
            self.triggeredProgramatically = True
            
            self.layoutAboutToBeChangedHandler()
            # this is the actual loading and will move all indexes to other positions
            self.setVisible(max(previousIndex - self.load_count, 0), topIndex.row())
            self.layoutChangedHandler()
            
            # we don't need to check if we have to lazy load rows below us, if we already had to load rows above us --> just return
            return
        
        nextIndex = self.proxyData.getNextIndexWithState(bottomIndex, False)
        if nextIndex != None and nextIndex - bottomIndex.row() <= self.load_distance:
            with self.triggerScrollChanges():
                self.setVisible(bottomIndex.row(), min(nextIndex + self.load_count, self.sourceModel().rowCount(None)))
    
    def triggerScrollChanges(self):
        return self.ChangeTriggeredFlag(self)

    @catch_exceptions(logger=logger)
    def clear(self):
        self.setCurrentRow(0)
        self.beginRemoveRows(self.parent(), 0, self.sourceModel().rowCount(None))
        self.proxyData.clear(False)
        self.endRemoveRows()

    @catch_exceptions(logger=logger)
    def setCurrentRow(self, row):
        index = self.createIndex(row, 0)
        logger.info(f"Setting row {row} to index {index.row()}")
        #self.uiWidget_listView.scrollTo(index, hint=QtWidgets.QAbstractItemView.PositionAtCenter)
        with self.triggerScrollChanges():
            # No mapFromSource required, because it sets the real index start and end points visible
            self.setVisible(max(0, row-self.loadContext), min(row+self.loadContext, self.sourceModel().rowCount(None)))

            self.listView().setCurrentIndex(self.mapFromSource(index))

    @catch_exceptions(logger=logger)
    def _rowsChangedHandler(self, parent, start, end, visibility):
        self.beginRemoveRows(parent, 6, 22)
        self.proxyData.removeRows(6, 22)
        self.endRemoveRows()
        return
    
        logger.debug(f"started with: {start = } » {end = }")
        self._initVisibilityList()
        for index in range(start, end+1):
            self._addToVisibilityList(index, visibility)
        visiblityList = self._sealVisibilityList(index)
        
        logger.debug(f"LAZY {visiblityList = }")
        
        for item in visiblityList:
            proxyStart = self.mapFromSource(self.createIndex(item["start"], 0)).row()
            proxyEnd = self.mapFromSource(self.createIndex(item["end"], 0)).row()
            logger.debug(f"Handling: {item['start'] = }, {item['end'] = }, {proxyStart = }, {proxyEnd = }")
            if visibility == True:
                logger.debug(f"Inserting with: {item['start'] = } » {item['end'] = }")
                self.beginInsertRows(parent, self.mapFromSource(self.createIndex(item["start"], 0)).row(), self.mapFromSource(self.createIndex(item["end"], 0)).row())
                self.proxyData.insertRows(item["start"], item["end"], True)
                self.endInsertRows()
                logger.debug(f"Inserted with: {item['start'] = } » {item['end'] = }")
            else:
                logger.debug(f"Removing with: {item['start'] = } » {item['end'] = }")
                self.beginRemoveRows(parent, proxyStart, proxyEnd)
                self.proxyData.removeRows(item["start"], item["end"])
                self.endRemoveRows()
                logger.debug(f"Removed with: {item['start'] = } » {item['end'] = }")
        
        # trigger scrollbarMovedHandler to make sure enough rows are visible
        #self.scrollbarMovedHandler()
