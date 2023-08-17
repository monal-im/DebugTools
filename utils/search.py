import logging
from .loglevels import LOGLEVELS

logger = logging.getLogger(__name__)

class Search:
    EOF_REACHED = 1
    QUERY_ERROR = 2
    QUERY_OK = 3
    QUERY_EMPTY = 4

    def __init__(self, rawlog, query, startIndex):
        super().__init__()
        self.rawlog = rawlog
        self.query = query
        self.filteredList = self.getItemswithQuerys(query)
        self.setStartIndex(startIndex)

    def setStartIndex(self, startIndex):
        self.resultIndex = 0
        self.resultStartIndex = 0
        for resultIndex in range(len(self.filteredList)):
            if self.filteredList[resultIndex] >= startIndex:
                self.resultIndex = resultIndex
                self.resultStartIndex = resultIndex
                break

    def next(self):
        if len(self.filteredList) == 0:
            return None

        self.resultIndex += 1
        if self.resultIndex >= len(self.filteredList):
            self.resultIndex = 0

        if self.resultIndex == self.resultStartIndex:
            self.status = self.EOF_REACHED

        return self.getCurrentResult()
    
    def previous(self):
        if len(self.filteredList) == 0:
            return None
        
        self.resultIndex -= 1
        if self.resultIndex < 0:
            self.resultIndex = len(self.filteredList) - 1

        if self.resultIndex == self.resultStartIndex:
            self.status = self.EOF_REACHED

        return self.getCurrentResult()

    def getStatus(self):
        return self.status
    
    def getQuery(self):
        return self.query
    
    def getCurrentResult(self):
        if len(self.filteredList) == 0:
            return None
        return self.filteredList[self.resultIndex]

    def getItemswithQuerys(self, query):
        entries = []
        self.status = self.QUERY_OK
        try:
            for resultIndex in range(len(self.rawlog)):
                if eval(query, {
                    **LOGLEVELS,
                    "true" : True,
                    "false": False,
                    "__index": resultIndex,
                    "__rawlog": self.rawlog,
                }, self.rawlog[resultIndex]['data']):
                    entries.append(resultIndex)
            
            if len(entries) == 0:
                self.status = self.QUERY_EMPTY
            return entries
        
        except (SyntaxError, NameError) as e:
            self.status = self.QUERY_ERROR
            logger.warning("ERROR(%s): %s" % (query, str(e)))
            return []