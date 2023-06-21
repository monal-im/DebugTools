import functools
import sys
import logging
import _thread

# see https://stackoverflow.com/a/16068850
def catch_exceptions(exception=Exception, logger=logging.getLogger(__name__)):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception as err:
                logger.exception("Exception in thread/pyqt callback!")
                logger.error("Shutting down immediately due to exception!")
                #_thread.interrupt_main()
                sys.exit(1)
                return None
        return wrapper
    return deco 
