# SPDX-License-Identifier: MIT
"""A module containing utility classes and functions."""

from __future__ import annotations

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
from nextcord.threads import Thread

from sggwbot.console import Console, FontColour
from sggwbot.errors import ExceptionData

if TYPE_CHECKING:
    from nextcord.member import Member
    from nextcord.user import User


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
        If the command is used in a thread, its name will be preceded
        by the name of the thread's parent channel.

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

                user_info = f"{user.display_name} "
                user_info += f"({MemberUtils.convert_to_string(user)})"

                kwargs_info = " ".join(
                    f"{k}:{v}" for k, v in kwargs.items() if v is not None
                )

                if show_channel:
                    channel = interaction.channel
                    if isinstance(channel, TextChannel):
                        type_info += f"/{channel.name}"
                    if isinstance(channel, Thread):
                        if parent := channel.parent:
                            type_info += f"/{parent.name}/{channel.name}"

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
        catch_exceptions: list[type[Exception] | ExceptionData] | None = None,
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
            @with_info(catch_exceptions=[ZeroDivisionError])
            async def foo(self, interaction: Interaction, a: int, b: int) -> None:
                await interaction.respond.send_message(f'{a} / {b} = {a/b})

        If an error occurs while running the command,
        the traceback will be printed by default.
        You can change this by passing an :class:`ExceptionData` instance
        with ``with_traceback_in_response`` and ``with_traceback_in_log`` parameters. ::

            @nextcord.slash_command()
            @with_info(
                catch_exceptions=[
                    ExceptionData(
                        ZeroDivisionError,
                        with_traceback_in_response=False,
                        with_traceback_in_log=False,
                    )
                ]
            ),
            async def foo(self, interaction: Interaction, a: int, b: int) -> None:
                await interaction.respond.send_message(f'{a} / {b} = {a/b})


        Parameters
        ----------
        before: :class:`str`
            The message to send before the command is run.
        after: :class:`str`
            The message to send after the command is run.
        catch_exceptions: list[type[:class:`Exception` | :class:`ExceptionData`]] | `None`
            An optional list of exception or exception data to catch.
            Defaults to `None`.

        Raises
        ------
        TypeError
            If the command is not a slash command.
        """

        def decorator(func: _FUNC) -> _FUNC:
            @functools.wraps(func)
            async def wrapper(
                self,
                interaction: Interaction,
                *args: _P.args,
                **kwargs: _P.kwargs,
            ) -> Awaitable[Any] | None:
                async def catch_error(exc: Exception, exc_data: ExceptionData) -> None:
                    err_msg = f"** [ERROR] ** {exc}"

                    if exc_data.with_traceback_in_response:
                        trcbck = traceback.format_exc()
                        err_msg += f"\n```py\n{trcbck}```"

                    if len(err_msg) > 2000:
                        err_msg = f"{err_msg[:496]}\n\n...\n\n{err_msg[-1496:]}"

                    if not interaction.response.is_done():
                        await interaction.response.send_message(err_msg, ephemeral=True)
                    else:
                        try:
                            msg = await interaction.original_message()
                            await msg.edit(content=err_msg)
                        except nextcord.errors.NotFound:
                            await interaction.send(err_msg, ephemeral=True)

                    comm_name = InteractionUtils._command_name(interaction)
                    if exc_data.with_traceback_in_log:
                        Console.error(f"Error while using /{comm_name}.", exception=exc)
                    else:
                        Console.error(f"Error while using /{comm_name}. {exc}")

                if before:
                    await interaction.response.send_message(
                        before.format(**kwargs), ephemeral=True
                    )

                try:
                    result = await func(self, interaction, *args, **kwargs)
                except Exception as e:  # pylint: disable=broad-except
                    for exc_data in catch_exceptions or []:
                        if isinstance(exc_data, type):
                            exc_data = ExceptionData(exc_data)

                        if isinstance(e, exc_data.type):
                            await catch_error(e, exc_data)
                            break
                    else:
                        raise e
                else:
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


class MemberUtils(ABC):  # pylint: disable=too-few-public-methods
    """A class containing utility methods for members."""

    @staticmethod
    def convert_to_string(member: Member | User) -> str:
        """Returns the name of a member with an optional discriminator,
        if the member doesn't have a unique name.

        Parameters
        ----------
        member: :class:`nextcord.Member`
            The member to get the name of.

        Returns
        -------
        :class:`str`
            The name of the member with an optional discriminator.
        """

        name = member.name
        if member.discriminator != "0":
            name += f"#{member.discriminator}"
        return name


class PathUtils(ABC):  # pylint: disable=too-few-public-methods
    """A class containing utility methods for paths."""

    @staticmethod
    def convert_classname_to_filename(obj: object) -> str:
        """Converts a class name to a filename.

        If classname ends with 'Model', the last word is removed.

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

        ret = re.sub("(?<!^)(?=[A-Z])", "_", obj.__class__.__name__).lower()
        if ret.endswith("_model"):
            return "_".join(ret.split("_")[:-1])
        return ret


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
    --------

    Run a code at midnight: ::

        async def foo():
            await wait_until_midnight()
            print("It's midnight!")

    Run a code every midnight: ::

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
    await asyncio.sleep(
        time_until_midnight.seconds + time_until_midnight.microseconds / 1000
    )
    return True
