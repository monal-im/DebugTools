import logging
from enum import Enum
from .constants import LOGLEVELS

logger = logging.getLogger(__name__)

class QueryStatus(Enum):
    EOF_REACHED = 1
    QUERY_ERROR = 2
    QUERY_OK = 3
    QUERY_EMPTY = 4

def matchQuery(query, rawlog, index, entry=None, preSearchFilter=None):
    matching = False
    error = None
    status = QueryStatus.QUERY_OK

    try:
        if entry == None:
            entry = rawlog[index]['data']
        if preSearchFilter == None or preSearchFilter(index, rawlog):
            if eval(query, {
                **LOGLEVELS,
                "true" : True,
                "false": False,
            }, entry):
                matching = True
        
    except (SyntaxError, NameError) as e:
        error = e
        status = QueryStatus.QUERY_ERROR
    
    return {"status": status, "error": error, "matching": matching}