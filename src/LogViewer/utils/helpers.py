import textwrap
import functools

def pythonize(value):
    if type(value) == int or type(value) == float or type(value) == bool:
        return str(value)
    return "'%s'" % str(value)

@functools.lru_cache(maxsize=1024*1024)
def wordWrapLogline(formattedMessage, staticLineWrap):
    uiItem = "\n".join([textwrap.fill(line, staticLineWrap,
        expand_tabs=False,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=True,
        max_lines=None
    ) if len(line) > staticLineWrap  else line for line in formattedMessage.strip().splitlines(keepends=False)])
    return uiItem