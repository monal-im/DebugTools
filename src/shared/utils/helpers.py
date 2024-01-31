from shared.utils import catch_exceptions
from shared.ui.about_dialog import AboutDialog

import logging
logger = logging.getLogger(__name__)

class SharedHelpers:
    def __init__(self):
        pass

    @catch_exceptions(logger=logger)
    def action_about(self, version, *args):
        logger.info("Showing About Dialog...")
        self.about = AboutDialog(version)
        self.about.show()
        result = self.about.exec_()