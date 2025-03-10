from PyQt5 import QtCore
import functools

from .proxy_data import ProxyData
from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

# this class only caches methods that return static values
class ProxyModel(QtCore.QAbstractProxyModel):
    @catch_exceptions(logger=logger)
    def __init__(self, sourceModel, parent=None, handledSignals=None):
        super().__init__(parent)
        self.setSourceModel(sourceModel)
        self.proxyData = ProxyData(self)
        # proxy signals, too
        signals = [
            "columnsAboutToBeInserted", "columnsAboutToBeMoved", "columnsAboutToBeRemoved",
            "columnsInserted", "columnsMoved", "columnsRemoved", "dataChanged", "headerDataChanged",
            "layoutAboutToBeChanged", "layoutChanged", "modelAboutToBeReset", "modelReset",
            "rowsAboutToBeInserted", "rowsAboutToBeMoved", "rowsAboutToBeRemoved", "rowsInserted",
            "rowsMoved", "rowsRemoved",
        ]
        if handledSignals != None:
            signals = [signal for signal in signals if not signal in handledSignals]
        def emitter(signal, *args):
            logger.debug(f"Proxying signal '{signal}' from parent model with args: {args}")
            getattr(self, signal).emit(*args)
        for signal in signals:
            getattr(sourceModel, signal).connect(functools.partial(emitter, signal))

    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def parent(self, index=None):
        # this method logs errors if not implemented, so simply return an invalid index to make qt happy
        return QtCore.QModelIndex()
    
    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def index(self, row, column, parent=None):
        # this method logs errors if not implemented and is needed for qt to show content
        return self.createIndex(row, column, parent)
    
    @catch_exceptions(logger=logger)
    def mapFromSource(self, sourceIndex):
        # from rawlog index to proxy index
        return self.createIndex(self.proxyData.getNextVisibleProxyRow(sourceIndex.row()), 0)

    @catch_exceptions(logger=logger)
    def mapToSource(self, proxyIndex):
        # from proxy index to rawlog index
        if not proxyIndex.isValid():
            return QtCore.QModelIndex()
        nextVisibleRow = self.proxyData.getNextVisibleRow(proxyIndex.row())
        try:
            return self.sourceModel().createIndex(nextVisibleRow, 0)
        except:
            #logger.exception(f"Exception with data: {nextVisibleRow = } {proxyIndex.row() = }")
            return QtCore.QModelIndex()

    @catch_exceptions(logger=logger)
    def rowCount(self, index):
        return self.proxyData.getRowCount()

    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def columnCount(self, index):
        return self.sourceModel().columnCount(index)
    
    @catch_exceptions(logger=logger)
    def setCurrentRow(self, row):
        index = self.createIndex(row, 0)
        logger.info(f"Setting row {row} to index {index.row()}")
        # No mapFromSource required, because it sets the real index start and end points visible
        self.listView().setCurrentIndex(self.mapFromSource(index))

    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def listView(self):
        return self.sourceModel().listView()

    def _initVisibilityList(self):
        self.visibilityList = []

    def _addToVisibilityList(self, index, visibility):
        if self.proxyData.getVisibility(index) != visibility:
            logger.debug(f"visibility is different to before: {self.proxyData.getVisibility(index) = } != {visibility = }...")
            if len(self.visibilityList) == 0 or self.visibilityList[-1]["end"] != None:
                logger.debug(f"adding new block at {index = }...")
                self.visibilityList.append({"start": index, "end": None, "visibility": visibility})
            elif self.visibilityList[-1]["visibility"] != visibility:
                logger.debug(f"visibility flipped: {self.visibilityList[-1]['visibility'] = } != {visibility = }...")
                if self.visibilityList[-1]["end"] == None:
                    logger.debug(f"ending previous block: {self.visibilityList[-1] = }")
                    self.visibilityList[-1]["end"] = index-1
                logger.debug(f"adding next block at {index = }...")
                self.visibilityList.append({"start": index, "end": None, "visibility": visibility})
        elif len(self.visibilityList) != 0:
            logger.debug(f"visibility is equal to before: {self.proxyData.getVisibility(index) = } == {visibility = }...")
            if self.visibilityList[-1]["end"] == None:
                logger.debug(f"ending previous block: {self.visibilityList[-1] = }")
                self.visibilityList[-1]["end"] = index-1

    def _sealVisibilityList(self, index):
        if len(self.visibilityList) != 0 and self.visibilityList[-1]["end"] == None:
            logger.debug(f"ended last block: {self.visibilityList[-1] = }")
            self.visibilityList[-1]["end"] = index
        return self.visibilityList
