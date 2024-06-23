import collections

import logging
logger = logging.getLogger(__name__)

class ProxyData():
    def __init__(self, proxyModel):
        super().__init__()
        self.visibility = collections.defaultdict(lambda: False)
        self.proxyModel = proxyModel

    def getVisibility(self, start, end):
        for index in range(start, end):
            if self.visibility[index] == False:
                return False
        return True  

    def getPreviousIndexWithState(self, realIndex, state=False):
        for index in range(realIndex.row(), -1, -1):
            if self.visibility[index] == state:
                return index
        return None  

    def getNextIndexWithState(self, realIndex, state=False):
        for index in range(realIndex.row(), self.proxyModel.sourceModel().rowCount(None)):
            if self.visibility[index] == state:
                return index
        return None
    
    def getNextVisibleIndex(self, proxyIndex):
        # from proxy index to real index
        counter = 0
        for realIndex in range(self.proxyModel.sourceModel().rowCount(None)):
            if self.visibility[realIndex] == True:
                counter += 1
                if counter == proxyIndex+1:
                    return realIndex
        return None

    def getNextVisibleProxyIndex(self, realIndex):
        # from real index to proxy index
        counter = 0
        for index in range(realIndex.row()):
            if self.visibility[index] == True:
                counter += 1
        return counter
        
    def setVisible(self, start, end):
        for index in range(start, end):
            self.visibility[index] = True
    
    def getRowCount(self):
        # len(self.visibility) gives the number of items already populated in defaultdict (regardless of it's value)
        # --> iterate over populated values and count truth values
        visible = 0
        for index in self.visibility:
            if self.visibility[index] == True:
                visible += 1
        return visible

    def clear(self, standardValue = False):
        self.visibility = collections.defaultdict(lambda: standardValue)

    def setVisibilityAtIndex(self, index, visibility):
        self.visibility[index] = visibility