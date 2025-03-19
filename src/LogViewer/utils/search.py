from LogViewer.storage import SettingsSingleton
from LogViewer.utils.queryhelpers import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

# own exception to allow our __init__ to communicate an abort condition
class AbortSearch(RuntimeError):
    pass

class Search:
    PREVIOUS = -1
    NEXT = 1

    def __init__(self, rawlog, query, startIndex, update_progressbar=None):
        super().__init__()
        self.rawlog = rawlog
        self.query = query
        self.resultList = []
        # the first search result should set our eof index (we want our status to be EOF_REACHED once we reach exactly this result again)
        self.updateStartIndex = True
        self.startIndex = startIndex                    # begin our search at this rawlog index
        self.status = QueryStatus.QUERY_OK
        self.error = None

        self.searchMatchingEntries(0, len(self.rawlog), update_progressbar=update_progressbar)

        self.resultIndex = -1           # don't jump over the first result on start
        self.eofIndex = 0               # the initial EOF point is the first result (e.g. result index 0)

    def searchMatchingEntries(self, start, end, update_progressbar=None):
        for index in range(start, end):
            # Presearch filter is expecting a finished rawlog loading
            result = matchQuery(self.query, self.rawlog, index, usePython=SettingsSingleton()["usePythonSearch"])
            if result["matching"]:
                self.resultList.append(index)
            if result["status"] == QueryStatus.QUERY_ERROR:
                self.status = result["status"]
                self.error = result["error"]
            if update_progressbar != None:
                if update_progressbar(index, len(self.rawlog)) == True:
                    raise AbortSearch()
        if len(self.resultList) == 0 and self.status != QueryStatus.QUERY_ERROR:
            self.status = QueryStatus.QUERY_EMPTY

    def calculateStartIndex(self, startIndex, direction):
        if direction == Search.NEXT:
            resultIndexList = range(len(self.resultList)-1, -1, -1)
        elif direction == Search.PREVIOUS:
            resultIndexList = range(len(self.resultList))
        else:
            raise RuntimeError("Unexpected search direction: %s" % str(direction))
        found = False
        for resultIndex in resultIndexList:
            if (direction == Search.NEXT and self.resultList[resultIndex] <= startIndex) or (direction == Search.PREVIOUS and self.resultList[resultIndex] >= startIndex):
                retval = resultIndex
                found = True
                break
        # if we could not find any search result preceeding (for NEXT) or following (for PREVIOUS) our current startIndex,
        # we have to round wrap and select the last search result one (for NEXT) or the first one (for PREVIOS)
        # --> searching will again round wrap increment/decrement the self.resultIndex to the first result (for NEXT) or last result (for PREVIOS)
        if not found:
            if direction == Search.NEXT:
                retval = len(self.resultList)-1
            elif direction == Search.PREVIOUS:
                retval = 0
            else:
                raise RuntimeError("Unexpected search direction: %s" % str(direction))
            
        logger.debug("Start index %dRI is at %dSI in direction %s" % (startIndex, retval, "NEXT" if direction == Search.NEXT else "PREVIOUS"))
        return retval

    def _handleEof(self):
        # self.updateStartIndex is only True if this is the first call after the user clicked onto a row in the ui to set a new starting point
        # --> save the new search result index as new starting point (e.g. the eof point)
        # --> if not the first call: test if we reached the old starting point (e.g. we reached eof)
        if self.updateStartIndex:
            self.eofIndex = self.resultIndex
            self.updateStartIndex = False
            self.status = QueryStatus.QUERY_OK
            logger.debug("Set eofIndex to %dSI..." % self.eofIndex)
        elif self.resultIndex == self.eofIndex:
            self.status = QueryStatus.EOF_REACHED
            logger.debug("Detected eof...")
        else:
            self.status = QueryStatus.QUERY_OK
            logger.debug("Neither eof detected nor eofIndex updated...")
    
    def resetStartIndex(self, startIndex):
        logger.debug("Resetting start index to %dRI on next search..." % startIndex)
        self.updateStartIndex = True
        self.startIndex = startIndex
    
    def next(self):
        if len(self.resultList) == 0:
            return None
        
        # if self.startIndex is set, this is our first search result
        # --> calculate the starting index of our search (not rawlog index but search result index)
        if self.startIndex != None:
            self.resultIndex = self.calculateStartIndex(self.startIndex, Search.NEXT)
            self.startIndex = None

        self.resultIndex += 1
        if self.resultIndex >= len(self.resultList):
            self.resultIndex = 0

        self._handleEof()
        
        return self.getCurrentResult()
    
    def previous(self):
        if len(self.resultList) == 0:
            return None
        
        # if self.startIndex is set, this is our first search result
        # --> calculate the starting index of our search (not rawlog index but search result index)
        if self.startIndex != None:
            self.resultIndex = self.calculateStartIndex(self.startIndex, Search.PREVIOUS)
            self.startIndex = None

        self.resultIndex -= 1
        if self.resultIndex < 0:
            self.resultIndex = len(self.resultList) - 1

        self._handleEof()

        return self.getCurrentResult()

    def getStatus(self):
        return self.status
    
    def getError(self):
        return self.error
    
    def getQuery(self):
        return self.query
    
    def getCurrentResult(self):
        if len(self.resultList) == 0:
            return None
        return self.resultList[self.resultIndex]
    
    def __len__(self):
        return len(self.resultList)

    def getPosition(self):
        return self.resultIndex + 1
    