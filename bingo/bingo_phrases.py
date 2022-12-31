from __future__ import annotations

from typing import Any, Generator, overload
from dataclasses import dataclass, field
from matplotlib.table import Cell
from pathlib import Path
from enum import Enum
import random
import json

from .bingo_utils import BingoUtils
from .bingo_settings import BingoSettings


class _PhrasePriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1


@dataclass(slots=True)
class _Phrase:

    __text: str
    __default_checked: bool
    __priority: _PhrasePriority
    __default_position: dict[str, int] | None
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
    def default_position(self) -> dict[str, int]:
        return self.__default_position or {}

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
            default_pos = value.get('position')

            self.__phrases.append(
                _Phrase(name, default_checked, priority, default_pos)
            )

    def shuffle(self, settings: BingoSettings) -> None:
        """Suffle the phrases.

        Reject phrases with the lowest priority.

        Put positional phrases where they belong.
        """

        prio_phrases: dict[_PhrasePriority, list[_Phrase]] = dict()
        for phrase in self.__phrases:
            try:
                prio_phrases[phrase.priority].append(phrase)
            except KeyError:
                prio_phrases[phrase.priority] = [phrase]

        phrases = self.__phrases

        phrases = prio_phrases[_PhrasePriority.HIGH]
        phrases.extend(prio_phrases[_PhrasePriority.MEDIUM])
        phrases.extend(prio_phrases[_PhrasePriority.LOW])
        self.__phrases = phrases = self.__phrases[:settings.no_of_cells]
        random.shuffle(self.__phrases)

        # Set phrases with a specific position
        for i in range(len(phrases)):
            if (def_pos := phrases[i].default_position.get(
                f'{settings.dim_cols}x{settings.dim_rows}'
            )) is not None:
                phrases[i], phrases[def_pos] = phrases[def_pos], phrases[i]

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
