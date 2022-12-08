from __future__ import annotations

from typing import Any, Generator, overload
from dataclasses import dataclass, field
from matplotlib.table import Cell
from pathlib import Path
from enum import Enum
import random
import json

from .bingo_utils import BingoUtils


class _PhrasePriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1


@dataclass(slots=True)
class _Phrase:

    __text: str
    __default_checked: bool
    __priority: _PhrasePriority
    __checked: bool = field(init=False, default=False)

    @property
    def text(self) -> str:
        return self.__text

    @property
    def checked(self) -> bool:
        return self.__checked

    @property
    def default_checked(self) -> bool:
        return self.__default_checked

    @property
    def priority(self) -> _PhrasePriority:
        return self.__priority

    @checked.setter
    def checked(self, item) -> None:
        if not isinstance(item, bool):
            raise TypeError('checked must be bool')
        self.__checked = item

    def __iter__(self) -> _Phrase:
        return self

    def __next__(self) -> _Phrase:
        return self


class BingoPhrases:

    __slots__ = (
        '__phrases',
    )

    __phrases: list[_Phrase]

    def __init__(self) -> None:
        self.__phrases = list()

    def load(self, dir_path: Path) -> None:
        """Load phrases from `./bingo_phrases.json`.

        Parameters
        ----------
        dir_path: `Path` - path with specified subject folder

        Raises
        ------
        OSError
            File not exists or cannot be loaded.
        """

        with open(dir_path / 'phrases.json', 'r', encoding='utf-8') as f:
            data: dict[str, dict[str, Any]] = json.load(f)

        for name, value in data.items():
            default_checked = value.get('default_checked') or False
            priority_name: str = value.get('priority') or "medium"
            priority = _PhrasePriority[priority_name.upper()]

            self.__phrases.append(
                _Phrase(name, default_checked, priority)
            )

    def shuffle(self, *, item_count: int | None = None) -> None:
        """Suffle the phrases.

        If item_count is specified reject phrases with the lowest priority.

        Raises
        ------
        TypeError
            item_count is not integer
        ValueError
            item_count is lower than 1 or too large
        """

        if item_count is not None:
            self.__phrases.sort(key=lambda i: i.priority.value)
            self.__phrases = self.__phrases[:item_count]

        random.shuffle(self.__phrases)

    @property
    def phrases(self) -> list[_Phrase]:
        return self.__phrases

    @overload
    def __getitem__(self, index: slice) -> list[_Phrase]:
        pass

    @overload
    def __getitem__(self, index: int) -> _Phrase:
        pass

    @overload
    def __getitem__(self, index: Cell) -> _Phrase:
        pass

    def __getitem__(self, index: int | slice | Cell) -> _Phrase | list[_Phrase]:
        if isinstance(index, Cell):
            for phrase in self.__phrases:
                cell_text = BingoUtils.get_text_from_cell(index)
                if phrase.text == cell_text:
                    return phrase
            raise ValueError('no suitable phrase found')

        return self.__phrases[index]

    def __iter__(self) -> Generator[_Phrase, None, None]:
        for phrase in self.__phrases:
            yield phrase
