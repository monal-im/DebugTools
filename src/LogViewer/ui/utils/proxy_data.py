import collections
import functools
import inspect

import logging
logger = logging.getLogger(__name__)

LRU_MAXSIZE = 1024*1024

class ProxyData():
    def __init__(self, proxyModel, standardValue=False):
        super().__init__()
        self.proxyModel = proxyModel
        logger.info(f"Using {standardValue = }...")
        self.clear(standardValue)

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getVisibility(self, index):
        return self.visibility[index]

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getPreviousIndexWithState(self, realIndex, state=False):
        for index in range(realIndex.row(), -1, -1):
            if self.visibility[index] == state:
                return index
        return None  

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getNextIndexWithState(self, realIndex, state=False):
        for index in range(realIndex.row(), self.proxyModel.sourceModel().rowCount(None)):
            if self.visibility[index] == state:
                return index
        return None
    
    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getNextVisibleRow(self, proxyRow):
        # from proxy index to real index
        counter = 0
        for realIndex in range(self.proxyModel.sourceModel().rowCount(None)):
            if self.visibility[realIndex] == True:
                counter += 1
                if counter == proxyRow+1:
                    return realIndex
        return None

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getNextVisibleProxyRow(self, realRow):
        # from real index to proxy index
        counter = 0
        for index in range(realRow):
            if self.visibility[index] == True:
                counter += 1
        return counter
    
    def setVisible(self, start, end):
        self._clearAllCaches()
        for index in range(start, end):
            self.visibility[index] = True
    
    def setInvisible(self, start, end):
        self._clearAllCaches()
        for index in range(start, end):
            self.visibility[index] = False
    
    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getRowCount(self):
        # len(self.visibility) gives the number of items already populated in defaultdict (regardless of it's value)
        # --> iterate over populated values and count truth values
        visible = 0
        for index in self.visibility:
            if self.visibility[index] == True:
                visible += 1
        return visible

    def clear(self, standardValue=False):
        logger.debug(f"Clearing proxy_data of {self.proxyModel.__class__.__name__}...")
        self.standardValue = standardValue
        self._clearAllCaches()
        self.visibility = collections.defaultdict(lambda: standardValue)

    def setVisibilityAtIndex(self, index, visibility):
        self._clearAllCaches()
        self.visibility[index] = visibility
    
    def _clearAllCaches(self):
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, "cache_parameters"):
                #logger.debug(f"Cache effects for {self.proxyModel.__class__.__name__}.{member.__name__}: {member.cache_info()}")
                member.cache_clear()

    def removeRows(self, start, end):
        keys = list(self.visibility.keys())
        for index in range(start, end+1):
            if index in keys:
                del self.visibility[index]
        values = list(self.visibility.values())
        self.clear(self.standardValue)
        self.visibility |= {k: values[k] for k in range(len(values))}
        logger.debug(f"removeRows: {self.visibility = }")
    
    def insertRows(self, start, end, value):
        old = self.visibility.copy()
        count = end - start + 1
        keys = list(self.visibility.keys())
        self.clear(self.standardValue)
        for k in keys:
            if k < start:
                self.visibility[k] = old[k]
            else:
                self.visibility[k+count] = old[k]
        for k in range(start, end+1):
            self.visibility[k] = value
