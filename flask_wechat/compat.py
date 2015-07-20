import sys

ENCODING = "utf8"

_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)


if is_py2:
    builtin_str = str
    bytes = str
    str = unicode
    basestring = basestring
elif is_py3:
    builtin_str = str
    str = str
    bytes = bytes
    basestring = (str, bytes)
else:
    raise ValueError("unsupported python version")


def to_bytes(data):
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode(ENCODING)
    else:
        return bytes(data, ENCODING)


def to_str(data):
    if isinstance(data, str):
        return data
    elif isinstance(data, bytes):
        return data.decode(ENCODING)
    else:
        return str(data)
