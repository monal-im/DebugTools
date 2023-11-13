import logging
from .queryhelpers import QueryStatus, matchQuery

logger = logging.getLogger(__name__)

class Search:
    def __init__(self, rawlog, query, startIndex):
        super().__init__()
        self.query = query
        self.filteredList = []
        self.status = QueryStatus.QUERY_OK
        for index in range(len(rawlog)):
            # Presearch filter is expecting a finished rawlog loading
            result = matchQuery(query, rawlog, index, preSearchFilter=self._preSearchFilter)
            if result["matching"]:
                self.filteredList.append(index)
            if result["status"] == QueryStatus.QUERY_ERROR:
                self.status = result["status"]
        if len(self.filteredList) == 0:
            self.status = QueryStatus.QUERY_EMPTY
        self.setStartIndex(startIndex)

    def _preSearchFilter(self, resultIndex, rawlog):
        if rawlog[resultIndex]["uiItem"].isHidden() == False:
            return True
        return False

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
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()
    
    def previous(self):
        if len(self.filteredList) == 0:
            return None
        
        self.resultIndex -= 1
        if self.resultIndex < 0:
            self.resultIndex = len(self.filteredList) - 1

        if self.resultIndex == self.resultStartIndex:
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()

    def getStatus(self):
        return self.status
    
    def getQuery(self):
        return self.query
    
    def getCurrentResult(self):
        if len(self.filteredList) == 0:
            return None
        return self.filteredList[self.resultIndex]
    
    def __len__(self):
        return len(self.filteredList)

    def getPosition(self):
        return self.resultIndex + 1