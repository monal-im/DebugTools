import collections
import functools
import inspect

import logging
logger = logging.getLogger(__name__)

LRU_MAXSIZE = 1024*1024

class ProxyData():
    def __init__(self, proxyModel):
        super().__init__()
        self.visibility = collections.defaultdict(lambda: False)
        self.proxyModel = proxyModel

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def getVisibility(self, start, end):
        for index in range(start, end):
            if self.visibility[index] == False:
                return False
        return True  

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

    def clear(self, standardValue = False):
        logger.debug(f"Clearing proxy_data of {self.proxyModel.__class__.__name__}...")
        self._clearAllCaches()
        self.visibility = collections.defaultdict(lambda: standardValue)

    def setVisibilityAtIndex(self, index, visibility):
        self._clearAllCaches()
        self.visibility[index] = visibility
    
    def _clearAllCaches(self):
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, "cache_parameters"):
                logger.debug(f"Cache effects for {self.proxyModel.__class__.__name__}.{member.__name__}: {member.cache_info()}")
                member.cache_clear()

    def removeRows(self, start, end):
        for index in range(start, end):
            if index in self.visibility.keys():
                del self.visibility[index]
    
    def insertRows(self, start, end):
        for index in range(start, end):
            if index not in self.visibility.keys():
                self.visibility[index] = self.visibility[index]
                