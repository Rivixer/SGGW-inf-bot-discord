from __future__ import annotations

from matplotlib.table import Table, Cell
from dataclasses import dataclass, field
from datetime import timedelta as td
from datetime import datetime as dt
import matplotlib.pyplot as plt
from typing import Generator
from pathlib import Path
import os

import nextcord
import pickle

from .bingo_table_generator import BingoTableGenerator
from .bingo_win_controller import BingoWinController
from .bingo_settings import BingoSettings
from .bingo_phrases import BingoPhrases
from .bingo_table_exceptions import *
from .bingo_utils import BingoUtils


@dataclass(slots=True)
class _TableController:

    __table: Table
    __settings: BingoSettings
    __phrases: BingoPhrases
    __win_ctrl: BingoWinController = field(init=False)

    def __post_init__(self) -> None:
        self.__win_ctrl = BingoWinController(
            self.__table,
            self.__settings,
            self.__phrases
        )

    @property
    def table(self) -> Table:
        return self.__table

    @property
    def win_ctrl(self) -> BingoWinController:
        return self.__win_ctrl

    def __getitem__(self, value: tuple[str, int]) -> Cell:
        if not isinstance(value, tuple):
            raise TypeError('indexes must be tuple')
        if len(value) != 2:
            raise ValueError('indexes must have tuple with 2 values')
        if not isinstance(value[0], str) or len(value[0]) != 1:
            raise ValueError('first index must be one letter str')
        if not isinstance(value[1], int):
            raise TypeError('second index must be int')

        column = ord(value[0].upper()) - ord('A')

        # We don't have to substract 1,
        # because the first index (zero) refers to column names
        row = value[1]

        return self.__table[(row, column)]

    def __iter__(self) -> Generator[Cell, None, None]:
        for i, cell in self.__table.get_celld().items():
            if i[0] == 0:  # is column_name
                continue
            if i[1] == -1:  # is row_name
                continue
            yield cell

    def iter_rows(self) -> Generator[Cell, None, None]:
        for i, cell in self.__table.get_celld().items():
            if i[1] == -1:
                yield cell

    def iter_cols(self) -> Generator[Cell, None, None]:
        for i, cell in self.__table.get_celld().items():
            if i[0] == 0:
                yield cell

    def mark_cell(self, cell: Cell) -> None:
        """Mark the cell.

        Raises
        ------
        CellIsMarked
            Cell is already marked.
        """
        phrase = self.__phrases[cell]

        if phrase.checked:
            raise CellIsMarked()

        phrase.checked = True
        cell.set_facecolor(self.__settings.checked_colour)

    def unmark_cell(self, cell: Cell) -> None:
        """Unmark the cell.

        Raises
        ------
        CellIsNotMarked
            Cell is not marked.
        """

        phrase = self.__phrases[cell]

        if not phrase.checked:
            raise CellIsNotMarked()

        cell.set_facecolor(self.__settings.unchecked_colour)
        phrase = self.__phrases[cell]
        phrase.checked = False

    def mark_default_checked_phrases(self) -> None:
        for cell, phrase in zip(self, self.__phrases):
            if phrase.default_checked:
                self.mark_cell(cell)


class BingoTableController:

    __slots__ = (
        '__table_ctrl',
        '__settings',
        '__phrases',
        '__last_action'
    )

    __table_ctrl: _TableController | None
    __phrases: BingoPhrases | None
    __settings: BingoSettings
    __last_action: str

    def __init__(self, settings: BingoSettings) -> None:
        self.__settings = settings
        self.__table_ctrl = None
        self.__phrases = None
        self.__last_action = ''

    @property
    def table(self) -> Table | None:
        """Get current bingo table.

        Returns
        -------
        matplotlib.Table
            If was generated or loaded properly.
        None
            Otherwise
        """

        if self.__table_ctrl is None:
            return None
        return self.__table_ctrl.table

    @property
    def can_generate_new(self) -> bool:
        """Check if bingo has been used recently.

        Returns
        -------
        `bool` False if bingo was used less than 15 minutes ago, otherwise True.
        """

        try:
            modified_timestamp = os.path.getmtime(self.__bingo_png_path)
        except FileNotFoundError:
            return True

        modified_time = dt.fromtimestamp(modified_timestamp)
        return modified_time + td(minutes=15) < dt.now()

    @property
    def last_action(self) -> str:
        return self.__last_action

    @property
    def _table_ctrl(self) -> _TableController:
        """Get _TableController.

        Raises
        ------
        ControllerNotLoaded
            _TableController is None.
        """

        if self.__table_ctrl is None:
            raise ControllerNotLoaded('_TableController is None')
        return self.__table_ctrl

    @property
    def __bingo_png_path(self) -> Path:
        return self.__settings.dir_path / 'bingo.png'

    def get_phrase(self, field: str) -> Cell:
        """Get phrase using position.

        Raises
        ------
        ControllerNotLoaded
            Bingo Table Controller is not loaded.
        ValueError
            field is invaild.
        KeyError
            Cell with this field not exists.
        """

        return self._table_ctrl[(field[0], int(field[1]))]

    def mark_phrase(self, field: str) -> None:
        """Mark phrase in bingo.

        Set last_action that a field has been marked.

        Parameters
        ----------
        field: `str`
            Two length string with column name and row index (e.g. `B2`)

        Raises
        ------
        ControllerNotLoaded
            Bingo Table Controller is not loaded.
        CellIsMarked
            Phrase is already marked.
        KeyError
            Phrase with this field not exists.
        TypeError || ValueError
            field is invaild.
        """

        cell = self._table_ctrl[(field[0], int(field[1]))]
        self._table_ctrl.mark_cell(cell)
        try:
            self._table_ctrl.win_ctrl.check_win(field)
        except Exception as e:
            from utils.console import Console
            Console.error('asdf', exception=e)

        text = BingoUtils.get_text_from_cell(cell, add_bslsh_bfr_strsk=True)
        self.__last_action = f'Zaznaczono: **{text}**'

    def unmark_phrase(self, field: str) -> None:
        """Unmark phrase in bingo.

        Set last_action that a field has been unmarked.

        Parameters
        ----------
        field: `str`
            Two length string with column name and row index (e.g. `B2`)

        Raises
        ------
        ControllerNotLoaded
            Bingo Table Controller is not loaded.
        CellIsNotMarked
            Phrase is not marked.
        KeyError
            Phrase with this field not exists.
        TypeError || ValueError
            field is invaild.
        """

        cell = self._table_ctrl[(field[0], int(field[1]))]
        self._table_ctrl.unmark_cell(cell)
        self._table_ctrl.win_ctrl.uncheck_win(field)

        text = BingoUtils.get_text_from_cell(cell, add_bslsh_bfr_strsk=True)
        self.__last_action = f'Odznaczono: **{text}**'

    def generate(self) -> Table:
        """Generate bingo table.

        Load phrases from ./bingo_phrases.json and shuffle them.

        Set last_action that a new bingo has been generated.`

        Raises
        ------
        OSError
            File with phrases not exists or cannot be loaded.
        JSONDecodeError
            Json is invaild.
        IndexError
            File with phrases contained too few values
        """

        self.__phrases = BingoPhrases()
        self.__phrases.load(self.__settings.dir_path)
        self.__phrases.shuffle(self.__settings)

        table = BingoTableGenerator.generate(
            self.__settings, self.__phrases
        )
        self.__table_ctrl = _TableController(
            table, self.__settings, self.__phrases
        )
        self.__table_ctrl.mark_default_checked_phrases()

        self.__last_action = "**WYGENEROWANO NOWE BINGO**"
        return table

    @staticmethod
    def load(dir_path: Path) -> BingoTableController:
        """Load controller from last `.pickle` file.

        Raises
        ------
        OSError
            File cannot be loaded.
        """

        return pickle.load(open(dir_path / 'pickles/last.pickle', 'rb'))

    @staticmethod
    def load_from_msg(message_id: int, dir_path: Path) -> BingoTableController:
        """Load controller from `<message_id>.pickle` file.

        Set last_action that a bingo has been loaded from file.

        Raises
        ------
        OSError
            File cannot be loaded.
        """

        path = dir_path / 'pickles' / f'{message_id}.pickle'
        ctrl: BingoTableController = pickle.load(open(path, 'rb'))

        ctrl.__last_action = '**ZAŁADOWANO BINGO**'
        return ctrl

    def new(self, *, settings: BingoSettings | None = None) -> BingoTableController:
        if settings is not None:
            return BingoTableController(settings)
        return BingoTableController(self.__settings)

    @property
    def dc_file_png(self) -> nextcord.File:
        """Get bingo picture in a nextcord.File class.
        Picture will be loaded from ./bingo.png.
        """

        return nextcord.File(self.__bingo_png_path)

    def save_png(self) -> None:
        """Save bingo table as `.png`.

        Raises
        ------
        Something for sure
            but it's not included in the matplotlib.pyplot.savefig docs
            .. or I'm too lazy to look for it :)
        """

        plt.savefig(
            self.__bingo_png_path,
            bbox_inches='tight',
            dpi=100,
            transparent=True
        )

    def serialize(self, message_id: int) -> None:
        """Save this class to `./pickles/<message_id>.pickle`.

        Create `./pickles/` if not exists.

        Raises
        ------
        OSError
            Cannot open file.
        """

        pickles_path = self.__settings.dir_path / 'pickles'
        if not pickles_path.exists():
            os.mkdir(pickles_path)

        file = pickles_path / f'{message_id}.pickle'
        pickle.dump(self, open(file, 'wb'))

        last_file = pickles_path / 'last.pickle'
        pickle.dump(self, open(last_file, 'wb'))
