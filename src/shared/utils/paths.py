import sys
import os
import platformdirs

import logging
logger = logging.getLogger(__name__)

class Paths:
    def set_personality(file):
        basename = os.path.splitext(os.path.basename(file))[0]
        Paths.PLATFORM_ARGS = (basename, "monal-im")
        Paths.BASEDIR = os.path.join(os.path.dirname(os.path.abspath(file)), basename)
    
    def get_basedir_path():
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.abspath(Paths.BASEDIR)

    def get_ui_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "ui", filename))

    def get_art_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "data", "art", filename))

    def get_default_conf_filepath(filename):
        return os.path.abspath(os.path.join(Paths.get_basedir_path(), "data", "conf", filename))

    def get_conf_filepath(filename):
        return os.path.abspath(os.path.join(Paths.user_data_dir(), filename))

    def user_data_dir():
        return os.path.abspath(platformdirs.user_data_dir(*Paths.PLATFORM_ARGS, roaming=True))

    def user_log_dir():
        return os.path.abspath(platformdirs.user_log_dir(*Paths.PLATFORM_ARGS))

# dummy defaults to be overwritten by main.py
Paths.PLATFORM_ARGS = ()
Paths.BASEDIR = "."
