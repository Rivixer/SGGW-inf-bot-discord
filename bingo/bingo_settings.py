from pathlib import Path
import re
import os

from utils.console import Console


class BingoSettings:

    __slots__ = (
        '__folder_name',
        '__cell_colour',
        '__cell_colour_checked',
        '__index_colour',
        '__index_colour_checked',
        '__dim_cols',
        '__dim_rows'
    )

    def __init__(
        self,
        *,
        folder_name: str,
        cell_colour: str,
        cell_colour_checked: str,
        index_colour: str,
        index_colour_checked: str,
        dim_cols: int,
        dim_rows: int
    ) -> None:
        """Generating Bingo table settings.

        Give colour in hexadecimal format,
        e.g. `#FF0000` means red.

        Dimentions given are default.
        It will be used if additional argument,
        in generating bingo command,
        will be not added.

        Raises
        ------
        TypeError
            Type of variable sent in init is invalid.
        ValueError
            Value of variable sent in init is invaild.
        """

        self.__folder_name = folder_name
        self.__create_folder_if_not_exists()

        colour_modules = {
            'cell_colour': cell_colour,
            'cell_colour_checked': cell_colour_checked,
            'index_colour': index_colour,
            'index_colour_checked': index_colour_checked,
        }

        for name, value in colour_modules.items():
            value = value.upper()
            self.__validate_colour(name, value)
            setattr(self, f'_{self.__class__.__name__}__{name}', value)

        dim_modules = {
            'dim_cols': dim_cols,
            'dim_rows': dim_rows,
        }

        for name, value in dim_modules.items():
            self.__validate_dim(name, value)
            setattr(self, f'_{self.__class__.__name__}__{name}', value)

    @staticmethod
    def __validate_colour(name: str, value: str) -> None:
        hex_colour_regex = r'^#[0-9A-F]{6}$'

        if not isinstance(value, str):
            raise TypeError(f'{name} must be str.')
        if not re.match(hex_colour_regex, value):
            raise ValueError(
                f'{name} must be hexadecimal and starts with \'#\'.'
            )

    @staticmethod
    def __validate_dim(name: str, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f'{name} must be int.')
        if isinstance(value, int) and not (0 < value < 10):
            raise ValueError(
                f'{name} must be between 0 and 10'
            )

    def __create_folder_if_not_exists(self) -> None:
        if not self.dir_path.exists():
            os.mkdir(self.dir_path)
            Console.other(
                f'Stworzono {self.dir_path}',
                type='bingo_settings'
            )

    @property
    def dir_path(self) -> Path:
        return Path(f'bingo/{self.__folder_name}')

    @property
    def no_of_cells(self) -> int:
        return self.__dim_cols * self.__dim_rows

    @property
    def checked_colour(self) -> str:
        return self.__cell_colour

    @property
    def unchecked_colour(self) -> str:
        return self.__cell_colour_checked

    @property
    def index_colour(self) -> str:
        return self.__index_colour

    @property
    def index_checked_colour(self) -> str:
        return self.__index_colour_checked

    @property
    def dim_cols(self) -> int:
        return self.__dim_cols

    @dim_cols.setter
    def dim_cols(self, item) -> None:
        if not isinstance(item, int):
            raise TypeError("dim_cols must be int")
        if not (0 < item < 10):
            raise ValueError('dim_rows must be between 0 and 10')
        self.__dim_cols = item

    @property
    def dim_rows(self) -> int:
        return self.__dim_rows

    @dim_rows.setter
    def dim_rows(self, item) -> None:
        if not isinstance(item, int):
            raise TypeError("dim_rows must be int")
        if not (0 < item < 10):
            raise ValueError('dim_rows must be between 0 and 10')
        self.__dim_cols = item
