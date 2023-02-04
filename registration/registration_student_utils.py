from pathlib import Path
from abc import ABC

from utils.console import Console, FontColour


class RegistrationStudentUtils(ABC):

    @staticmethod
    def __get_file_path() -> Path:
        """Returns Path to txt where student indexes are stored.

        If the file doesn't exist, it creates new one.
        """

        path = Path('registration/student_indexes.txt')
        if not path.exists():
            path.touch()
            Console.specific(
                f'{path} has been created',
                'Registration', FontColour.YELLOW
            )
        return path

    @classmethod
    def is_student(cls, index_no: str) -> bool | None:
        """Returns true if the student's index number
            is contained in the student_indexes.txt file.

        If the file cannot be opened, it returns None
            and prints an exception to the console.

        Otherwise, it returns False.
        """

        path = cls.__get_file_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                indexes = list(map(str.strip, f.readlines()))
        except Exception as e:
            Console.error(f'Cannot open {path}', exception=e)
            return None

        if len(indexes) == 0:
            Console.warn(f'The file {path} is empty.')

        return index_no in indexes
