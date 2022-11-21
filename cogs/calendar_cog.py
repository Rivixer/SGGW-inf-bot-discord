from datetime import datetime, timedelta
from typing import Generator
import collections
import asyncio
import json
import uuid

from nextcord.ext import commands, tasks
from nextcord.colour import Colour
from nextcord.embeds import Embed
import nextcord

from utils.checks import has_admin_role, is_bot_channel
from utils.message import MainMessageUtils
from utils.settings import settings, update_settings
from utils.console import Console, FontColour
from utils.update_embed import UpdateEmbed
from sggw_bot import BOT_PREFIX

_event = collections.namedtuple('Event', ['date', 'time', 'text'])
_event_time = collections.namedtuple('EventTime', ['time', 'text'])

_MSG_JSON_NAME = 'CALENDAR_MSG'


class CalendarCog(commands.Cog):

    __slots__ = (
        '__bot',
    )

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot
        self.__load_calendar_from_json()
        self.__remove_deprecated_events.start()

    @tasks.loop(count=1)
    async def __remove_deprecated_events(self) -> None:
        await self.__bot.wait_until_ready()

        while True:
            msg_settings: dict = settings.get(_MSG_JSON_NAME)
            channel_id = msg_settings.get('CHANNEL_ID')
            msg_id = msg_settings.get('MSG_ID')

            try:
                channel = await self.__bot.fetch_channel(channel_id)
            except Exception as e:
                return Console.important_error(
                    'Info channel not found. Loop stopped.', e
                )

            try:
                message = await channel.fetch_message(msg_id)
            except Exception as e:
                return Console.important_error(
                    'Message not found. Loop stopped.', e
                )

            today = datetime.now()

            async def remove_from_calendar(preview: bool) -> None:
                calendar = self.__load_calendar_from_json(preview=preview)
                calendar_copy = calendar.copy()

                for uuid, event in calendar.copy().items():
                    if today.date() > event.date:
                        event = calendar_copy.pop(uuid)
                        Console.specific(
                            f'Usunięto {event.date} {event.time} {event.text} '
                            f'z powodu przedawnienia. (calendar{"_preview" if preview else ""})',
                            'Kalendarz', FontColour.GREEN
                        )

                if calendar != calendar_copy:
                    self.__save_calendar_to_json(
                        calendar_copy, preview=preview
                    )

                    if preview is False:
                        embed = self.generate_embed(preview=False)
                        await message.edit(embed=embed)

            await asyncio.gather(
                remove_from_calendar(preview=True),
                remove_from_calendar(preview=False)
            )

            tomorrow = today + timedelta(days=1)
            midnight = datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            time_to_midnight = midnight - today
            await asyncio.sleep(time_to_midnight.seconds)

    def __load_calendar_from_json(self, *, preview: bool = False) -> dict[str, _event]:
        with open(f'files{"/preview" if preview else ""}/calendar.json', encoding='utf-8') as f:
            data: dict[str, dict[str, str]] = json.load(f)

        calendar = dict()

        for event_id, event_data in data.items():
            datetime_str = event_data[0] + ' ' + event_data[1]
            text = event_data[2]

            _datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            date = _datetime.date()
            time = _datetime.time()

            event = _event(date, time, text)
            calendar[event_id] = event

        return calendar

    async def __add_event_to_preview_json(self, ctx: commands.Context, datetime: datetime, text: str) -> None:
        calendar = self.__load_calendar_from_json(preview=True)

        calendar[str(uuid.uuid4())] = _event(
            datetime.date(),
            datetime.time(),
            text
        )

        try:
            with open('files/preview/calendar.json', 'w', encoding='utf-8') as f:
                json.dump(
                    calendar, f, ensure_ascii=True,
                    indent=4, default=str
                )
        except Exception as e:
            await ctx.send(
                f'{ctx.author.mention} Coś poszło nie tak z zapisywaniem do pliku!\n{e}'
            )
        else:
            await ctx.send(
                f'{ctx.author.mention} Dodano nowe wydarzenie.'
            )

    def __save_calendar_to_json(self, calendar: dict[str, _event], *, preview: bool) -> str | None:
        """Return exception content if something went wrong."""

        try:
            with open(
                f'files{"/preview" if preview else ""}/calendar.json',
                'w', encoding='utf-8'
            ) as f:
                json.dump(
                    calendar, f, ensure_ascii=True,
                    indent=4, default=str
                )
        except Exception as e:
            Console.important_error(f'Nie udało się zapisać kalendarza', e)
            return f'Coś poszło nie tak z zapisywaniem do pliku!\n{e}'

    async def __remove_event_from_json(self, ctx: commands.Context, uuid: str) -> None:
        calendar = self.__load_calendar_from_json(preview=True)
        event = calendar.pop(uuid)

        if reason := self.__save_calendar_to_json(calendar, preview=True):
            await ctx.send(f'{ctx.author.mention} {reason}')
        else:
            await ctx.send(
                f'{ctx.author.mention} Usunięto wydarzenie '
                f'{event.date} {event.time}, {event.text}'
            )

    @staticmethod
    def weekday(date: datetime) -> str:
        return {
            6: "niedziela",
            0: "poniedziałek",
            1: "wtorek",
            2: "środa",
            3: "czwartek",
            4: "piątek",
            5: "sobota",
        }.get(date.weekday())

    def generate_embed(self, *, preview: bool = False) -> Embed:
        embed = Embed(
            title='Kalendarz',
            description=f'Aktualizacja: {datetime.now().strftime("%d.%m.%Y %H:%M")}',
            colour=Colour.green()
        )

        calendar = self.__load_calendar_from_json(preview=preview)
        dated_events: dict[datetime, list[_event_time]] = dict()

        for event in calendar.values():
            event_time = _event_time(event.time, event.text)
            try:
                dated_events[event.date].append(event_time)
            except KeyError:
                dated_events[event.date] = [event_time]

        sorted_events = {k: v for k, v in sorted(dated_events.items())}

        def convert_event_time_to_str(event_time: _event_time) -> str:
            time_str = event_time.time.strftime('%H:%M')
            if time_str == '00:00':
                return event_time.text
            return f'{event_time.text} ({time_str})'

        for event_date, events in sorted_events.items():
            events_sorted = sorted(events, key=lambda i: i.time)
            embed.add_field(
                name=f"{event_date.strftime('%d.%m.%Y')} ({self.weekday(event_date)}):",
                value='\n'.join(
                    convert_event_time_to_str(i)
                    for i in events_sorted
                ),
                inline=False
            )

        if len(embed.fields) == 0:
            embed.set_footer(
                text='HURRA! Nie ma nic 🥳'
            )

        return embed

    @ has_admin_role()
    @ commands.group(name='calendar', brief='Embed with important events')
    async def _calendar(self, *_) -> None:
        pass

    @ _calendar.command(
        name='send',
        brief='Send new main message',
        description='''The command message will be deleted.
        The sent message will be the main message now.
        The channel where the message was sent
        will be now the main channel of this message.
        If old main message exists, delete it.'''
    )
    async def _send(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        try:
            _, old_message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except:
            ...
        else:
            await old_message.delete()

        embed = self.generate_embed(preview=False)
        message = await ctx.send(embed=embed)
        update_settings(
            _MSG_JSON_NAME, {
                "MSG_ID": message.id,
                "CHANNEL_ID": ctx.channel.id
            }
        )

    @ is_bot_channel()
    @ _calendar.command(
        name='reset_loop',
        brief='Reset `remove deprecated events` loop',
        description='Only on bot-channel.'
    )
    async def _reset_loop(self, ctx: commands.Context, *_) -> None:
        self.__remove_deprecated_events.stop()
        self.__remove_deprecated_events.start()
        await ctx.send(
            f'{ctx.author.mention} Jeśli w konsoli nie ma błędu, '
            'to znaczy że chyba działa.'
        )

    @ _calendar.command(
        name='update',
        brief='Update current main message',
        description='''You can use this on any channel,
        but only on the main channel the message will be deleted.
        If main message not exists, send info about it.
        '''
    )
    async def _update(self, ctx: commands.Context, *_) -> None:
        msg_settings: dict = settings.get(_MSG_JSON_NAME)
        channel_id = msg_settings.get('CHANNEL_ID')

        if channel_id == ctx.channel.id:
            await ctx.message.delete()

        try:
            channel, message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except (nextcord.NotFound, nextcord.HTTPException, commands.errors.CommandInvokeError):
            return await ctx.send(
                f'{ctx.author.mention} Nie znaleziono wiadmomości do zaktualizowania. '
                f'Zaktualizuj settings.json lub użyj komendy \'{BOT_PREFIX}calendar send\'.',
                delete_after=(10 if channel_id == ctx.channel.id else None)
            )

        UpdateEmbed.override_file('calendar')

        embed = self.generate_embed()
        await message.edit(embed=embed)

        if channel.id != ctx.channel.id:
            await ctx.send(
                f'{ctx.author.mention} Zaktualizowano kalendarz na {channel.mention}'
            )

    @ is_bot_channel()
    @ _calendar.command(
        name='new',
        brief=f'Type \'{BOT_PREFIX}help calendar new\' for more info',
        description=f"""Create new event. Only on bot-channel.
        Use: '{BOT_PREFIX}calendar new [date] [time] [text...]'
        Where:
            [date] - 'dd.mm.yyyy' (e.g. 03.04.2012)
            [time] - 'HH.MM' (e.g. 7.30) or '-' if not specified
        You can use ':' or '-' separator instead of '.'
        Examples:
            {BOT_PREFIX}calendar new 01-10-2023 9:00 Rozpoczęcie studiów
            {BOT_PREFIX}calendar new 6.01:2040 - Trzech Króli
        """
    )
    async def _new(
        self,
        ctx: commands.Context,
        date: str | None = None,
        time: str | None = None,
        *text: str
    ) -> None:
        command_input = f"{BOT_PREFIX}calendar new {date} {time} {' '.join(text)}"

        if date is None or time is None or len(text) == 0:
            return await ctx.send(
                f"{ctx.author.mention} Brak wszystkich argumentów.\n"
                f"Wpisz **{BOT_PREFIX}help calendar new** po więcej informacji.\n"
                f"Your command: *{command_input}*"
            )

        _date = date.replace('-', '.').replace(':', '.')

        if time == '-':
            _time = '00.00'
        else:
            _time = time.replace('-', '.').replace(':', '.')

        try:
            _datetime = datetime.strptime(
                f'{_date} {_time}',
                '%d.%m.%Y %H.%M'
            )
        except ValueError as e:
            return await ctx.send(
                f"{ctx.author.mention} Niepoprawna data lub godzina!\n{e}\n"
            )

        await self.__add_event_to_preview_json(ctx, _datetime, ' '.join(text))

    @ is_bot_channel()
    @ _calendar.command(
        name='remove',
        aliases=['delete', 'del'],
        brief=f'Remove event from calendar',
        description=f"""Only on bot-channel.
        Type \'{BOT_PREFIX}calendar remove\' to see the indexses of all events.
        """
    )
    async def _remove(self, ctx: commands.Context, index: str | None = None, *_) -> None:

        calendar = self.__load_calendar_from_json(preview=True)

        def index_events() -> Generator[str, None, None]:
            for i, event in enumerate(calendar.values()):
                date = event.date.strftime('%d.%m.%y')
                time = event.time.strftime('%H:%M')
                if time == '00:00':
                    time = '(cały dzień)'
                yield f'**{i+1}:** {date} {time} {event.text}'

        if index is None:
            embed = Embed(
                title='Indeksy wydarzeń:',
                description='\n'.join(index_events()) or 'Brak wydarzeń'
            ).add_field(
                name='Aby usunąć wydarzenie, użyj:',
                value=f'{BOT_PREFIX}calendar remove *\*index\**'
            ).set_footer(
                text="Uważaj! Usunięcie jakiegoś wydarzenia "
                "zmieni pozostałym wydarzeniom indeksy!"
            )
            return await ctx.send(
                f'{ctx.author.mention}',
                embed=embed
            )

        try:
            _index = int(index)
        except ValueError:
            return await ctx.send(
                f'{ctx.author.mention} Nieprawidłowa wartość index.'
            )

        if not (0 < _index <= len(calendar)):
            return await ctx.send(
                f'{ctx.author.mention} Nieprawidłowa wartość index.'
            )

        uuid = list(calendar.keys())[_index-1]
        await self.__remove_event_from_json(ctx, uuid)

    @ is_bot_channel()
    @ _calendar.command(
        name='preview',
        brief='Show preview of calendar',
        description='Only on the bot-channel.'
    )
    async def _preview(self, ctx: commands.Context, *_) -> None:
        embed = self.generate_embed(preview=True)
        embed.set_author(name='PREVIEW')
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(CalendarCog(bot))
