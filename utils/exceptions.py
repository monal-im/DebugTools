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
                #logger.debug("ARGS: %s" % str(args))
                #logger.debug("KWARGS: %s" % str(kwargs))
                return func(*args, **kwargs)
            except exception as err:
                logger.exception(err)
                logger.error("Shutting down immediately due to exception!")
                #_thread.interrupt_main()
                sys.exit(1)
                return None
        return wrapper
    return deco 
