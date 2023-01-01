from matplotlib.table import Table
from dataclasses import dataclass

from .bingo_phrases import BingoPhrases
from .bingo_settings import *


@dataclass(slots=True)
class BingoWinController:

    __table: Table
    __settings: BingoSettings
    __phrases: BingoPhrases

    @staticmethod
    def __convert_col(field: str) -> int:
        return ord(field[0].upper()) - ord('A')

    @staticmethod
    def __convert_row(field: str) -> int:
        return int(field[1])

    def __check_horizontal(self, y: int) -> bool:
        for x in range(self.__settings.dim_cols):
            cell = self.__table[(y, x)]
            if not self.__phrases[cell].checked:
                return False
        return True

    def __check_vertical(self, x: int) -> bool:
        for y in range(1, self.__settings.dim_rows + 1):
            cell = self.__table[(y, x)]
            if not self.__phrases[cell].checked:
                return False
        return True

    def __check_diagonal1(self, x: int, y: int) -> bool:
        if self.__settings.dim_cols != self.__settings.dim_rows:
            return False

        if x + 1 != y:
            return False

        for i in range(self.__settings.dim_cols):
            cell = self.__table[(i+1, i)]
            if not self.__phrases[cell].checked:
                return False
        return True

    def __check_diagonal2(self, x: int, y: int) -> bool:
        if self.__settings.dim_cols != self.__settings.dim_rows:
            return False

        if x + y != self.__settings.dim_rows:
            return False

        for i in range(1, self.__settings.dim_cols + 1):
            cell = self.__table[(i, self.__settings.dim_cols - i)]
            if not self.__phrases[cell].checked:
                return False
        return True

    def check_win(self, field: str) -> None:
        x = self.__convert_col(field)
        y = self.__convert_row(field)

        if self.__settings.way_to_win is WayToWinBingo.ONELINE:
            if self.__check_horizontal(y):
                self.__mark_table_horizontal(y)
            if self.__check_vertical(x):
                self.__mark_table_vertical(x)
            if self.__check_diagonal1(x, y):
                self.__mark_table_diagonal1()
            if self.__check_diagonal2(x, y):
                self.__mark_table_diagonal2()

    def uncheck_win(self, field: str) -> None:
        x = self.__convert_col(field)
        y = self.__convert_row(field)

        if self.__settings.way_to_win is WayToWinBingo.ONELINE:
            if not self.__check_horizontal(y):
                self.__unmark_table_horizontal(y)
            if not self.__check_vertical(x):
                self.__unmark_table_vertical(x)
            if not self.__check_diagonal1(x, y):
                self.__unmark_table_diagonal1()
            if not self.__check_diagonal2(x, y):
                self.__unmark_table_diagonal2()

    def __mark_table_horizontal(self, y: int) -> None:
        for x in range(self.__settings.dim_cols):
            self.__table[(y, x)].set_facecolor(self.__settings.win_colour)

    def __mark_table_vertical(self, x: int) -> None:
        for y in range(1, self.__settings.dim_cols + 1):
            self.__table[(y, x)].set_facecolor(self.__settings.win_colour)

    def __mark_table_diagonal1(self) -> None:
        for i in range(1, self.__settings.dim_cols + 1):
            self.__table[(i, i-1)].set_facecolor(self.__settings.win_colour)

    def __mark_table_diagonal2(self) -> None:
        for i in range(1, self.__settings.dim_cols + 1):
            cell = self.__table[(i, self.__settings.dim_cols - i)]
            cell.set_facecolor(self.__settings.win_colour)

    def __unmark_table_horizontal(self, y: int) -> None:
        for x in range(self.__settings.dim_cols):
            if (
                self.__check_diagonal1(x, y)
                or self.__check_diagonal2(x, y)
                or self.__check_vertical(x)
            ):
                continue
            cell = self.__table[(y, x)]
            if self.__phrases[cell].checked:
                cell.set_facecolor(self.__settings.checked_colour)

    def __unmark_table_vertical(self, x: int) -> None:
        for y in range(1, self.__settings.dim_cols + 1):
            if (
                self.__check_diagonal1(x, y)
                or self.__check_diagonal2(x, y)
                or self.__check_horizontal(y)
            ):
                continue

            cell = self.__table[(y, x)]
            if self.__phrases[cell].checked:
                cell.set_facecolor(self.__settings.checked_colour)

    def __unmark_table_diagonal1(self) -> None:
        for i in range(1, self.__settings.dim_cols + 1):
            y, x = i, i - 1
            if self.__check_horizontal(y) or self.__check_vertical(x) or self.__check_diagonal1(x, y):
                continue
            cell = self.__table[(y, x)]
            if self.__phrases[cell].checked:
                cell.set_facecolor(self.__settings.checked_colour)
            if self.__check_diagonal2(x, y):
                self.__mark_table_diagonal2()

    def __unmark_table_diagonal2(self) -> None:
        for i in range(1, self.__settings.dim_cols + 1):
            y, x = i, self.__settings.dim_cols - i
            if self.__check_horizontal(y) or self.__check_vertical(x) or self.__check_diagonal2(x, y):
                continue
            cell = self.__table[(y, x)]
            if self.__phrases[cell].checked:
                cell.set_facecolor(self.__settings.checked_colour)
            if self.__check_diagonal1(x, y):
                self.__mark_table_diagonal1()
