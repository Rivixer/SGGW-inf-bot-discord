# SPDX-License-Identifier: MIT
"""A module for printing information to the console.

All information is added to the `logs/<bot_launch_date>.log` file.

Examples
-------- ::

    from sggwbot.console import Console, FontColour
    
    Console.info("Hello World!")
    Console.debug("Hello World!")
    Console.warn("Hello World!")
    Console.specific("Hello World!", "TEST", FontColour.RED)
"""

from __future__ import annotations

import atexit
import datetime as dt
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import ClassVar, NoReturn

_DEBUG = True


class FontColour(Enum):
    """An Enum for the colours of the text in the console.

    Examples
    --------

    Uses print function: ::

        from sggwbot.console import FontColour
        print(f"{FontColour.RED}Hello World!{FontColour.RESET}")

    Uses Console class: ::

        from sggwbot.console import Console, FontColour
        Console.specific("Hello World!", "TEST", FontColour.RED)
    """

    GREY = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PINK = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


class Console:
    """Represents a class for printing information to the console.

    All information is added to the `logs/<bot_launch_date>.log` file.

    Examples
    -------- ::

        from sggwbot.console import Console

        Console.info("Hello World!")
        Console.debug("Hello World!")
        Console.warn("Hello World!")
    """

    _logs: ClassVar[list[str]] = []
    _file_path: ClassVar[Path | None] = None
    _last_message_time: ClassVar[dt.date | None] = None

    @classmethod
    @property
    def _logs_directory(cls) -> Path:
        directory = Path("logs/")
        if not directory.exists():
            directory.mkdir()
            Console.warn(f"Directory {directory} has been created.")
        return directory

    @classmethod
    def _register_atexit(cls):
        cls.debug("REGISTER ATEXIT")
        atexit.register(cls._append_to_file)

    @classmethod
    @property
    def _filename(cls) -> str:
        """The name of the file where the logs will be stored.
        Contains the current datetime in the format yy-mm-dd_HH-MM-SS.
        """

        now = str(dt.datetime.now().replace(microsecond=0))
        return now.replace(" ", "_").replace(":", "-")

    @classmethod
    def _create_file_path(cls) -> None:
        cls._file_path = cls._logs_directory / (cls._filename + ".log")
        with open(cls._file_path, "a", encoding="utf-8") as f:
            f.write(f"DEBUG = {_DEBUG}\n")

    @classmethod
    def _append_to_file(cls) -> None:
        if cls._file_path is None:
            cls._create_file_path()

        file_path: Path = cls._file_path  # type: ignore
        with open(file_path, "a", encoding="utf-8") as f:
            for log in cls._logs:
                f.writelines(log + "\n")

    @classmethod
    def _print_to_console(
        cls,
        text: str,
        type_: str,
        color: FontColour,
        *,
        bold_text: bool,
        bold_type: bool,
        exception: Exception | str | None = None,
    ) -> None:
        date = dt.datetime.now().strftime("%d.%m.%y %H:%M:%S")
        reset = "\033[0m"

        _bold_text = "\033[1m" if bold_text else ""
        _bold_type = "\033[1m" if bold_type else ""

        if isinstance(exception, Exception):
            exc = "\n" + traceback.format_exc()
        elif isinstance(exception, str):
            exc = "| " + exception
        else:
            exc = ""

        if exc.strip() == "NoneType: None":
            exc = "\n"

        print(
            f"[{date}] {color.value}{_bold_type}[{type_}]{reset} "
            f"{color.value}{_bold_text}{text} {exc}{reset}"
        )

        cls._logs.append(f"[{date}] <{type_}> {text}")

    @classmethod
    def info(cls, text: str, *, bold_type: bool = True, bold_text: bool = True) -> None:
        """Prints information in blue to the console."""
        color = FontColour.BLUE
        cls._print_to_console(
            text, "INFO", color, bold_text=bold_text, bold_type=bold_type
        )
        cls._append_to_file()

    @classmethod
    def debug(
        cls, text: str, *, bold_type: bool = True, bold_text: bool = False
    ) -> None:
        """Prints debug information in grey to the console only if `._DEBUG` is True."""
        if _DEBUG:
            color = FontColour.GREY
            cls._print_to_console(
                text, "DEBUG", color, bold_text=bold_text, bold_type=bold_type
            )
            cls._append_to_file()

    @classmethod
    def specific(
        cls,
        text: str,
        type_: str,
        colour: FontColour,
        *,
        bold_type: bool = False,
        bold_text: bool = False,
    ) -> None:
        """Prints information to the console with the specified message type and colour."""
        cls._print_to_console(
            text, type_, colour, bold_text=bold_text, bold_type=bold_type
        )
        cls._append_to_file()

    @classmethod
    def warn(
        cls,
        text: str,
        *,
        bold_type: bool = True,
        bold_text: bool = True,
        exception: Exception | None = None,
    ) -> None:
        """Prints a warning in yellow in the console.

        If an exception is given, it also prints the traceback.
        """

        color = FontColour.YELLOW
        cls._logs.append(f'\n{" WARNING ":-^35}')
        cls._print_to_console(
            text,
            "WARN",
            color,
            bold_text=bold_text,
            bold_type=bold_type,
            exception=exception,
        )
        if exception:
            cls._logs.append(traceback.format_exc())
        cls._logs.append("-" * 37 + "\n")
        cls._append_to_file()

    @classmethod
    def error(
        cls,
        text: str,
        *,
        bold_type: bool = False,
        bold_text: bool = False,
        exception: Exception | None = None,
    ) -> None:
        """Prints an error in red to the console.

        If an exception is given, it also prints the traceback.
        """
        color = FontColour.RED
        cls._logs.append(f'\n{" ERROR ":-^38}')
        cls._print_to_console(
            text,
            "ERROR",
            color,
            bold_text=bold_text,
            bold_type=bold_type,
            exception=exception,
        )
        if exception:
            cls._logs.append(traceback.format_exc())
        cls._logs.append("-" * 41 + "\n")
        cls._append_to_file()

    @classmethod
    def important_error(
        cls,
        text: str,
        exception: Exception,
        *,
        bold_type: bool = True,
        bold_text: bool = True,
    ) -> None:
        """Prints an error with traceback in red to the console."""
        color = FontColour.RED
        cls._logs.append(f'\n{" IMPORTANT ERROR ":-^33}')
        cls._print_to_console(
            text,
            "!ERROR!",
            color,
            bold_text=bold_text,
            bold_type=bold_type,
            exception=exception,
        )
        cls._logs.append(traceback.format_exc())
        cls._logs.append("-" * 41 + "\n")
        cls._append_to_file()

    @classmethod
    def critical_error(cls, text: str, exception: Exception) -> NoReturn:
        """Prints an error with traceback in red to the console and exits the program."""
        cls._logs.append(f'\n{" CRITICAL ERROR ":=^33}')
        cls._print_to_console(
            text,
            "!ERROR!",
            FontColour.RED,
            bold_text=True,
            bold_type=True,
            exception=exception,
        )
        cls._logs.append(f"{exception}\n")
        cls._logs.append(traceback.format_exc())
        cls._append_to_file()
        sys.exit()


Console()
