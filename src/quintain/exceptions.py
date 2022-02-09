class QuintainError(Exception):
    pass


class NoSuchPort(QuintainError):
    pass


class NoSuchDevice(QuintainError):
    pass


class InvalidDuration(QuintainError):
    pass


class DuplicateDeviceError(QuintainError):
    pass
