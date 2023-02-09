from enum import Enum
import datetime as dt
import traceback
import atexit
import sys
import os


class FontColour(Enum):
    GRAY = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    PINK = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'


_LOGS_FOLDER = 'logs/'


class Console:
    __logs = []
    __last_message_time: dt.date | None = None

    def __init__(self) -> None:
        self.file_name = self.__get_filename()
        self.__create_folder_if_not_exists()
        atexit.register(self.__save_to_file)

    @staticmethod
    def __new_day_info(func):
        """A decorator that prints info about the new day
        if the last log was sent another day.
        """

        def wrapper(*args, **kwargs):
            current_date = dt.datetime.now().date()
            if (
                Console.__last_message_time is None
                or Console.__last_message_time != current_date
            ):
                Console.__last_message_time = current_date
                msg = f'{current_date.strftime("%d-%m-%Y"):_^22}'
                logs.__logs.append(f'\n{msg}\n')
                print(msg)

            func(*args, **kwargs)

        return wrapper

    @staticmethod
    def __get_filename() -> str:
        """Returns the filename where logs will be stored.
        The filename contains the current datetime.
        """

        now = str(dt.datetime.now().replace(microsecond=0))
        return now.replace(' ', '_').replace(':', '-')

    @staticmethod
    def __create_folder_if_not_exists():
        """Creates a folder for logs if it doesn't exist."""
        if not os.path.exists(_LOGS_FOLDER):
            os.mkdir(_LOGS_FOLDER)

    def __save_to_file(self):
        """Saves logs to .txt file. Clears self.__logs."""
        with open(f'{_LOGS_FOLDER}/{self.file_name}.txt', 'a', encoding='utf-8') as f:
            for log in self.__logs:
                f.writelines(log + '\n')

        self.__logs.clear()

    def __add__(self, obj) -> None:
        if not isinstance(obj, str):
            raise TypeError('Only str can be added')
        self.__logs.append(obj)

    @staticmethod
    def __send(
        text: str,
        type: str,
        color: FontColour,
        *,
        bold_text: bool,
        bold_type: bool,
        exception: Exception | str | None = None
    ) -> None:
        """Prints log to the console.
        Adds info to logs."""

        date = dt.datetime.now().strftime("%H:%M:%S")
        reset = '\033[0m'

        _bold_text = '\033[1m' if bold_text else ''
        _bold_type = '\033[1m' if bold_type else ''

        if isinstance(exception, Exception):
            exc = '\n' + traceback.format_exc()
        elif isinstance(exception, str):
            exc = '| ' + exception
        else:
            exc = ""

        if exc.strip() == "NoneType: None":
            exc = "\n"

        print(
            f'[{date}]  {color.value}{_bold_type}[{type}]{reset} '
            f'{color.value}{_bold_text}{text} {exc}{reset}'
        )

        Console.__logs.append(f'[{date}] <{type}> {text}')

    @staticmethod
    @__new_day_info
    def cogs(text: str, *, bold_type: bool = True, bold_text: bool = True) -> None:
        color = FontColour.GREEN
        Console.__send(
            text, "COGS", color,
            bold_text=bold_text,
            bold_type=bold_type
        )
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def info(text: str, *, bold_type: bool = True, bold_text: bool = True) -> None:
        color = FontColour.BLUE
        Console.__send(
            text, 'INFO', color,
            bold_text=bold_text,
            bold_type=bold_type
        )
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def message(text: str, type: str, *, bold_type: bool = True, bold_text: bool = False) -> None:
        color = FontColour.CYAN
        Console.__send(
            text, type, color,
            bold_text=bold_text,
            bold_type=bold_type
        )
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def specific(
        text: str,
        type: str,
        colour: FontColour,
        *,
        bold_type: bool = False,
        bold_text: bool = False
    ) -> None:
        Console.__send(
            text, type, colour,
            bold_text=bold_text,
            bold_type=bold_type
        )
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def warn(
        text: str,
        *,
        bold_type: bool = True,
        bold_text: bool = True,
        exception: Exception | None = None
    ) -> None:
        color = FontColour.YELLOW
        logs.__logs.append(f'\n{" WARNING ":"-"^30}')
        Console.__send(
            text, 'WARN', color,
            bold_text=bold_text,
            bold_type=bold_type,
            exception=exception
        )
        if exception:
            logs.__logs.append(traceback.format_exc())
        logs.__logs.append('-'*37+'\n')
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def error(
        text: str,
        *,
        bold_type: bool = False,
        bold_text: bool = False,
        exception: Exception | None = None
    ) -> None:
        color = FontColour.RED
        logs.__logs.append(f'\n{" ERROR ":"-"^34}')
        Console.__send(
            text, 'ERROR', color,
            bold_text=bold_text,
            bold_type=bold_type, exception=exception
        )
        if exception:
            logs.__logs.append(traceback.format_exc())
        logs.__logs.append('-'*41+'\n')
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def important_error(
        text: str,
        exception: Exception,
        *,
        bold_type: bool = True,
        bold_text: bool = True
    ) -> None:
        color = FontColour.RED
        logs.__logs.append(f'\n{" IMPORTANT ERROR ":"-"^24}')
        Console.__send(
            text, '!ERROR!', color,
            bold_text=bold_text,
            bold_type=bold_type,
            exception=exception
        )
        logs.__logs.append(traceback.format_exc())
        logs.__logs.append('-'*41+'\n')
        logs.__save_to_file()

    @staticmethod
    @__new_day_info
    def critical_error(text: str, exception: Exception):
        """Exits the program."""
        logs.__logs.append(f'\n{" CRITICAL ERROR ":=^33}')
        Console.__send(
            text, '!ERROR!', FontColour.RED,
            bold_text=True,
            bold_type=True,
            exception=exception
        )
        logs.__logs.append(f'{exception}\n')
        logs.__logs.append(traceback.format_exc())
        logs.__save_to_file()
        sys.exit()


logs = Console()
