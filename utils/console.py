import os
import sys
import atexit
import traceback
from enum import Enum
from datetime import datetime as dt
from datetime import timedelta as td


class FontColour(Enum):
    WHITE = ''
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    PINK = '\033[35m'
    CYAN = '\033[36m'


_LOGS_FOLDER = 'logs/'


class Console:
    last_save = dt.now()
    logs = []
    __last_message_time: dt.date = None

    def __new_day_info(func):
        def wrapper(*args, **kwargs):
            current_date = dt.now().date()
            if (
                Console.__last_message_time is None
                or Console.__last_message_time != current_date
            ):
                Console.__last_message_time = current_date
                msg = f'{current_date.strftime("%d-%m-%Y"):_^22}'
                logs.logs.append(f'\n{msg}\n')
                print(msg)

            func(*args, **kwargs)

        return wrapper

    def __init__(self):
        self.file_name = self.__get_file_name()
        self.__create_folder_if_not_exists()
        atexit.register(self.__save_to_file)

    def __get_file_name(self):
        now = str(dt.now().replace(microsecond=0))
        return now.replace(' ', '_').replace(':', '-')

    def __create_folder_if_not_exists(self):
        if not os.path.exists(_LOGS_FOLDER):
            os.mkdir(_LOGS_FOLDER)

    def __try_save_to_file(self):
        if len(self.logs) >= 10 or self.last_save + td(minutes=10) < dt.now():
            self.__save_to_file()

    def __save_to_file(self):
        with open(f'{_LOGS_FOLDER}/{self.file_name}.txt', 'a', encoding='utf-8') as f:
            for log in self.logs:
                f.writelines(log + '\n')

        self.logs = []
        self.last_save = dt.now()

    @staticmethod
    @__new_day_info
    def __send(text: str, type: str, color: str, *, bold_text, bold_type, bold, exception: str | Exception = None):
        date = dt.now().strftime("%H:%M:%S")
        reset = '\033[0m'

        if bold is not False:
            if bold_text or bold:
                bold_text = "\033[1m"
            if bold_type or bold:
                bold_type = "\033[1m"

        if bold_text not in ("\033[1m", ""):
            bold_text = ""
        if bold_type not in ("\033[1m", ""):
            bold_type = ""

        if isinstance(exception, Exception):
            exc = '\n' + traceback.format_exc()
        elif isinstance(exception, str):
            exc = '| ' + exception
        else:
            exc = ""

        if exc.strip() == "NoneType: None":
            exc = "\n"

        print(
            f'[{date}]  {color}{bold_type}[{type}]{reset} '
            f'{color}{bold_text}{text} {exc}{reset}'
        )

    @staticmethod
    def cogs(text: str, *, bold_type: bool = True, bold_text: bool = True, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.GREEN.value
        logs.logs.append(f'[{date}] <COGS> {text}')
        logs.__try_save_to_file()
        Console.__send(text, "COGS", color,
                       bold_text=bold_text, bold_type=bold_type, bold=bold)

    @staticmethod
    def info(text: str, *, bold_type: bool = True, bold_text: bool = True, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.BLUE.value
        logs.logs.append(f'[{date}] <INFO> {text}')
        logs.__try_save_to_file()
        Console.__send(text, 'INFO', color,
                       bold_text=bold_text, bold_type=bold_type, bold=bold)

    @staticmethod
    def message(text: str, type: str, *, bold_type: bool = True, bold_text: bool = False, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.CYAN.value
        logs.logs.append(f'[{date}] {{{type}}} {text}')
        logs.__try_save_to_file()
        Console.__send(text, type, color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold)

    @staticmethod
    def other(text: str, type: str, *, bold_type: bool = False, bold_text: bool = False, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.PINK.value
        logs.logs.append(f'[{date}] {{{type}}} {text}')
        logs.__try_save_to_file()
        Console.__send(text, type, color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold)

    @staticmethod
    def specific(text: str, type: str, colour: FontColour, *, bold_type: bool = False, bold_text: bool = False, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = colour.value
        logs.logs.append(f'[{date}] {{{type}}} {text}')
        logs.__try_save_to_file()

        Console.__send(text, type, color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold)

    @staticmethod
    def warn(text: str, *, bold_type: bool = True, bold_text: bool = True, bold: bool = None, exception: Exception = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.YELLOW.value
        logs.logs.append('\n---------------- WARNING ----------------')
        logs.logs.append(f'[{date}] {text}')
        if exception:
            logs.logs.append(traceback.format_exc())
        logs.logs.append('-----------------------------------------\n')
        logs.__try_save_to_file()

        Console.__send(text, 'WARN', color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold, exception=exception)

    @staticmethod
    def error(text: str, *, bold_type: bool = False, bold_text: bool = False, bold: bool = None, exception: Exception = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.RED.value
        logs.logs.append('\n----------------- ERROR -----------------')
        logs.logs.append(f'[{date}] {text}')
        if exception:
            logs.logs.append(traceback.format_exc())
        logs.logs.append('-----------------------------------------\n')
        logs.__try_save_to_file()

        Console.__send(text, 'ERROR', color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold, exception=exception)

    @staticmethod
    def important_error(text: str, exception: Exception, *, bold_type: bool = True, bold_text: bool = True, bold: bool = None):
        date = dt.now().strftime("%H:%M:%S")
        color = FontColour.RED.value
        logs.logs.append('\n------------ IMPORTANT ERROR ------------')
        logs.logs.append(f'[{date}]')
        logs.logs.append(text)
        logs.logs.append(traceback.format_exc())
        logs.logs.append('-----------------------------------------\n')
        logs.__save_to_file()

        Console.__send(text, '!ERROR!', color, bold_text=bold_text,
                       bold_type=bold_type, bold=bold, exception=exception)

    @staticmethod
    def critical_error(text: str, exception: Exception):
        """Quit the program after this error and save content to logs file."""
        date = dt.now().strftime("%H:%M:%S")
        logs.logs.append('\n============= CRITICAL ERROR =============')
        logs.logs.append(f'[{date}] {text}\n')
        logs.logs.append(f'{exception}\n')
        logs.logs.append(traceback.format_exc())
        logs.__save_to_file()

        Console.__send(text, '!ERROR!', '\033[31m', bold_text=True,
                       bold_type=True, bold=True, exception=exception)

        sys.exit()


logs = Console()
