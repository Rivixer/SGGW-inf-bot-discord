# SPDX-License-Identifier: MIT
"""A module to control the calendar embed.

The calendar embed is an embed that shows the events.
The events are stored in the data/settings/calendar_settings.json file.
"""

from __future__ import annotations

import datetime
import functools
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Generator

import nextcord
from nextcord.application_command import SlashOption
from nextcord.channel import TextChannel
from nextcord.errors import DiscordException
from nextcord.ext import commands, tasks
from nextcord.interactions import Interaction
from nextcord.member import Member
from nextcord.message import Attachment
from nextcord.ui import Modal, TextInput

from sggwbot.console import Console, FontColour
from sggwbot.errors import ExceptionData, UpdateEmbedError
from sggwbot.models import ControllerWithEmbed, EmbedModel, Model
from sggwbot.utils import InteractionUtils, wait_until_midnight

if TYPE_CHECKING:
    from nextcord.embeds import Embed
    from sggw_bot import SGGWBot


class CalendarCog(commands.Cog):
    """Cog to control the calendar embed."""

    __slots__ = (
        "_bot",
        "_ctrl",
        "_model",
    )

    _bot: SGGWBot
    _ctrl: CalendarController
    _model: CalendarModel

    def __init__(self, bot: SGGWBot) -> None:
        """Initialize the cog."""
        self._bot = bot
        self._model = CalendarModel()
        embed_model = CalendarEmbedModel(self._model, bot)
        self._ctrl = CalendarController(self._model, embed_model)
        self._remove_expired_events_task.start()  # pylint: disable=no-member

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
        catch_exceptions=[DiscordException],
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
        description="Update the calendar embed.",
    )
    @InteractionUtils.with_info(
        before="Updating calendar embed...",
        after="The calendar embed has been updated.",
        catch_exceptions=[UpdateEmbedError],
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
        await wait_until_midnight()
        await self._ctrl.update_embed()

    @_calendar.subcommand(
        name="get_json",
        description="Get the calendar embed json.",
    )
    @InteractionUtils.with_info(
        before="Getting calendar embed json...",
        catch_exceptions=[DiscordException],
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
        catch_exceptions=[TypeError, DiscordException, UpdateEmbedError],
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
        description="Add a new event.",
    )
    @InteractionUtils.with_info(catch_exceptions=[UpdateEmbedError, ValueError])
    @InteractionUtils.with_log()
    async def _add(self, interaction: Interaction) -> None:
        modal = EventModal(EventModalType.ADD, self._ctrl)
        await interaction.response.send_modal(modal)

    @_calendar.subcommand(
        name="edit",
        description="Edit an event.",
    )
    @InteractionUtils.with_info(
        catch_exceptions=[
            UpdateEmbedError,
            ValueError,
            ExceptionData(
                IndexError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
        ],
    )
    @InteractionUtils.with_log()
    async def _edit(
        self,
        interaction: Interaction,
        index: int = SlashOption(
            description="The index of the event to edit started from 1.",
        ),
    ) -> None:
        event = self._model.get_event_at_index(index)
        modal = EventModal(
            EventModalType.EDIT,
            self._ctrl,
            event=event,
        )
        await interaction.response.send_modal(modal)

    @_calendar.subcommand(
        name="show_with_indexes",
        description="Show events with indexes.",
    )
    @InteractionUtils.with_info(catch_exceptions=[DiscordException])
    @InteractionUtils.with_log()
    async def _show(self, interaction: Interaction) -> None:
        """Shows events with their indexes.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """
        events = self._model.events_with_indexes
        await interaction.response.send_message(events, ephemeral=True)

    @_calendar.subcommand(
        name="remove",
        description="Remove an event with the given index.",
    )
    @InteractionUtils.with_info(
        before="Removing event with index **{index}**...",
        catch_exceptions=[
            DiscordException,
            UpdateEmbedError,
            ExceptionData(
                IndexError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
        ],
    )
    @InteractionUtils.with_log()
    async def _remove(
        self,
        interaction: Interaction,
        index: int = SlashOption(
            description="The index of the event to remove started from 1.",
        ),
    ) -> None:
        """Removes an event from the calendar with the given index.

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

        event = self._model.get_event_at_index(index)
        self._model.remove_event_from_json(event)
        await self._ctrl.update_embed()

        # We edit the original message here
        # instead of in the `with_info` decorator,
        # because we don't have access to the event description there.
        msg = await interaction.original_message()
        await msg.edit(f"The event **{event.full_info}** has been removed.")

    @_calendar.subcommand(
        name="remove_expired_events",
        description="Remove expired events.",
    )
    @InteractionUtils.with_info(
        before="Removing expired events...",
        after="Expired events have been removed.",
        catch_exceptions=[DiscordException, UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _remove_expired_events(
        self,
        interaction: Interaction,  # pylint: disable=unused-argument
    ) -> None:
        """Removes expired events from the calendar.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """

        removed_events = self._model.remove_expired_events()
        if removed_events:
            await self._ctrl.update_embed()

    @tasks.loop(count=1)
    async def _remove_expired_events_task(self) -> None:
        """Removes expired events from the calendar.

        Expired events are events that have already taken place.

        The events are removed at midnight.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._bot.wait_until_ready()
        while True:
            removed_events = self._model.remove_expired_events()
            if removed_events:
                await self._ctrl.update_embed()
            await wait_until_midnight()


@dataclass(slots=True)
class Event:
    """Represents an event in the calendar.

    If event is an all-day event, :attr:`time` will be '00:00'.

    Attributes
    ----------
    description: :class:`str`
        The event description.
    date: :class:`datetime.date`
        The date when the event is to take place.
    time: :class:`datetime.date`
        The time when the event is to take place.
        If is None, the event is an all-day one.
    prefix: :class:`str`
        The prefix of the event.
    location: :class:`str`
        The location of the event.
    """

    description: str
    date: datetime.date
    time: datetime.time | None
    prefix: str
    location: str

    @property
    def datetime(self) -> datetime.datetime:
        """The datetime representation of the event.

        If the event is an all-day one, the time is set to 00:00:00.
        """
        time = self.time if self.time is not None else datetime.time()
        return datetime.datetime.combine(self.date, time)

    @property
    def is_all_day(self) -> bool:
        """Whether the event is an all-day one.

        Notes
        -----
        An event is an all-day one if its time is None.
        """
        return self.time is None

    @property
    def is_expired(self) -> bool:
        """Whether the event has already started.

        Notes
        -----
        If the event is an all-day one,
        the start time is taken as 11:59 PM.
        """

        now = datetime.datetime.now()
        if self.time is None:
            return self.date < now.date()
        return self.datetime < now

    @property
    def full_name(self) -> str:
        """The full name of the event in format:

        `[prefix if exists] **description**
        [location if exists] (time if not an all-day event)`
        """

        result = f"**{self.description}**"

        if self.prefix:
            result = f"[{self.prefix}] {result}"

        if self.location:
            result = f"{result} [{self.location}]"

        if self.time is not None:
            if sys.platform == "win32":
                result += f' ({self.time.strftime("%#H:%M")})'  # pragma: no cover
            else:
                result += f' ({self.time.strftime("%-H:%M")})'  # pragma: no cover

        return result

    @property
    def full_info(self) -> str:
        """The full information of the event in format:

        `(date) [prefix if exists] **description**
        [location if exists] (time if not an all-day event)

        Similar to :attr:`.Event.full_name` but with the date at the beginning.
        """
        return f"({self.date.strftime('%d.%m.%Y')}) {self.full_name}"

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

    @staticmethod
    def compare_method(event1: Event, event2: Event) -> int:
        """Compares events with their date and time."""
        return int((event1.datetime - event2.datetime).total_seconds())


class CalendarModel(Model):
    """Represents the calendar model."""

    @dataclass
    class _RawEventData:
        description: str
        date: str
        time: str | None
        prefix: str
        location: str

        def to_event(self) -> Event:
            """Converts data to the :class:`.Event` class."""
            dt = CalendarModel.convert_datetime_input(self.date, self.time)
            return Event(
                self.description,
                dt.date(),
                dt.time() if self.time else None,
                self.prefix,
                self.location,
            )

    @staticmethod
    def _convert_event_to_raw_data(event: Event) -> _RawEventData:
        return CalendarModel._RawEventData(
            event.description,
            event.date.strftime("%d.%m.%Y"),
            event.time.strftime("%H.%M") if event.time else None,
            event.prefix,
            event.location,
        )

    @staticmethod
    def convert_datetime_input(
        date_input: str, time_input: str | None
    ) -> datetime.datetime:
        """Converts date and time inputs to the datetime format."""
        date_input = re.sub("[-:/]", ".", date_input)
        time_input = re.sub("[-:/]", ".", time_input) if time_input else "00.00"
        _input = f"{date_input} {time_input}"
        return datetime.datetime.strptime(_input, "%d.%m.%Y %H.%M")

    @property
    def calendar_data(self) -> list[Event]:
        """A list of events formatted to the :class:`.Event` class.
        Sorted by date."""
        result: list[Event] = []
        for raw_event in self._events_data:
            result.append(raw_event.to_event())
        result.sort(key=functools.cmp_to_key(Event.compare_method))
        return result

    @property
    def _events_data(self) -> list[_RawEventData]:
        events: list[dict[str, str]] = self.data.get("events", [])
        return (
            list(map(lambda i: CalendarModel._RawEventData(*i.values()), events))
            if events
            else []
        )

    def get_event_at_index(self, index: int) -> Event:
        """Returns the event at the specified index.

        Parameters
        ----------
        index: :class:`int`
            The index of the event to get.

        Returns
        -------
        :class:`.Event`
            The found event.

        Raises
        ------
        IndexError
            - If the index is out of bounds (less than 1 or greater than the number of events).
            - If there are no events.
        """

        events = self.calendar_data
        number_of_events = len(events)

        if number_of_events == 0:
            raise IndexError("There are no events")

        if not (1 <= index <= number_of_events):
            raise IndexError(f"Index must be between 1 and {number_of_events}")

        return events[index - 1]

    def remove_event_from_json(self, event: Event) -> None:
        """Removes event from the `settings.json` file.

        Parameters
        ----------
        event: :class:`.Event`
            The event to remove.
        """
        data: list[dict[str, str]] = self.data.get("events", [])
        data.remove(asdict(self._convert_event_to_raw_data(event)))
        self.update_settings("events", data)

    def remove_expired_events(self) -> list[Event]:
        """Removes all events that have already started.

        Returns
        -------
        list[:class:`.Event`]
            A list of removed events.
        """

        removed_events = []
        for event in self.calendar_data:
            if event.is_expired:
                self.remove_event_from_json(event)
                removed_events.append(event)

                Console.specific(
                    f"Event '{event.full_info}' has been removed due to expiration.",
                    "Calendar",
                    FontColour.GREEN,
                    bold_type=True,
                )

        return removed_events

    @property
    def events_with_indexes(self) -> str:
        """A string with all events and their indexes.
        Indexes start from 1.
        """
        result = []
        events = self.calendar_data
        for i, event in enumerate(events):
            result.append(f"{i+1}. {event.full_info}")
        return "\n".join(result)

    def add_event_to_json(self, event: Event) -> None:
        """Adds the event to the `settings.json` file.

        Parameters
        ----------
        event: :class:`.Event`
            An event to be added.
        """
        data: list[dict[str, str]] = self.data.get("events", [])
        data.append(asdict(self._convert_event_to_raw_data(event)))
        self.update_settings("events", data, force=True)

    def get_grouped_events(
        self,
    ) -> Generator[tuple[datetime.date, list[Event]], None, None]:
        """An iterator that reads all events from settings and sorts them.

        Yields
        ------
        tuple[:class:`datetime.date`, list[:class:`.Event`]]
            A tuple of events, grouped by date and sorted.
        """
        calendar: dict[datetime.date, list[Event]] = {}

        for event in self.calendar_data:
            try:
                calendar[event.date].append(event)
            except KeyError:
                calendar[event.date] = [event]

        for date, event in calendar.items():
            yield (date, event)


# pylint: disable=no-member


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
    def _convert_input_to_event(
        description: str,
        date: str,
        time: str | None,
        prefix: str,
        location: str,
    ) -> Event:
        dt = CalendarModel.convert_datetime_input(date, time)
        return Event(
            description, dt.date(), dt.time() if time else None, prefix, location
        )

    def add_event(  # pylint: disable=too-many-arguments
        self,
        description: str,
        date: str,
        time: str | None,
        prefix: str,
        location: str,
    ) -> Event:
        """Adds event to the `settings.json` file.

        The date and time separator can be `.`, `:`, `-` or `/`.

        Parameters
        ----------
        description: :class:`str`
            The event description.
        date: :class:`str`
            The date in the format `dd.mm.yyyy`.
        time: :class:`str` | `None`
            The time in the format `hh.mm`.
            If `None`, the time will be set to `00.00`.
        prefix: :class:`str`
            The prefix of the event.
        location: :class:`str`
            The location of the event.

        Returns
        -------
        :class:`.Event`
            An event that has been added.

        Raises
        ------
        ValueError
            The date or time was invalid.
        """
        event = self._convert_input_to_event(description, date, time, prefix, location)
        self.model.add_event_to_json(event)
        return event


class EventModalType(Enum):
    """Represents type of event modal."""

    ADD = auto()
    EDIT = auto()


class EventModal(Modal):  # pylint: disable=too-many-instance-attributes
    """A modal to add or edit an event.

    Parameters
    ----------
    title: :class:`str`
        The title of the modal.
    controller: :class:`.CalendarController`
        The calendar controller.
    event: :class:`.Event` | `None`
        The event to edit. If `None`, a new event will be added.

    Attributes
    ----------
    description: :class:`TextInput`
        The description of the event.
    date: :class:`TextInput`
        The date of the event.
    time: :class:`TextInput`
        The time of the event.
    prefix: :class:`TextInput`
        The prefix of the event.
    location: :class:`TextInput`
        The location of the event.
    """

    __slots__ = (
        "description",
        "date",
        "time",
        "prefix",
        "location",
        "modal_type",
        "_controller",
        "_event",
    )

    description: TextInput
    date: TextInput
    time: TextInput
    prefix: TextInput
    location: TextInput
    modal_type: EventModalType
    _controller: CalendarController
    _event: Event | None

    def __init__(
        self,
        modal_type: EventModalType,
        /,
        controller: CalendarController,
        event: Event | None = None,
    ):
        match modal_type:
            case EventModalType.ADD:
                title = "Add a new event"
            case EventModalType.EDIT:
                title = "Edit the event"
            case _:
                raise NotImplementedError

        super().__init__(title=title, timeout=None)

        self.modal_type = modal_type
        self._controller = controller
        self._event = event

        self.description = TextInput(
            label="Description:",
            placeholder="The description of the event",
            default_value=event.description if event else "",
            max_length=100,
            required=True,
        )
        self.add_item(self.description)

        self.date = TextInput(
            label="Date:",
            placeholder="The date in the format `dd.mm.yyyy`",
            default_value=event.date.strftime("%d.%m.%Y") if event else "",
            max_length=10,
            required=True,
        )
        self.add_item(self.date)

        self.time = TextInput(
            label="Time:",
            placeholder="The time (`hh.mm`), not specified = all day event",
            max_length=5,
            required=False,
        )

        if event is None or event.time is None:
            self.time.default_value = None
        else:
            self.time.default_value = event.time.strftime("%H.%M")

        self.add_item(self.time)

        self.prefix = TextInput(
            label="Prefix:",
            placeholder="The prefix of the event",
            default_value=event.prefix if event else "",
            max_length=10,
            required=False,
        )
        self.add_item(self.prefix)

        self.location = TextInput(
            label="Location:",
            placeholder="The location of the event",
            default_value=event.location if event else "",
            max_length=20,
            required=False,
        )
        self.add_item(self.location)

    @InteractionUtils.with_info(catch_exceptions=[ValueError, UpdateEmbedError])
    async def callback(self, interaction: Interaction) -> None:
        """The callback for the modal.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the modal.
        """
        member = interaction.user
        assert isinstance(member, Member)

        await interaction.response.defer()

        description = self.description.value or ""
        date = self.date.value or ""
        time = self.time.value or None
        prefix = self.prefix.value or ""
        location = self.location.value or ""

        old_event: Event | None = self._event
        if self._event is not None:
            self._controller.model.remove_event_from_json(self._event)

        self._event = self._controller.add_event(
            description, date, time, prefix, location
        )

        msg = f"{member} "
        match self.modal_type:
            case EventModalType.ADD:
                msg += "added a new event "
            case EventModalType.EDIT:
                assert old_event is not None
                msg += f"edited the event '{old_event.full_info}' -> "
            case _:
                raise NotImplementedError
        msg += f"'{self._event.full_info}'"
        Console.specific(msg, "Calendar", FontColour.GREEN, bold_type=True)

        await self._controller.update_embed()


def setup(bot: SGGWBot):
    """Loads the CalendarCog cog."""
    bot.add_cog(CalendarCog(bot))
