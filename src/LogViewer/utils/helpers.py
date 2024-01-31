from LogViewer.storage import SettingsSingleton
import textwrap

class Helpers:
    def __init__(self):
        pass

    def pythonize(self, value):
        if type(value) == int or type(value) == float or type(value) == bool:
            return str(value)
        return "'%s'" % str(value)

    def wordWrapLogline(self, formattedMessage):
        uiItem = "\n".join([textwrap.fill(line, SettingsSingleton()["staticLineWrap"],
            expand_tabs=False,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=True,
            max_lines=None
        ) if len(line) > SettingsSingleton()["staticLineWrap"]  else line for line in formattedMessage.strip().splitlines(keepends=False)])
        return uiItem