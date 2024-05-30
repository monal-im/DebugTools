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

    def getNextVisibleIndex(self, proxyIndex):
        # from proxy index to real index
        counter = 0
        for nextIndex in range(len(self.proxyModel.rawlogModel.rawlog)):
            if self.visibility[nextIndex] == True:
                if counter == proxyIndex+1:
                    return nextIndex
                counter += 1
        return None

    def getNextVisibleProxyIndex(self, index):
        # from real index to proxy index
        counter = 0
        for nextIndex in range(index.row()):
            if self.visibility[nextIndex] == True:
                counter += 1
        return counter
        
    def setVisible(self, start, end):
        for index in range(start, end):
            self.visibility[index] = True
    
    def getRowCount(self):
        return len(self.visibility)-1
        
