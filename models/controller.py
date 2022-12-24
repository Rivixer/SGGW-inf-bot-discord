from abc import ABC

from .model import Model


class Controller(ABC):

    __slots__ = (
        '_model',
    )

    _model: Model

    def __init__(self, model: Model) -> None:
        self._model = model
