import asyncio
import os

from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.ext import commands, tasks
import nextcord

from utils.wait_time import time_to_midnight
from sggw_bot import SGGWBot

from .calendar_controller import CalendarController


class CalendarCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: CalendarController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = CalendarController(bot)
        self._remove_deprecated_events.start()

    @nextcord.slash_command(
        name='calendar',
        description='Embed with events.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _calendar(self, *_) -> None:
        pass

    @_calendar.subcommand(name='send', description='Send new embed')
    async def _send(self, interaction: Interaction) -> None:
        await self.__ctrl.send(interaction)

    @_calendar.subcommand(name='update', description='Update embed')
    async def _update(self, interaction: Interaction) -> None:
        await self.__ctrl.update(interaction)

    @_calendar.subcommand(name='add', description='Add new event')
    async def _add(
        self,
        interaction: Interaction,
        description: str = SlashOption(
            description='Event description'
        ),
        date: str = SlashOption(
            description='Date (format: `dd.mm.yyyy` e.g. `9.10.2022`)'
        ),
        time: str = SlashOption(
            description='Time (format `hh.mm` e.g. `12.34`). '
            'If not specified, it will be an all day event',
            required=False,
            default=None
        )
    ) -> None:
        await self.__ctrl.add_event(interaction, description, date, time)

    @_calendar.subcommand(name='remove', description='Remove event')
    async def _remove(
        self,
        interaction: Interaction,
        index: int = SlashOption(
            description='Event index. Use `/calendar show` to see indexes.'
        )
    ) -> None:
        await self.__ctrl.remove_event(interaction, index)

    @_calendar.subcommand(name='show', description='Show events with indexes')
    async def _show(self, interaction: Interaction) -> None:
        events = self.__ctrl.get_events_with_indexes()
        await interaction.response.send_message(
            '\n'.join([f'**{k}**: {v}' for k, v in events.items()]),
            ephemeral=True
        )

    @ _calendar.subcommand(name='change_thumbnail', description='Change thumbnail')
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Emoji url (prefered page: \'emoji.gg\')',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @ _calendar.subcommand(name='get_json', description='Get json with embed fields')
    async def _get_fields(self, interaction: Interaction) -> None:
        try:
            file = self.__ctrl.get_fields_from_json('calendar')
        except OSError as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove('calendar_fields_temp.json')
            except:
                pass

    @_calendar.subcommand(name='set_json', description='Set json with embed fields')
    async def _set_fields(
        self,
        interaction: Interaction,
        file: nextcord.Attachment = SlashOption(
            description='JSON file with fields, '
            'downloaded from `/calendar get_json` and updated'
        )
    ) -> None:
        await self.__ctrl.set_fields_from_json(interaction, file, 'calendar')

    @_calendar.subcommand(name='remove_deprecated_events_loop')
    async def _remove_deprecated_events_command(
        self,
        interaction: Interaction,
        choice: str = SlashOption(
            description='What do you want to do with loop?',
            choices=['start', 'stop', 'status', 'restart', 'force']
        )
    ) -> None:
        match choice:
            case 'start':
                if self._remove_deprecated_events.is_running():
                    msg = 'Pętla jest już uruchomiona'
                else:
                    self._remove_deprecated_events.start()
                    msg = 'Uruchomiono'
            case 'stop':
                if not self._remove_deprecated_events.is_running():
                    msg = 'Pętla jest już zastopowana'
                else:
                    self._remove_deprecated_events.cancel()
                    msg = 'Zastopowano'
            case 'status':
                if self._remove_deprecated_events.is_running():
                    msg = 'Działa'
                else:
                    msg = 'Nie działa'
            case 'restart':
                self._remove_deprecated_events.restart()
                msg = 'Zrestartowano'
            case 'force':
                await self.__ctrl.remove_deprecated_events()
                msg = 'Wymuszono użycie loopa bez czekania do północy'
            case _:
                msg = 'Błędna opcja wyboru'

        await interaction.response.send_message(msg, ephemeral=True)

    @tasks.loop(count=1)
    async def _remove_deprecated_events(self) -> None:
        await self.__bot.wait_until_ready()
        while True:
            await asyncio.sleep(time_to_midnight())
            await self.__ctrl.remove_deprecated_events()


def setup(bot: SGGWBot):
    bot.add_cog(CalendarCog(bot))
