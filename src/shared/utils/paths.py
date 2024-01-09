import sys
import os
import platformdirs

import logging
logger = logging.getLogger(__name__)

class Paths:
    @staticmethod
    def set_personality(file):
        basename = os.path.splitext(os.path.basename(file))[0]
        Paths.PLATFORM_ARGS = (basename, "monal-im")
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            Paths.BASEDIR = os.path.join(sys._MEIPASS, basename)
        else:
            Paths.BASEDIR = os.path.join(os.path.dirname(os.path.abspath(file)), basename)

    @staticmethod
    def get_basedir_path():
        return os.path.abspath(Paths.BASEDIR)

    @staticmethod
    def get_ui_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "ui", filename))

    @staticmethod
    def get_art_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "data", "art", filename))

    @staticmethod
    def get_default_conf_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "data", "conf", filename))

    @staticmethod
    def get_user_documents_dir():
        return os.path.abspath(platformdirs.user_documents_dir())

    @staticmethod
    def get_conf_filepath(filename):
        return os.path.abspath(os.path.join(Paths.user_data_dir(), filename))

    @staticmethod
    def user_data_dir():
        return os.path.abspath(platformdirs.user_data_dir(*Paths.PLATFORM_ARGS, roaming=True))

    @staticmethod
    def user_log_dir():
        return os.path.abspath(platformdirs.user_log_dir(*Paths.PLATFORM_ARGS))

# dummy defaults to be overwritten by main.py
Paths.PLATFORM_ARGS = ()
Paths.BASEDIR = "."
