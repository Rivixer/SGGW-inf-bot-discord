import pytest
from dataclasses import dataclass

from bingo.bingo_table_generator import BingoTableGenerator


class TestBingoTableGenerator:

    @dataclass
    class __Settings:
        dim_cols: int
        dim_rows: int

    def test_matrix_item(self):
        settings = self.__Settings(2, 2)
        m = BingoTableGenerator._BingoTableController__matrix(  # type: ignore
            settings.dim_cols, settings.dim_rows, 'a'
        )
        assert m == [['a', 'a'], ['a', 'a']]

    def test_matrix_item_with_irregular_shape(self):
        settings = self.__Settings(3, 1)
        m = BingoTableGenerator._BingoTableController__matrix(  # type: ignore
            settings.dim_cols, settings.dim_rows, 'a'
        )
        assert m == [['a', 'a', 'a']]

        settings = self.__Settings(2, 4)
        m = BingoTableGenerator._BingoTableController__matrix(  # type: ignore
            settings.dim_cols, settings.dim_rows, 'a'
        )
        assert m == [['a', 'a'], ['a', 'a'], ['a', 'a'], ['a', 'a']]

    def test_matrix_list(self):
        settings = self.__Settings(2, 2)
        m = BingoTableGenerator._BingoTableController__matrix(  # type: ignore
            settings.dim_cols, settings.dim_rows, ['a', 'b', 'c', 'd']
        )
        assert m == [['a', 'b'], ['c', 'd']]

    def test_matrix_too_short_list(self):
        settings = self.__Settings(2, 2)
        with pytest.raises(IndexError):
            BingoTableGenerator._BingoTableController__matrix(  # type: ignore
                settings.dim_cols, settings.dim_rows, ['a', 'b']
            )

    def test_matrix_generator(self):
        def gen():
            i = 97
            while True:
                yield chr(i)
                i += 1

        settings = self.__Settings(2, 2)
        m = BingoTableGenerator._BingoTableController__matrix(  # type: ignore
            settings.dim_cols, settings.dim_rows, gen()
        )
        assert m == [['a', 'b'], ['c', 'd']]
