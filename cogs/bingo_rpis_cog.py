from matplotlib.table import Table as tbl
from datetime import timedelta as td
from datetime import datetime as dt
from difflib import SequenceMatcher
from matplotlib.table import Cell
import matplotlib.pyplot as plt
from typing import ClassVar
import PIL.Image
import textwrap
import asyncio
import random
import pickle
import shutil
import json
import os
import re

from nextcord.raw_models import RawReactionActionEvent
from nextcord.permissions import PermissionOverwrite
from nextcord.mentions import AllowedMentions
from nextcord.ext import commands, tasks
from nextcord.channel import TextChannel
from nextcord.enums import MessageType
from nextcord.message import Message
from nextcord.colour import Colour
from nextcord.member import Member
from nextcord.embeds import Embed
import nextcord

from utils.console import Console, FontColour
from utils.wait_time import time_to_midnight
from utils.checks import is_channel
from utils.settings import settings

from bingo.updates_embed import updates_embed
from sggw_bot import BOT_PREFIX


_TABLE_PNG_PATH = 'bingo/bingo.png'
_TABLE_PICKLE_PATH = 'bingo/bingo.pickle'
_BINGO_PHRASES_PATH = 'bingo/bingo.txt'
_PICKLES_FOLDER = 'bingo/pickles/'
_BINGO_WIN_GIF_PATH = 'bingo/bingo_win.gif'
_BINGO_MSG_HISTORY_PATH = 'bingo/bingo_msg_history.json'
_FIREWORKS_RAW_FOLDER = 'bingo-fireworks-gif-raw/'


class _Table:
    CHECKED_COLOUR = '#5fc377'
    UNCHECKED_COLOUR = '#999999'
    TITLE_COLOUR = '#ffffff'
    ROWS_COLUMNS_COLOUR = '#696969'
    ROWS_COLUMNS_CHECKED_COLOUR = '#a0a000'
    DIM_COLS: ClassVar[int] = 4
    DIM_ROWS: ClassVar[int] = 4


class _BingoRPiSController:

    __slots__ = (
        '__bot',
    )

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.__bot = bot

    @staticmethod
    def save_bingo(table: tbl) -> None:
        plt.savefig(
            _TABLE_PNG_PATH,
            bbox_inches="tight",
            dpi=100,
            transparent=True
        )
        pickle.dump(
            table, open(_TABLE_PICKLE_PATH, 'wb')
        )

    @staticmethod
    def load_bingo() -> tbl:
        table = pickle.load(open(_TABLE_PICKLE_PATH, 'rb'))

        # Brute force but why not
        for y in range(11):
            try:
                table[y, 0]
            except KeyError:
                _Table.DIM_ROWS = y - 1
                break

        for x in range(11):
            try:
                table[0, x]
            except KeyError:
                _Table.DIM_COLS = x
                break
        return table

    @staticmethod
    def load_bingo_png() -> nextcord.File | None:
        if not os.path.exists(_TABLE_PNG_PATH):
            return None
        return nextcord.File(_TABLE_PNG_PATH)

    @classmethod
    def generate_new_bingo(cls) -> nextcord.File:
        """Generate new bingo. Save it to the file and return png file."""

        try:
            with open(_BINGO_PHRASES_PATH, encoding='utf-8') as f:
                words = f.readlines()
        except Exception as e:
            Console.error(
                f'Nie udało się załadować pliku {_BINGO_PHRASES_PATH}',
                exception=e
            )

            plt.figure().clear()
            table = plt.table(
                cellText=(('Coś',), ('poszło',), ('nie',), ('tak!',)),
                cellLoc='center',
                loc='center'
            )

            cls.save_bingo(table)
            return cls.load_bingo_png()

        random.shuffle(words)

        def wrap_text(words: list[str]) -> list:
            return ['\n'.join(textwrap.wrap(i.split('--')[0].strip(), 13)) for i in words]

        plt.figure().clear()
        table = plt.table(
            cellText=[
                wrap_text(words[i:i+_Table.DIM_COLS])
                for i in range(0, _Table.DIM_COLS*_Table.DIM_ROWS, _Table.DIM_COLS)
            ],
            cellColours=[
                [_Table.UNCHECKED_COLOUR] * _Table.DIM_COLS
            ] * _Table.DIM_ROWS,
            cellLoc='center',
            rowLabels=list(map(
                lambda i: f' {i+1}',
                range(_Table.DIM_ROWS)
            )),
            rowColours=[_Table.ROWS_COLUMNS_COLOUR] * _Table.DIM_ROWS,
            rowLoc='right',
            colLabels=list(
                map(lambda i: chr(i+65), range(_Table.DIM_COLS))
            ),
            colColours=[_Table.ROWS_COLUMNS_COLOUR] * _Table.DIM_COLS,
            colLoc='center',
            loc='center',
        )

        for i, word in enumerate(words):
            if i >= _Table.DIM_COLS * _Table.DIM_ROWS:
                break
            if len(w := word.split('--')) > 1:
                if w[1].strip().upper() == 'CHECKED':
                    x_field = i % _Table.DIM_COLS
                    y_field = i // _Table.DIM_COLS + 1
                    field = table[(y_field, x_field)]
                    field.set_facecolor(_Table.CHECKED_COLOUR)

        # The magic numbers that make table scale good
        table.scale(0.35 * _Table.DIM_COLS,
                    0.1 * _Table.DIM_ROWS + 5)

        for i in range(_Table.DIM_COLS):
            table[(0, i)].set_height(0.05)

        plt.axis('off')
        plt.grid('off')

        cls.save_bingo(table)
        return cls.load_bingo_png()


class BingoRPiSCog(commands.Cog):
    """This Cog is not well written, but it works."""

    __slots__ = (
        '__bot',
        '__generating_bingo',
        '__changing_bingo',
        '__available_args',
        '__adding_or_deleting'
    )

    __bot: commands.Bot
    __generating_bingo: bool
    __changing_bingo: bool
    __adding_or_deleting: list[int]
    __available_args: tuple[str]

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot
        self.__generating_bingo = False
        self.__changing_bingo = False
        self.__adding_or_deleting = list()
        self.__send_commands_at_midnight.start()
        self.__available_args = (
            '--force',
            '--u',
            '--s'
        )

    @tasks.loop(count=1)
    async def __send_commands_at_midnight(self) -> None:
        await self.__bot.wait_until_ready()

        while True:
            wait_time = time_to_midnight() + 5
            await asyncio.sleep(wait_time)
            self.__adding_or_deleting = list()

            modified_timestamp = os.path.getmtime(_TABLE_PICKLE_PATH)
            modified_time = dt.fromtimestamp(modified_timestamp)
            yesterday = dt.now() - td(days=1)

            if modified_time.date() != yesterday.date():
                continue

            channel_id: int = settings.get('RPIS_CHANNEL_ID')
            try:
                channel = await self.__bot.fetch_channel(channel_id)
            except Exception as e:
                return Console.important_error(
                    'Bingo channel not found. Bingo loop stopped.', e
                )

            if channel.overwrites_for(self.__bot.user).view_channel is not True:
                return Console.error(
                    'Brak permisji do wysłania komend na bingo potajemnie. '
                    'Zatrzymano pętle.'
                )

            await channel.set_permissions(
                channel.guild.default_role,
                overwrite=PermissionOverwrite(
                    view_channel=False
                )
            )
            Console.specific(
                'Usunięto everyone z kanału.', 'BINGO',
                colour=FontColour.PINK
            )
            await self._show_commands(channel)
            Console.specific(
                'Wysłano embed z komendami.', 'BINGO',
                colour=FontColour.PINK
            )
            await channel.set_permissions(
                channel.guild.default_role,
                overwrite=PermissionOverwrite(
                    view_channel=True
                )
            )
            Console.specific(
                'Przywrócono everyone do kanału.', 'BINGO',
                colour=FontColour.PINK
            )

    async def __reset_loop(self, ctx: commands.Context) -> None:
        await ctx.message.delete()
        self.__send_commands_at_midnight.stop()
        self.__send_commands_at_midnight.start()
        Console.specific(
            'Zresetowano pętlę z komendami w embedzie',
            'BINGO', colour=FontColour.PINK, bold_type=True
        )

    def __add_msg_id_to_history(self, msg: nextcord.Message) -> None:
        try:
            with open(_BINGO_MSG_HISTORY_PATH, 'r') as f:
                data: dict[str, list[int]] = json.load(f)

            try:
                data[str(msg.channel.id)].append(msg.id)
            except Exception as ee:
                print(ee)
                data[str(msg.channel.id)] = [msg.id]

            with open(_BINGO_MSG_HISTORY_PATH, 'w') as f:
                json.dump(data, f, ensure_ascii=True, indent=4)

        except Exception as e:
            Console.error(
                'Nie udało się zapisać bingo msg_id',
                exception=e
            )

    @staticmethod
    def __convert_facecolor_to_hex(cell: Cell) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            *list(map(lambda i: int(i*255), cell.get_facecolor()[:3]))
        )

    def __convert_args_to_user(self, ctx: commands.Context, args: list) -> str | Member:
        """Send args, where args[0] is user_id.
        Return reason if something went wrong.
        Otherwise, return `nextcord.Member`.
        """

        if len(args) == 0:
            return 'Podaj dodatkowy argumnt: `user_id`'

        try:
            user = ctx.guild.get_member(int(args[0]))
        except ValueError:
            return 'Wartość `user_id` nie jest liczbą całkowitą.'

        if user is None:
            return 'Nie znaleziono użytkownika o takim ID.'

        admin_role = ctx.guild.get_role(settings.get("ADMIN_ROLE_ID"))
        if admin_role in user.roles:
            return f'Nie możesz zbanować {admin_role.mention}'

        return user

    async def _ban_user(self, ctx: commands.Context, *args) -> None:
        user = self.__convert_args_to_user(ctx, args)

        if not isinstance(user, Member):
            return await ctx.reply(
                user,
                allowed_mentions=AllowedMentions.none(),
                mention_author=True,
            )

        if user.bot:
            return await ctx.reply(
                'Nie możesz zbanować bota!',
                mention_author=True,
            )

        overwrite = ctx.channel.overwrites_for(user)

        if overwrite.send_messages is False:
            return await ctx.reply(
                f'{user.mention} jest już zbanowany!',
                allowed_mentions=AllowedMentions.none(),
                mention_author=True,
            )

        overwrite.send_messages = False
        await ctx.channel.set_permissions(user, overwrite=overwrite)
        await ctx.reply(
            f'Zbanowano {user.mention}',
            allowed_mentions=AllowedMentions.none(),
            mention_author=True,
        )

    async def _unban_user(self, ctx: commands.Context, *args) -> None:
        user = self.__convert_args_to_user(ctx, args)

        if not isinstance(user, Member):
            return await ctx.reply(user)

        overwrite = ctx.channel.overwrites_for(user)

        if overwrite.send_messages is not False:
            return await ctx.reply(
                f'{user.mention} nie jest przecież zbanowany!',
                allowed_mentions=AllowedMentions.none(),
                mention_author=True,
            )

        overwrite.send_messages = None
        await ctx.channel.set_permissions(user, overwrite=overwrite)
        await ctx.reply(
            f'Odbanowano {user.mention}',
            allowed_mentions=AllowedMentions.none(),
            mention_author=True,
        )

    async def __handle_win(self, ctx: commands.Context) -> None:

        images: list[PIL.Image.Image] = []

        confetti_file_paths = sorted(
            os.listdir(_FIREWORKS_RAW_FOLDER),
            key=lambda i: int(i[6:8])
        )
        for confetti_file_path in confetti_file_paths:
            if not confetti_file_path.endswith('.png'):
                continue

            bingo_file = PIL.Image.open(_TABLE_PNG_PATH)
            bingo_png = bingo_file.convert('RGBA')

            confetti_file = PIL.Image.open(
                _FIREWORKS_RAW_FOLDER + confetti_file_path
            )
            confetti_png = confetti_file.convert('RGBA')
            confetti_png = confetti_png.resize(bingo_png.size)

            bingo_png.paste(confetti_png, (0, 0), confetti_png)
            images.append(bingo_png)

        image = images.pop(0)
        image.save(
            _BINGO_WIN_GIF_PATH, 'GIF', append_images=images,
            save_all=True, duration=100, disposal=2, loop=0
        )

        bingo_gif = nextcord.File(_BINGO_WIN_GIF_PATH)
        msg = await ctx.reply(
            file=bingo_gif,
            mention_author=False
        )
        self.__add_msg_id_to_history(msg)
        self.__update_pickle_file(msg)
        self.__changing_bingo = False

    @commands.command(
        name='bingo',
        brief='Check out field in RPiS bingo!',
        description=f'''Use: `{BOT_PREFIX}bingo <field>` where field is a cell,
        example: `{BOT_PREFIX}bingo a3`

        Use: `{BOT_PREFIX}bingo new` to generate new bingo.
        The sent message will be the main message now.
        This message can be send only on this channel.
        You can add '--<col>x<row>` to generate bingo with specific dimensions.

        Use: `{BOT_PREFIX}bingo add <text...>` to add a new phrase.
        Voting will start.

        Use: `{BOT_PREFIX}bingo del <text...>` to delete a new phrase.
        <text> doesn't have to be exact.
        The most accurate will be selected.
        Voting will start.

        Use `{BOT_PREFIX}bingo phrases` to send file with all phrases.

        Use: `{BOT_PREFIX}bingo show` to send bingo again.

        @AdminOnly
        Use: `{BOT_PREFIX}bingo ban <user_id>` to prohibit a user from posting on this channel.
        Use: `{BOT_PREFIX}bingo unban <user_id>` to undo it.
        Use: `{BOT_PREFIX}bingo info` to send info about updates.
        Use: `{BOT_PREFIX}bingo commands` to send info how to use bingo.
        Use: `{BOT_PREFIX}bingo load <message_id>` to load old bingo from message.
        '''
    )
    @is_channel('RPIS_CHANNEL_ID', 'BOT_CHANNEL_ID')
    async def _bingo(self, ctx: commands.Context, field: str = "", *args) -> None:

        regex = r'^([-]{2})([1-9]{1})([xX]{1})([1-9]{1})$'

        _Table.DIM_COLS = 4
        _Table.DIM_ROWS = 4

        arg: str
        for arg in args:
            if field.upper() in ('ADD', 'DEL', 'LOAD'):
                break

            if re.match(regex, arg):
                cols = int(arg[2])
                rows = int(arg[4])
                try:
                    if cols * rows > (l := len(open(_BINGO_PHRASES_PATH, encoding='utf-8').readlines())):
                        return await ctx.reply(
                            f'Obecnie liczba powiedzonek wynosi {l}.\n'
                            'Nie można wygenerować bingo z większą ilością pól.',
                            mention_author=True
                        )
                except Exception as e:
                    Console.important_error(
                        'Nie można sprawdzić argumentu wymiaru!', e
                    )
                    return await ctx.reply(
                        'Coś poszło nie tak... Skontaktuj się z Adminem...'
                    )
                _Table.DIM_COLS = cols
                _Table.DIM_ROWS = rows
            elif arg.lower() not in self.__available_args:
                return await ctx.reply(
                    f'Nieprawidłowy argument: `{arg}`.'
                )

        if ctx.channel.id == int(settings.get('BOT_CHANNEL_ID')) and (len(args) == 0 or '--s' not in args):
            async with ctx.typing():
                return await ctx.reply(
                    'Jeśli jesteś pewien, że chcesz użyć tego tu, dopisz `--s` na końcu!'
                )

        if field == "":
            async with ctx.typing():
                return await ctx.reply(
                    'Niepoprawne użycie komendy.\n'
                    f'Aby dowiedzieć się więcej, napisz - `{BOT_PREFIX}help bingo`',
                    mention_author=True
                )

        if field.upper() in ('NEW', 'NOWA'):
            return await self._new_bingo(ctx, *args)

        async with ctx.typing():
            match field.upper():
                case 'SHOW':
                    return await self._show_bingo_again(ctx)
                case 'PHRASES':
                    return await self._send_phrases(ctx)
                case 'ADD':
                    return await self._add_phrase(ctx, ' '.join(args).upper())
                case 'DEL':
                    return await self._del_phrase(ctx, ' '.join(args))

            if field.upper() in ('BAN', 'UNBAN', 'INFO', 'LOAD', 'COMMANDS', 'RESET_LOOP'):
                admin_role = ctx.guild.get_role(settings.get("ADMIN_ROLE_ID"))
                if admin_role in ctx.author.roles:
                    match field.upper():
                        case 'BAN':
                            return await self._ban_user(ctx, *args)
                        case 'UNBAN':
                            return await self._unban_user(ctx, *args)
                        case 'INFO':
                            return await self._show_info(ctx)
                        case 'LOAD':
                            return await self._load_pickle(ctx, *args)
                        case 'COMMANDS':
                            return await self._show_commands(ctx)
                        case 'RESET_LOOP':
                            return await self.__reset_loop(ctx)
                return await ctx.reply(
                    f'Tylko {admin_role.mention} może używać tej funkcji!',
                    allowed_mentions=AllowedMentions.none(),
                    mention_author=True,
                )

            def generate_random_field() -> str:
                letter_id = random.randint(0, _Table.DIM_COLS - 1)
                letter = chr(letter_id + 65 + random.randint(0, 1) * 32)
                number = random.randint(1, _Table.DIM_ROWS)
                return f'{letter}{number}'

            if len(field) != 2:
                return await ctx.reply(
                    'Złe użycie funkcji!\n'
                    f'Prawidłowe użycie: **{BOT_PREFIX}bingo <kolumna><wiersz>** '
                    f'np. **{BOT_PREFIX}bingo {generate_random_field()}**'
                )

            try:
                table = _BingoRPiSController.load_bingo()
            except Exception as e:
                Console.error(
                    "Problem z ładowaniem bingo.pickle", exception=e
                )
                return await ctx.reply(
                    'Coś poszło nie tak!\n'
                    'Szczegółowe informacje w konsoli programisty.'
                )

            try:
                x_field = ord(field[0].upper()) - 65
                y_field = int(field[1])
            except:
                return await ctx.reply(
                    'Złe użycie funkcji!\n'
                    f'Prawidłowe użycie: **{BOT_PREFIX}bingo <kolumna><wiersz>** '
                    f'np. **{BOT_PREFIX}bingo {generate_random_field()}**'
                )

            if not (0 <= x_field < _Table.DIM_COLS):
                reason = f'Wartość <kolumna> nie mieści się z zakresu A-{chr(_Table.DIM_COLS + 65 - 1)}!'
            elif not (0 < y_field <= _Table.DIM_ROWS):
                reason = f'Wartość <wiersz> nie mieści się z zakresu 1-{_Table.DIM_ROWS}!'
            else:
                reason = None

            if reason is not None:
                return await ctx.reply(f'Nieprawidłowe pole! {reason}')

            if self.__changing_bingo:
                return await ctx.reply(
                    'Obecnie przetwarzana jest inna komenda. '
                    'Spróbuj ponownie za chwilę.'
                )

            self.__changing_bingo = True

            cell: Cell = table[(y_field, x_field)]
            current_facecolor = self.__convert_facecolor_to_hex(cell)
            cell_name = cell.get_text().get_text().replace('\n', ' ').replace('*', '\\*')

            if current_facecolor == _Table.CHECKED_COLOUR:
                if '--u' not in map(str.lower, args):
                    self.__changing_bingo = False
                    return await ctx.reply(
                        'To pole jest już zaznaczone. Jeśli chcesz je odznaczyć, dopisz na końcu `--u`.'
                    )
                cell.set_facecolor(_Table.UNCHECKED_COLOUR)
                action_done = 'Odznaczono'
            elif current_facecolor == _Table.UNCHECKED_COLOUR:
                if '--u' in map(str.lower, args):
                    self.__changing_bingo = False
                    return await ctx.reply(
                        'To pole nie jest zaznaczone, `--u` używa się do odznaczania.'
                    )
                cell.set_facecolor(_Table.CHECKED_COLOUR)
                action_done = 'Zaznaczono'

            for y in range(1, _Table.DIM_ROWS + 1):
                row = [table[y, x] for x in range(_Table.DIM_COLS)]
                if all(map(lambda i: self.__convert_facecolor_to_hex(i) == _Table.CHECKED_COLOUR, row)):
                    table[y, -1].set_facecolor(
                        _Table.ROWS_COLUMNS_CHECKED_COLOUR
                    )
                else:
                    table[y, -1].set_facecolor(
                        _Table.ROWS_COLUMNS_COLOUR
                    )

            for x in range(_Table.DIM_COLS):
                column = [table[y, x] for y in range(1, _Table.DIM_ROWS + 1)]
                if all(map(lambda i: self.__convert_facecolor_to_hex(i) == _Table.CHECKED_COLOUR, column)):
                    table[0, x].set_facecolor(
                        _Table.ROWS_COLUMNS_CHECKED_COLOUR
                    )
                else:
                    table[0, x].set_facecolor(
                        _Table.ROWS_COLUMNS_COLOUR
                    )

            _BingoRPiSController.save_bingo(table)
            bingo_png = _BingoRPiSController.load_bingo_png()

            for y, x in table.get_celld():
                if y == 0 or x == -1:
                    continue
                cell = table[y, x]
                current_facecolor = self.__convert_facecolor_to_hex(cell)
                if current_facecolor == _Table.UNCHECKED_COLOUR:
                    break
            else:
                return await self.__handle_win(ctx)

            msg = await ctx.reply(
                f'{action_done}: **{cell_name}**',
                file=bingo_png,
                mention_author=False
            )
        self.__add_msg_id_to_history(msg)
        self.__changing_bingo = False
        self.__update_pickle_file(msg)

    async def __depracte_messeges(self, ctx: commands.Context, old_msg_ids: list[int]) -> None:
        async def deprecate_message(id: str) -> None:
            try:
                msg = await ctx.channel.fetch_message(id)
                await msg.edit(
                    content=f'{msg.content}\n**PRZESTARZAŁE**',
                    allowed_mentions=AllowedMentions.none()
                )
            except:
                ...
        await asyncio.gather(
            *(deprecate_message(i) for i in old_msg_ids)
        )

    async def _send_phrases(self, ctx: commands.Context) -> None:
        with open(_BINGO_PHRASES_PATH, 'r', encoding='utf-8') as f:
            phrases = f.readlines()

        phrases = map(lambda i: i.replace('*', '\\*'), phrases)

        description = ''.join(
            [f'**{i+1}.** {p}' for i, p in enumerate(phrases)]
        )

        embed = Embed(
            title='**OBECNE POWIEDZONKA:**',
            description=description,
            colour=Colour.gold()
        )

        await ctx.reply(embed=embed)

    def __update_pickle_file(self, msg: Message):
        source = _TABLE_PICKLE_PATH
        destination = f'{_PICKLES_FOLDER}{msg.id}.pickle'
        shutil.copy(source, destination)

    async def __send_bingo(self, ctx: commands.Context) -> None:
        message = await ctx.reply(
            'Generowanie bingo, proszę czekać... ',
            mention_author=False
        )

        self.__add_msg_id_to_history(message)
        bingo_png = _BingoRPiSController.generate_new_bingo()
        msg = await message.edit(
            content='**WYGENEROWANO NOWE BINGO**',
            file=bingo_png,
            allowed_mentions=AllowedMentions.none()
        )
        self.__update_pickle_file(msg)

    async def _show_commands(self, ctx_or_channel: TextChannel | commands.Context) -> None:
        """If ctx was sent, the trigger message will be deleted."""

        embed = Embed(
            title='BINGO RPIS KOMENDY',
            colour=Colour.green()
        ).add_field(
            name='GENEROWANIE NOWEGO BINGO:',
            value=f'**{BOT_PREFIX}bingo new**\n'
            '*dopisz \'--<kolumny>x<wiersze>\' by zmienić wielkość*',
            inline=False,
        ).add_field(
            name='ZAZNACZANIE PÓL:',
            value=f'**{BOT_PREFIX}bingo <kolumna><wiersz>** np. **{BOT_PREFIX}bingo b2**\n'
            '*dopisz \'--u\' aby odznaczyć*',
            inline=False,
        ).add_field(
            name='PODGLĄD OBECNYCH POWIEDZONEK:',
            value=f'**{BOT_PREFIX}bingo phrases**',
            inline=False,
        ).add_field(
            name='ROZPOCZĘCIE GŁOSOWANIA O DODANIE SŁÓWKA:',
            value=f'**{BOT_PREFIX}bingo add <słówko...>**',
            inline=False,
        ).add_field(
            name='ROZPOCZĘCIE GŁOSOWANIA O USUNIĘCIE SŁÓWKA:',
            value=f'**{BOT_PREFIX}bingo del <zbliżone_słówko...>**',
            inline=False,
        ).set_footer(
            text='Uwagi proszę kierować do Wiktor J lub Krzysztof K'
        )

        if isinstance(ctx_or_channel, commands.Context):
            await asyncio.gather(
                ctx_or_channel.message.delete(),
                ctx_or_channel.send(embed=embed),
            )
        else:
            await ctx_or_channel.send(embed=embed)

    async def _show_info(self, ctx: commands.Context) -> None:
        embed = updates_embed()

        await asyncio.gather(
            ctx.message.delete(),
            ctx.send(embed=embed),
        )

    async def _show_bingo_again(self, ctx: commands.Context) -> None:
        bingo_png = _BingoRPiSController.load_bingo_png()
        if bingo_png is None:
            return await ctx.reply(
                'Wystąpił problem z wczytaniem ostatniego bingo...',
                mention_author=True
            )

        message = await ctx.reply(file=bingo_png, mention_author=False)
        self.__add_msg_id_to_history(message)
        self.__update_pickle_file(message)

    async def _new_bingo(self, ctx: commands.Context, *args) -> None:
        if self.__generating_bingo:
            return await ctx.reply(
                'Nie można obecnie wygenerować bingo. '
                'Spróbuj ponownie później.'
            )

        if os.path.exists(_TABLE_PNG_PATH):
            modified_timestamp = os.path.getmtime(_TABLE_PNG_PATH)
            modified_time = dt.fromtimestamp(modified_timestamp)
            if modified_time + td(minutes=15) > dt.now():
                if '--force' not in map(str.lower, args):
                    return await ctx.reply(
                        'Ostatnie bingo było używane mniej niż 15 min temu.\n'
                        'Jesteś pewny/a, że chcesz wygenerować nowe?\n'
                        f'Jeśli tak, użyj komendy: **{BOT_PREFIX}bingo new --force**\n'
                        'Poprzednia plansza do bingo zostanie napisana i nie będzie można już jej edytować!\n'
                        'Robienie na złość innym może skończyć się banem na tym kanale!'
                    )

        self.__generating_bingo = True

        try:
            with open(_BINGO_MSG_HISTORY_PATH, 'r') as f:
                data: dict[str, list[int]] = json.load(f)

            old_msg_ids = data.get(str(ctx.channel.id)) or list()
            data[str(ctx.channel.id)] = list()

            with open(_BINGO_MSG_HISTORY_PATH, 'w') as f:
                json.dump(data, f, ensure_ascii=True, indent=4)

        except Exception as e:
            old_msg_ids = []
            Console.error(
                'Nie udało się załadować bingo msg_id',
                exception=e
            )

        await asyncio.gather(
            self.__send_bingo(ctx),
            self.__depracte_messeges(ctx, old_msg_ids)
        )

        self.__generating_bingo = False

    async def _load_pickle(self, ctx: commands.Context, *args) -> None:
        if len(args) == 0:
            return await ctx.reply(
                'Podaj dodatkowy argument: message_id'
            )

        path = f'{_PICKLES_FOLDER}{args[0]}.pickle'

        try:
            table = pickle.load(open(path, 'rb'))
        except:
            return await ctx.reply(
                'Niepoprawne id wiadomości lub takie bingo nie istnieje.'
            )

        shutil.copy(path, _TABLE_PICKLE_PATH)
        _BingoRPiSController.save_bingo(table)
        bingo_png = _BingoRPiSController.load_bingo_png()
        msg = await ctx.reply(
            '**ZAŁADOWANO BINGO**',
            file=bingo_png,
            mention_author=False
        )
        self.__add_msg_id_to_history(msg)
        self.__update_pickle_file(msg)

    @staticmethod
    def __get_phrases_ratio(text: str) -> dict[str, float]:
        with open(_BINGO_PHRASES_PATH, 'r', encoding='utf-8') as f:
            phrases = f.readlines()

        matches: dict[str, float] = dict()
        for phrase in phrases:
            ratio = SequenceMatcher(None, phrase.lower(), text.lower()).ratio()
            matches[phrase] = ratio

        return matches

    async def _add_phrase(self, ctx: commands.Context, text: str) -> None:
        if text.endswith('--A'):
            text = text.split(' --A')[0]
            force = True
        else:
            force = False

        matches = self.__get_phrases_ratio(text)
        if not force and max(matches.values()) >= 0.75:
            similar: list[str] = []
            for k, v in matches.items():
                if v >= 0.75:
                    similar.append(k)

            return await ctx.reply(
                'Podobne powiedzonka już istnieją:\n**'
                + ''.join(similar).replace('*', '\\*') +
                '**Jeśli chcesz dodać swoje, napisz komendę jeszcze raz, dopsiując `--a` na końcu.'
            )

        text = text.replace("*", "\\*")
        msg = await ctx.reply(
            f'Propozycja dodania powiedzonka od {ctx.author.mention}:\n'
            f'\"**{text}**\"\n\n'
            'Aby powiedzonko zostało dodane, musi znaleźć się pod tą wiadomością '
            'o 10 reakcji więcej pozytywnych niż negatywnych.',
            mention_author=False
        )
        await asyncio.gather(
            msg.pin(),
            msg.add_reaction('👍'),
            msg.add_reaction('👎'),
        )

    async def _del_phrase(self, ctx: commands.Context, text: str) -> None:
        matches = self.__get_phrases_ratio(text)

        if (m := max(matches.values())) <= 0.5:
            return await ctx.reply(
                f'Nie znaleziono nic podobnego do {text}!'
            )

        for k, v in matches.items():
            if v == m:
                break

        k = k.replace("*", "\\*").replace('\n', '')
        msg = await ctx.reply(
            f'Propozycja usunięcia powiedzonka od {ctx.author.mention}:\n'
            f'\"**{k}**\"\n\n'
            'Aby powiedzonko zostało usunięte, musi znaleźć się pod tą wiadomością '
            'o 10 reakcji więcej pozytywnych niż negatywnych.',
            mention_author=False
        )
        await asyncio.gather(
            msg.pin(),
            msg.add_reaction('👍'),
            msg.add_reaction('👎'),
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        if (
            payload.member.bot
            or payload.channel_id != settings.get('RPIS_CHANNEL_ID')
        ):
            return

        guild = self.__bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        if (
            not msg.author.bot
            or not (
                msg.content.startswith('Propozycja dodania powiedzonka od')
                or msg.content.startswith('Propozycja usunięcia powiedzonka od')
            )
            or msg.content.endswith('**DODANO**')
            or msg.content.endswith('**USUNIĘTO**')
        ):
            return

        bot_reaction = False
        for reaction in msg.reactions:
            async for user in reaction.users():
                if user == self.__bot.user:
                    bot_reaction = True
                    break
                # if user == payload.member and str(reaction.emoji) != str(payload.emoji):
                #     await msg.remove_reaction(reaction.emoji, user)

        msg = await channel.fetch_message(payload.message_id)

        async def user_reaction(emoji: str) -> list[Member]:
            for reaction in msg.reactions:
                if str(reaction) == emoji:
                    return await reaction.users().flatten()

        positive, negative = await asyncio.gather(
            user_reaction('👍'),
            user_reaction('👎'),
        )

        if len(positive) - len(negative) < 10:
            return

        if payload.message_id in self.__adding_or_deleting:
            return

        self.__adding_or_deleting.append(payload.message_id)

        if not bot_reaction:
            return

        if positive:
            to_add = '**Byli za:**\n'
            to_add += ('\n'.join(
                [f'\t*{member.display_name} ({member})*' for member in positive if not member.bot]
            ) or '\t-')
        else:
            to_add = ""

        if negative:
            to_no_add = '**Byli przeciw:**\n'
            to_no_add += ('\n'.join(
                [f'\t*{member.display_name} ({member})*' for member in negative if not member.bot]
            ) or '\t-')
        else:
            to_no_add = ""

        async with channel.typing():
            phrase = msg.content.split(
                '\n')[1][3:-3].replace('\\', '').strip()

            if msg.content.startswith('Propozycja dodania powiedzonka od'):
                with open(_BINGO_PHRASES_PATH, 'a', encoding='utf-8') as f:
                    f.write(f'\n{phrase}')
                phrase = phrase.replace('*', '\\*')
                await asyncio.gather(
                    msg.reply(
                        'Dodano nowe powiedzonko!\n'
                        f'\"**{phrase}**\"\n\n'
                        f'{to_add}\n'
                        f'{to_no_add}'
                    ),
                    msg.unpin(),
                    msg.edit(f'{msg.content}\n\n**DODANO**'),
                    msg.clear_reactions()
                )

            elif msg.content.startswith('Propozycja usunięcia powiedzonka od'):
                with open(_BINGO_PHRASES_PATH, 'r', encoding='utf-8') as f:
                    phrases = list(map(str.strip, f.readlines()))

                for p in phrases:
                    if p.strip() == phrase:
                        phrases.remove(p)
                        break
                else:
                    return

                with open(_BINGO_PHRASES_PATH, 'w', encoding='utf-8') as f:
                    f.writelines(map(lambda i: i + '\n', phrases[:-1]))
                    f.write(phrases[-1])

                phrase = phrase.replace('*', '\\*')
                await asyncio.gather(
                    msg.reply(
                        'Usunięto powiedzonko!\n'
                        f'\"**{phrase}**\"\n\n'
                        f'{to_add}\n'
                        f'{to_no_add}'
                    ),
                    msg.unpin(),
                    msg.edit(f'{msg.content}\n\n**USUNIĘTO**'),
                    msg.clear_reactions()
                )

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if (
            not message.author.bot
            or message.channel.id != settings.get('RPIS_CHANNEL_ID')
            or message.type != MessageType.pins_add
        ):
            return

        await message.delete()


def setup(bot: commands.Bot):
    bot.add_cog(BingoRPiSCog(bot))
