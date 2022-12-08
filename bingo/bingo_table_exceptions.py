__all__ = (
    'BingoTableException',
    'CellIsMarked',
    'CellIsNotMarked',
    'ControllerNotLoaded'
)


class BingoTableException(Exception):
    pass


class CellIsMarked(BingoTableException):
    pass


class CellIsNotMarked(BingoTableException):
    pass


class ControllerNotLoaded(BingoTableException):
    pass
