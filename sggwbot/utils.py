# SPDX-License-Identifier: MIT
"""A module containing utility classes and functions."""

import asyncio
import datetime as dt
import functools
import os
import re
import traceback
from abc import ABC
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Literal,
    ParamSpec,
)

import nextcord
from nextcord.channel import TextChannel
from nextcord.interactions import Interaction

from sggwbot.console import Console, FontColour

if TYPE_CHECKING:
    from nextcord.member import Member


_P = ParamSpec("_P")
_FUNC = Callable[Concatenate[Any, Interaction, _P], Awaitable[Any]]


class InteractionUtils(ABC):
    """A class containing static methods that can be used to decorate commands.

    This class should not be instantiated.
    """

    @staticmethod
    def _command_name(interaction: Interaction) -> str:
        """Returns the name of the command that was run."""
        command = interaction.application_command
        if command is None:
            raise TypeError("Command was None")
        return command.qualified_name

    @staticmethod
    def with_log(
        colour: FontColour = FontColour.PINK, show_channel: bool = False
    ) -> Callable[[_FUNC], _FUNC]:
        """Logs information about the user who ran a decorated command to the console.

        This decorator should be placed after decorators that set a function as a command.

        If the command is a subcommand, its name will be preceded by its parent name.

        Parameters
        ----------
        colour: :class:`FontColour`
            The colour of the log message.
        show_channel: :class:`bool`
            Whether to show the channel name in the log message.
        """

        def decorator(func: _FUNC) -> _FUNC:
            @functools.wraps(func)
            async def wrapper(
                self,
                interaction: Interaction,
                *args: _P.args,
                **kwargs: _P.kwargs,
            ) -> Awaitable[Any]:
                type_info = "SLASH_COMMAND"
                command_name = InteractionUtils._command_name(interaction)
                user: Member = interaction.user  # type: ignore
                user_info = f"{user.display_name} ({user.name}#{user.discriminator})"
                kwargs_info = " ".join(
                    f"{k}:{v}" for k, v in kwargs.items() if v is not None
                )

                if show_channel:
                    channel = interaction.channel
                    if isinstance(channel, TextChannel):
                        type_info += f"/{channel.name}"

                Console.specific(
                    f"{user_info} used /{command_name} {kwargs_info}",
                    type_info,
                    colour,
                )

                return await func(self, interaction, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def with_info(
        *,
        before: str | None = None,
        after: str | None = None,
        catch_errors: bool = False,
        with_traceback: bool = True,
        additional_errors: list[type[Exception]] | None = None,
    ) -> Callable[[_FUNC], _FUNC]:
        """Responds to the interaction an ephemeral message to the user who ran a decorated command.

        This decorator should be placed after decorators that set a function as a command.

        If the interaction has already been responded to, it edits the message content.

        Examples
        --------

        After invoking the command below,
        first response to the interaction will be 'msg_before'.
        Then the response content will be changed to 'msg_foo'
        and finally it will be changed to 'msg_after'. ::

            @nextcord.slash_command()
            @with_info(before='msg_before', after='msg_after')
            async def foo(self, interaction: Interaction) -> None:
                msg = await interaction.original_message()
                await msg.edit(content='msg_foo')

        After invoking the command below,
        if the user sent 0 as 'b' parameter,
        an error will occur and will be printed as an interaction response. ::

            @nextcord.slash_command()
            @with_info(catch_errors=True, additional_errors=[ZeroDivisionError])
            async def foo(self, interaction: Interaction, a: int, b: int) -> None:
                await interaction.respond.send_message(f'{a} / {b} = {a/b})

        Parameters
        ----------
        before: :class:`str`
            The message to send before the command is run.
        after: :class:`str`
            The message to send after the command is run.
        catch_errors: :class:`bool`
            Whether to catch errors that occur while running the command.
            Defaults to ``False``.
        with_traceback: :class:`bool`
            Whether to include a traceback in the error message.
            Defaults to ``True``.
        additional_errors: `list[type[:class:Exception]]` | `None`
            A list of additional errors to catch.
            Defaults to ``None``.

        Raises
        ------
        TypeError
            If the command is not a slash command.

        Notes
        -----
        If `catch_errors` is ``True``, the following errors will be caught:
        - :class:`AttributeError`
        - :class:`IndexError`
        - :class:`KeyError`
        - :class:`TypeError`
        - :class:`ValueError`
        - :class:`nextcord.DiscordException`
        - Any errors in `additional_errors`
        """

        def decorator(func: _FUNC) -> _FUNC:
            @functools.wraps(func)
            async def wrapper(
                self,
                interaction: Interaction,
                *args: _P.args,
                **kwargs: _P.kwargs,
            ) -> Awaitable[Any] | None:
                if before:
                    await interaction.response.send_message(
                        before.format(**kwargs), ephemeral=True
                    )

                if catch_errors:
                    try:
                        result = await func(self, interaction, *args, **kwargs)
                    except (
                        AttributeError,
                        IndexError,
                        KeyError,
                        TypeError,
                        ValueError,
                        nextcord.DiscordException,
                        *(additional_errors or []),
                    ) as e:
                        err_msg = f"** [ERROR] ** {e}"

                        if with_traceback:
                            trcbck = traceback.format_exc()
                            err_msg += f"\n```py\n{trcbck}```"

                        if len(err_msg) > 2000:
                            err_msg = f"{err_msg[:496]}\n\n...\n\n{err_msg[-1496:]}"

                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                err_msg, ephemeral=True
                            )
                        else:
                            msg = await interaction.original_message()
                            await msg.edit(content=err_msg)
                        comm_name = InteractionUtils._command_name(interaction)
                        return Console.error(
                            f"Error while using /{comm_name}.", exception=e
                        )
                else:
                    result = await func(self, interaction, *args, **kwargs)

                if after:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            after.format(**kwargs), ephemeral=True
                        )
                    else:
                        msg = await interaction.original_message()
                        if not msg.content.startswith("**[ERROR]**"):
                            await msg.edit(content=after.format(**kwargs))

                return result

            return wrapper

        return decorator


class PathUtils(ABC):  # pylint: disable=too-few-public-methods
    """A class containing utility methods for paths."""

    @staticmethod
    def convert_classname_to_filename(obj: object) -> str:
        """Converts a class name to a filename.

        Parameters
        ----------
        obj: :class:`object`
            The object to convert.

        Returns
        -------
        :class:`str`
            The converted class name.

        Examples
        -------- ::

            class ClassFoo:
                pass

            obj = ClassFoo()
            convert_classname_to_filename(obj)  # 'class_foo'

        Notes
        -----
        This method is used to convert a class name to a filename
        when saving a class to a file.
        """

        return re.sub("(?<!^)(?=[A-Z])", "_", obj.__class__.__name__).lower()


class ProjectUtils(ABC):  # pylint: disable=too-few-public-methods
    """A class containing utility methods for the project.

    This class should not be instantiated.
    """

    @staticmethod
    def lines_of_code() -> int:
        """Returns the number of lines of code in the project.

        Returns
        -------
        :class:`int`
            The number of lines of code in the project.

        Notes
        -----
        This method counts lines of code in the project
        by counting lines of code in all Python files
        in the project directory except for the ones
        that are ignored by the '.gitignore' file.
        """

        try:
            with open(".gitignore", "r", encoding="utf-8") as f:
                ignored = f.read().split("\n")
        except OSError as e:
            ignored = []
            Console.warn(
                "Cannot open the '.gitignore' file to count lines of code properly.",
                exception=e,
            )

        ignored.extend([".git", ".gitignore"])
        result = [0]

        def count(path: Path, result: list[int]) -> None:
            for item in os.listdir(path):
                if item in ignored:
                    continue
                current_path = path / item
                if current_path.is_dir():
                    count(current_path, result)
                if item.endswith(".py"):
                    try:
                        with open(current_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                    except OSError as e:
                        Console.warn(
                            f"Cannot open {current_path} to count lines of code.",
                            exception=e,
                        )
                    else:
                        result[0] += len(lines)

        root_dir = Path(os.path.abspath(os.curdir))
        count(root_dir, result)
        return result[0]


async def wait_until_midnight() -> Literal[True]:
    """|coro|

    Waits until midnight and returns ``True``.

    Examples
    -------- ::

        while await wait_until_midnight():
            print("It's midnight!")
    """

    today = dt.datetime.now()
    tomorrow = today + dt.timedelta(days=1)
    midnight = dt.datetime(
        year=tomorrow.year,
        month=tomorrow.month,
        day=tomorrow.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    time_until_midnight = midnight - today
    await asyncio.sleep(time_until_midnight.seconds)
    return True
