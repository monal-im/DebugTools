import logging
from enum import Enum
from .constants import LOGLEVELS

logger = logging.getLogger(__name__)

class QueryStatus(Enum):
    EOF_REACHED = 1
    QUERY_ERROR = 2
    QUERY_OK = 3
    QUERY_EMPTY = 4

def matchQuery(query, rawlog, additionalMatchFunc = None):
    entries = []
    error = None
    status = QueryStatus.QUERY_OK

    for resultIndex in range(len(rawlog)):

        if additionalMatchFunc != None and not additionalMatchFunc(resultIndex, rawlog):
            continue

        try:
            if eval(query, {
                **LOGLEVELS,
                "true" : True,
                "false": False,
                "__index": resultIndex,
                "__rawlog": rawlog,
            }, rawlog[resultIndex]['data']):
                entries.append(resultIndex)

        except (SyntaxError, NameError) as e:
            error = e
            status = QueryStatus.QUERY_ERROR
            
    if len(entries) == 0 and error == None:
        status = QueryStatus.QUERY_EMPTY
    
    return {"status": status, "entries": entries, "error": error}