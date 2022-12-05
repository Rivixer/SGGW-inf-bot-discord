from typing import overload, Generator
from matplotlib import pyplot as plt
from matplotlib.table import Table
from abc import ABC

from .bingo_settings import BingoSettings
from .bingo_phrases import BingoPhrases
from .bingo_utils import BingoUtils

_MATRIX = list[list[str]]
_COLOR = str | tuple[float, float, float]


class BingoTableGenerator(ABC):

    @classmethod
    def generate(cls, settings: BingoSettings, phrases: BingoPhrases) -> Table:
        """Generate matplotlib.Table using dimentions in settings.

        Raises
        ------
        IndexError
            List contained too few phrases
        ValueError
            Type of phrase is invaild
        """

        plt.figure().clear()
        table = plt.table(
            cellText=cls.__cellText(settings, phrases),
            cellColours=cls.__cellColour(settings),
            cellLoc='center',
            rowLabels=cls.__rowLabels(settings.dim_rows),
            rowColours=cls.__rowColours(settings),
            rowLoc='right',
            colLabels=cls.__colLabels(settings.dim_cols),
            colColours=cls.__colColours(settings),
            colLoc='center',
            loc='center',
        )

        cls.__scale_table(table, settings.dim_rows, settings.dim_cols)
        cls.__set_colname_height(table, settings.dim_cols)
        cls.__remove_axes()
        return table

    @overload
    @staticmethod
    def __matrix(x: int, y: int, item: str) -> _MATRIX:
        """Generate matrix x*y. Item will be in all cells.

        Raises
        ------
        TypeError
            Type of item is invaild
        """

    @overload
    @staticmethod
    def __matrix(x: int, y: int, item: list[str]) -> _MATRIX:
        """Generate matrix x*y.
        List must have minimum the same number of elements as the matrix.

        Raises
        ------
        IndexError
            List contained too few values
        TypeError
            Type of item in list is invaild
        """

    @overload
    @staticmethod
    def __matrix(x: int, y: int, item: Generator[str, None, None]) -> _MATRIX:
        """Generate matrix x*y.
        Generator must have minimum the same number of elements as the matrix.

        Raises
        ------
        StopIteration
            Generator returned too few values
        TypeError
            Type of item in list is invaild
        """

    @staticmethod
    def __matrix(x: int, y: int, item: str | Generator[str, None, None] | list[str]) -> _MATRIX:
        if not isinstance(item, (Generator, list, str)):
            raise TypeError(
                'item must be str, list[str] or Generator[str, None, None]'
            )

        if isinstance(item, str):
            return [[item] * x] * y

        matrix: _MATRIX = [[]]
        for col in range(x):
            for row in range(y):
                if isinstance(item, Generator):
                    obj = next(item)
                elif isinstance(item, list):
                    obj = item[row + col*y]
                    if not isinstance(obj, str):
                        raise TypeError('item in list must be str')

                try:
                    matrix[col].append(obj)
                except IndexError:
                    matrix.append([obj])

        return matrix

    @classmethod
    def __cellText(cls, settings: BingoSettings, phrases: BingoPhrases) -> _MATRIX:
        max_len = max(max(map(len, phrase.text.split()))
                      for phrase in phrases[:settings.no_of_cells])

        phrases_text = list(map(
            lambda i: BingoUtils.split_words(
                i.text, max_chars=max_len
            ), phrases)
        )

        return cls.__matrix(settings.dim_cols, settings.dim_rows, phrases_text)

    @classmethod
    def __cellColour(cls, settings: BingoSettings) -> _MATRIX:
        return cls.__matrix(settings.dim_cols, settings.dim_rows, settings.unchecked_colour)

    @staticmethod
    def __rowLabels(dim_rows: int) -> list[str]:
        return list(map(lambda i: f' {i+1}', range(dim_rows)))

    @staticmethod
    def __rowColours(settings: BingoSettings) -> list[_COLOR]:
        return [settings.index_colour] * settings.dim_rows

    @staticmethod
    def __colLabels(dim_cols: int) -> list[str]:
        return [chr(i+65) for i in range(dim_cols)]

    @staticmethod
    def __colColours(settings: BingoSettings) -> list[_COLOR]:
        return [settings.index_colour] * settings.dim_cols

    @staticmethod
    def __set_colname_height(table: Table, dim_cols: int) -> None:
        for i in range(dim_cols):
            table[(0, i)].set_height(0.05)

    @staticmethod
    def __scale_table(table: Table, dim_rows: int, dim_cols: int) -> None:
        # The magic numbers that make table scale good
        table.scale(0.35 * dim_rows, 0.1 * dim_cols + 5)

    @staticmethod
    def __remove_axes() -> None:
        plt.axis('off')
