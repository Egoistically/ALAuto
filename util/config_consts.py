import enum

class UtilConsts(object):

    def __new__(cls):
        return cls

    class ScreenCapMode(enum.Enum):
        SCREENCAP_PNG = enum.auto()
        SCREENCAP_RAW = enum.auto()
        ASCREENCAP = enum.auto()


