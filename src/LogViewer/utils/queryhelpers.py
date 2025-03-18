from enum import Enum
from PyQt5 import QtWidgets

from LogViewer.storage import SettingsSingleton

import logging
logger = logging.getLogger(__name__)

class QueryStatus(Enum):
    EOF_REACHED = 1
    QUERY_ERROR = 2
    QUERY_OK = 3
    QUERY_EMPTY = 4

def matchQuery(query, rawlog, index, entry=None, usePython=True):
    matching = False
    error = None
    status = QueryStatus.QUERY_OK

    try:
        if entry == None:
            entry = rawlog[index]
        if usePython:
            if eval(query, {
                **SettingsSingleton().getLoglevels(),
                "true" : True,
                "false": False,
            }, entry):
                matching = True
        else:
            # this is unset if not loaded into ui, fall back to raw message in non-ui cases
            if "__formattedMessage" in entry:
                if query in entry["__formattedMessage"]:
                    matching = True
            else:
                if query in entry["message"]:
                    matching = True
    except (SyntaxError, NameError) as e:
        error = e
        status = QueryStatus.QUERY_ERROR
    
    return {"status": status, "error": error, "matching": matching}

def loader(entry):
    # directly warn about file corruptions when they happen to allow the user to abort the loading process
    # using the cancel button in the progressbar window
    if "__warning" in entry and entry["__warning"] == True:
        QtWidgets.QMessageBox.warning("File corruption detected", entry["message"])
    
    return entry
