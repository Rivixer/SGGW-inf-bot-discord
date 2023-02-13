from pathlib import Path
import os

from utils.console import Console


class LineCounter:

    __suffix: str
    __lines: int
    __ignored: list

    def __init__(self, suffix: str) -> None:
        """A suffix of the files to be counted.
        It is already preceded by a dot.
        """

        self.__lines = 0
        self.__suffix = suffix

        try:
            with open('.gitignore') as f:
                self.__ignored = f.read().split('\n')
        except OSError as e:
            self.__ignored = []
            Console.warn(
                f'Cannot open \'.gitignore\' to count lines of code.',
                exception=e
            )

        self.__ignored.extend(['.git', '.gitignore'])

    def __count(self, path: Path) -> None:
        for item in os.listdir(path):
            if item in self.__ignored:
                continue
            current_path = path / item
            if current_path.is_dir():
                self.__count(current_path)
            if item.endswith(f'.{self.__suffix}'):
                try:
                    with open(current_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except OSError as e:
                    Console.warn(
                        f'Cannot open {current_path} to count lines of code.',
                        exception=e
                    )
                else:
                    self.__lines += len(lines)

    def count_lines_of_code(self) -> int:
        """Returns number of lines of files including empty lines."""

        root_dir = Path(os.path.abspath(os.curdir))
        self.__count(root_dir)
        return self.__lines
