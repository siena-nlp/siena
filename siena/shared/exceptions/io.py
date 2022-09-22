from siena.shared.exceptions.base import SIENABaseException


class SIENAIOException(SIENABaseException):
    pass


class YAMLFormatException(SIENAIOException):
    pass


class NLUFileNotFoundException(SIENAIOException):
    pass


class InvalidFileExtensionException(SIENAIOException):
    pass


class FileSizeInspectingException(SIENAIOException):
    pass
