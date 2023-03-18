# SPDX-License-Identifier: MIT
"""A module to control the calendar embed.

The calendar embed is an embed that shows the events.
The events are stored in the data/settings/calendar_settings.json file.
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generator

import nextcord
from nextcord.application_command import SlashOption
from nextcord.channel import TextChannel
from nextcord.ext import commands, tasks
from nextcord.interactions import Interaction
from nextcord.message import Attachment

from .errors import UpdateEmbedError
from .models import ControllerWithEmbed, EmbedModel, Model
from .utils import InteractionUtils, wait_until_midnight

if TYPE_CHECKING:
    from nextcord.embeds import Embed
    from sggw_bot import SGGWBot


class CalendarCog(commands.Cog):
    """Cog to control the calendar embed."""

    __slots__ = (
        "_bot",
        "_ctrl",
    )

    _bot: SGGWBot
    _ctrl: CalendarController

    def __init__(self, bot: SGGWBot) -> None:
        """Initialize the cog."""
        self._bot = bot
        model = CalendarModel()
        embed_model = CalendarEmbedModel(model, bot)
        self._ctrl = CalendarController(model, embed_model)

    @nextcord.slash_command(
        name="calendar",
        description="The calendar embed.",
        dm_permission=False,
    )
    async def _calendar(self, *_) -> None:
        """The calendar embed.

        This command is a placeholder for the subcommands.
        """

    @_calendar.subcommand(
        name="send",
        description="Send a new calendar embed.",
    )
    @InteractionUtils.with_info(
        before="Sending calendar embed...",
        after="The calendar embed has been sent.",
        catch_errors=True,
    )
    @InteractionUtils.with_log(show_channel=True)
    async def _send(self, interaction: Interaction) -> None:
        """Sends a new calendar embed.

        The calendar embed is sent to the channel where the command was used.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """

        channel = interaction.channel
        if isinstance(channel, TextChannel):
            await self._ctrl.send_embed(channel)

    @_calendar.subcommand(
        name="update",
        description="Update the dalendar embed.",
    )
    @InteractionUtils.with_info(
        before="Updating calendar embed...",
        after="The calendar embed has been updated.",
        catch_errors=True,
        additional_errors=[UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _update(
        self, interaction: Interaction  # pylint: disable=unused-argument
    ) -> None:
        """Updates the calendar embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._ctrl.update_embed()

    @_calendar.subcommand(
        name="get_json",
        description="Get the dalendar embed json.",
    )
    @InteractionUtils.with_info(
        before="Getting calendar embed json...",
        catch_errors=True,
    )
    @InteractionUtils.with_log()
    async def _get_json(self, interaction: Interaction) -> None:
        """Gets the json file representing the calendar embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """
        msg = await interaction.original_message()
        await msg.edit(file=self._ctrl.embed_json)

    @_calendar.subcommand(
        name="set_json",
        description="Set the calendar embed json and update the embed.",
    )
    @InteractionUtils.with_info(
        before="Setting calendar embed json and updating the embed...",
        after="The calendar embed and json file have been updated.",
        catch_errors=True,
        additional_errors=[UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _set_json(
        self,
        _: Interaction,
        file: Attachment = SlashOption(
            description="JSON file " "downloaded from `/calendar get_json` and updated"
        ),
    ) -> None:
        """Sets the json file representing the calendar embed and updates this embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        file: :class:`Attachment`
            The json file downloaded from `/calendar get_json` and updated.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._ctrl.set_embed_json(file)
        await self._ctrl.update_embed()

    @_calendar.subcommand(
        name="add",
        description="Add a new event",
    )
    @InteractionUtils.with_info(
        before="Adding a new event... **{description}**",
        after="The new event **{description}** has been added.",
        catch_errors=True,
        additional_errors=[UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _add(
        self,
        _: Interaction,
        description: str = SlashOption(description="The event description"),
        date: str = SlashOption(
            description="The date (format: `dd.mm.yyyy` e.g. `9.10.2022`)"
        ),
        time: str = SlashOption(
            description="The time (format `hh.mm` e.g. `12.34`). "
            "If not specified, it will be an all day event",
            required=False,
            default=None,
        ),
    ) -> None:
        self._ctrl.add_event(description, date, time)
        await self._ctrl.update_embed()

    @_calendar.subcommand(
        name="show_with_indexes",
        description="Show events with indexes.",
    )
    @InteractionUtils.with_info(catch_errors=True)
    @InteractionUtils.with_log()
    async def _show(self, interaction: Interaction) -> None:
        """Shows events with their indexes.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """
        events = self._ctrl.events_with_indexes
        await interaction.response.send_message(events, ephemeral=True)

    @_calendar.subcommand(
        name="remove",
        description="Show events with indexes.",
    )
    @InteractionUtils.with_info(
        before="Removing event with index **{index}**...",
        catch_errors=True,
        additional_errors=[UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _remove(self, interaction: Interaction, index: int) -> None:
        """Removes an event from the calendar.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        index: :class:`int`
            The index of the event to remove.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """

        event = self._ctrl.remove_event(index)
        await self._ctrl.update_embed()
        msg = await interaction.original_message()
        await msg.edit(f"The event **{event}** has been removed.")

    @tasks.loop(count=1)
    async def _remove_deprecated_events(self) -> None:
        """Removes deprecated events from the calendar.

        Deprecated events are events that have already taken place.

        The events are removed at midnight.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._bot.wait_until_ready()
        while await wait_until_midnight():
            removed_events = self._ctrl.remove_deprecated_events()
            if removed_events:
                await self._ctrl.update_embed()


# pylint: disable=no-member


@dataclass(slots=True, order=True)
class Event:
    """Represents an event in the calendar.

    If event is an all-day event, time in :attr:`date` will be '00:00'.

    Attributes
    ----------
    descrption: :class:`str`
        The event description.
    date: :class:`datetime.datetime`
        The date and time when the event is to take place.
        Used for compare.
    is_all_day: :class:`bool`
        Whether the event is an all-day event.
    """

    description: str = field(compare=False)
    date: dt.datetime
    is_all_day: bool = field(compare=False)

    def __post_init__(self) -> None:
        # Checks that the time is 00:00 if the event is an all-day event.
        time = self.date.strftime("%H:%M:%S")
        if self.is_all_day and time != "00:00:00":
            raise ValueError("Time must be 00:00.00:if is_all_day is True")

    def is_deprecated(self) -> bool:
        """Returns ``True`` if the event has already started.

        If the event is an all-day event,
        the start time is taken as 11:59 PM.
        """

        now = dt.datetime.now()
        if self.is_all_day:
            return self.date.date() < now.date()
        return self.date < now

    @property
    def full_name(self) -> str:
        """The full name of the event.
        It includes the time if the event is not an all-day event.
        """

        result = f"**{self.description}**"
        if not self.is_all_day:
            if sys.platform == "win32":
                result += f' ({self.date.strftime("%#H:%M")})'  # pragma: no cover
            else:
                result += f' ({self.date.strftime("%-H:%M")})'  # pragma: no cover

        return result

    @property
    def weekday(self) -> str:
        """The weekday of the event."""

        weekdays = {
            0: "poniedziałek",
            1: "wtorek",
            2: "środa",
            3: "czwartek",
            4: "piątek",
            5: "sobota",
            6: "niedziela",
        }
        return weekdays.get(self.date.weekday(), "")


class CalendarModel(Model):
    """Represents the calendar model."""

    @property
    def calendar_data(self) -> list[Event]:
        """A list of events formatted to the :class:`.Event` class.
        Sorted by date."""

        result = []

        for event in self._events_data:
            description, date_str, is_all_day = event
            date = dt.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

            _event = Event(description, date, is_all_day)
            result.append(_event)

        result.sort()
        return result

    @property
    def _events_data(self) -> list[tuple[str, str, bool]]:
        return list(map(tuple, self.data.get("events", [])))

    def add_event_to_json(
        self, description: str, datetime: dt.datetime, is_all_day: bool
    ) -> Event:
        """Adds the event to the `settings.json` file.

        Parameters
        ----------
        description: :class:`str`
            The event description.
        datetime: :class:`datetime.datetime`
            The date and time when the event is to take place.
        is_all_day: :class:`bool`
            Whether the event is an all-day event.

        Returns
        -------
        :class:`.Event`
            The event that was added.
        """
        datetime = datetime.replace(microsecond=0)
        if is_all_day:
            datetime = datetime.replace(hour=0, minute=0, second=0)
        data = self._events_data
        data.append((description, str(datetime), is_all_day))
        self.update_settings("events", data, force=True)
        return Event(description, datetime, is_all_day)

    def remove_event_from_json(self, event: Event) -> None:
        """Removes the event from the `settings.json` file."""
        data = self._events_data
        data.remove((event.description, str(event.date), event.is_all_day))
        self.update_settings("events", data)

    def get_grouped_events(self) -> Generator[tuple[dt.date, list[Event]], None, None]:
        """An iterator that reads all events from settings and sorts them.

        Yields
        ------
        tuple[:class:`datetime.date`, list[:class:`.Event`]]
            A tuple of events, grouped by date and sorted.
        """
        calendar: dict[dt.date, list[Event]] = {}

        for event in self.calendar_data:
            try:
                calendar[event.date.date()].append(event)
            except KeyError:
                calendar[event.date.date()] = [event]

        for date, event in calendar.items():
            yield (date, event)


class CalendarEmbedModel(EmbedModel):
    """Represents the calendar embed model.

    Attributes
    ----------
    model: :class:`.CalendarModel`
        The calendar model.
    """

    model: CalendarModel

    def generate_embed(self, **_) -> Embed:
        """Generates an embed with all events."""
        embed = super().generate_embed()

        for day, events in self.model.get_grouped_events():
            weekday = events[0].weekday
            date = day.strftime("%d.%m.%Y")
            embed.add_field(
                name=f"{date} ({weekday}):",
                value="∟" + "\n∟".join(map(lambda i: i.full_name, events)),
                inline=False,
            )

        return embed


class CalendarController(ControllerWithEmbed):
    """Represents the calendar controller.

    Attributes
    ----------
    embed_model: :class:`.CalendarEmbedModel`
        The calendar embed model.
    model: :class:`.CalendarModel`
        The calendar model.
    """

    embed_model: CalendarEmbedModel
    model: CalendarModel

    @staticmethod
    def _convert_input_to_datetime(date: str, time: str | None) -> dt.datetime:
        """Converts the input to a :class:`datetime.datetime` object."""
        if time is None:
            time = "00.00"

        date = date.replace(":", ".").replace("-", ".").replace("/", ".")
        time = time.replace(":", ".").replace("-", ".").replace("/", ".")
        return dt.datetime.strptime(f"{date} {time}", "%d.%m.%Y %H.%M")

    def add_event(
        self,
        text: str,
        date: str,
        time: str | None,
    ) -> None:
        """Adds event to the `settings.json` file.

        The date and time separator can be `.`, `:`, `-` or `/`.

        Parameters
        ----------
        text: :class:`str`
            The event description.
        date: :class:`str`
            The date in the format `dd.mm.yyyy`.
        time: :class:`str` | `None`
            The time in the format `hh.mm`.
            If `None`, the time will be set to `00.00`.

        Raises
        ------
        ValueError
            The date or time was invalid.
        """
        datetime = self._convert_input_to_datetime(date, time)
        is_all_day = time is None
        self.model.add_event_to_json(text, datetime, is_all_day)

    def remove_event(self, index: int) -> Event:
        """Removes event from the `settings.json` file.

        Parameters
        ----------
        index: :class:`int`
            The index of the event to remove.

        Returns
        -------
        :class:`.Event`
            The removed event.

        Raises
        ------
        IndexError
            The index was invalid.

        Notes
        -----
        The index starts from 1.
        """

        number_of_events = len(self.model.data.get("events", []))
        if number_of_events == 0:
            raise IndexError("There are no events to remove")

        try:
            if index <= 0:
                raise IndexError
            event = self.model.calendar_data[index - 1]
        except IndexError as e:
            raise IndexError(f"Index must be between 1 and {number_of_events}") from e

        self.model.remove_event_from_json(event)
        return event

    def remove_deprecated_events(self) -> list[Event]:
        """Removes all events that have already started.

        Returns
        -------
        list[:class:`.Event`]
            A list of removed events.
        """

        removed_events = []
        for event in self.model.calendar_data:
            if event.is_deprecated():
                self.model.remove_event_from_json(event)
                removed_events.append(event)
        return removed_events

    @property
    def events_with_indexes(self) -> str:
        """A string with all events and their indexes.
        Indexes start from 1.
        """
        result = []
        events = self.model.calendar_data
        for i, event in enumerate(events):
            result.append(f"{i+1}. {event.full_name}")
        return "\n".join(result)


def setup(bot: SGGWBot):
    """Loads the CalendarCog cog."""
    bot.add_cog(CalendarCog(bot))
