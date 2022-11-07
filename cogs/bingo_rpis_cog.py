from matplotlib.table import Table as tbl
import matplotlib.pyplot as plt
import datetime as dt
import PIL.Image
import textwrap
import asyncio
import random
import pickle
import os

from nextcord.mentions import AllowedMentions
from nextcord.colour import Colour
from nextcord.member import Member
from nextcord.embeds import Embed
from nextcord.ext import commands
import nextcord

from utils.checks import is_channel
from utils.settings import settings
from utils.console import Console
from main import BOT_PREFIX


_TABLE_PNG_PATH = 'bingo.png'
_TABLE_PICKLE_PATH = 'bingo.pickle'
_BINGO_PHRASES_PATH = 'files/bingo.txt'
_FIREWORKS_RAW_FOLDER = 'bingo-fireworks-gif-raw/'


class _Table:
    CHECKED_COLOUR = '#5fc377'
    UNCHECKED_COLOUR = '#999999'
    TITLE_COLOUR = '#ffffff'
    ROWS_COLUMNS_COLOUR = '#696969'
    ROWS_COLUMNS_CHECKED_COLOUR = '#a0a000'
    DIMENSION = 4

    assert 0 < DIMENSION <= 26


class _BingoRPiSController:

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.__bot = bot

    @staticmethod
    def save_bingo(table: tbl) -> None:
        plt.savefig(
            _TABLE_PNG_PATH,
            bbox_inches="tight",
            dpi=300,
            transparent=True
        )
        pickle.dump(
            table, open(_TABLE_PICKLE_PATH, 'wb')
        )

    @staticmethod
    def load_bingo() -> tbl:
        return pickle.load(open(_TABLE_PICKLE_PATH, 'rb'))

    @staticmethod
    def load_bingo_png() -> nextcord.File | None:
        if not os.path.exists(_TABLE_PNG_PATH):
            return None
        return nextcord.File(_TABLE_PNG_PATH)

    @classmethod
    def generate_new_bingo(cls) -> nextcord.File:
        """Generate new bingo. Save it to the file and return png file."""

        try:
            with open('files/bingo.txt', encoding='utf-8') as f:
                words = f.readlines()
        except Exception as e:
            Console.error(
                'Nie udało się załadować pliku files/bingo.txt',
                exception=e
            )
            table = plt.table(
                cellText=(('Coś',), ('poszło',), ('nie',), ('tak!',)),
                cellLoc='center',
                loc='center'
            )
        else:
            random.shuffle(words)

            def wrap_text(words: list[str]) -> list:
                return ['\n'.join(textwrap.wrap(i.split('--')[0].strip(), 13)) for i in words]

            table = plt.table(
                cellText=[
                    wrap_text(words[i:i+_Table.DIMENSION])
                    for i in range(0, _Table.DIMENSION**2, _Table.DIMENSION)
                ],
                cellColours=[
                    [_Table.UNCHECKED_COLOUR] * _Table.DIMENSION
                ] * _Table.DIMENSION,
                cellLoc='center',
                rowLabels=list(map(
                    lambda i: f' {i+1}',
                    range(_Table.DIMENSION)
                )),
                rowColours=[_Table.ROWS_COLUMNS_COLOUR] * _Table.DIMENSION,
                rowLoc='right',
                colLabels=list(
                    map(lambda i: chr(i+65), range(_Table.DIMENSION))
                ),
                colColours=[_Table.ROWS_COLUMNS_COLOUR] * _Table.DIMENSION,
                colLoc='center',
                loc='center',
            )

            for i, word in enumerate(words):
                if i >= _Table.DIMENSION ** 2:
                    break
                if len(w := word.split('--')) > 1:
                    if w[1].strip().upper() == 'CHECKED':
                        x_field = i % _Table.DIMENSION
                        y_field = i // _Table.DIMENSION + 1
                        field = table[(y_field, x_field)]
                        field.set_facecolor(_Table.CHECKED_COLOUR)

        table.scale(1.5, 5.2)

        for i in range(_Table.DIMENSION):
            table[(0, i)].set_height(0.05)

        plt.axis('off')
        plt.grid('off')
        plt.title(
            'R P i S',
            fontsize=25,
            color=_Table.TITLE_COLOUR
        )

        cls.save_bingo(table)
        return cls.load_bingo_png()


class BingoRPiSCog(commands.Cog):
    """This Cog is not well written, but it works."""

    __slots__ = (
        '__bot',
        '__generating_bingo',
        '__changing_bingo'
    )

    __bot: commands.Bot
    __generating_bingo: bool
    __changing_bingo: bool

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot
        self.__generating_bingo = False
        self.__changing_bingo = False

    def __add_msg_id_to_history(self, msg: nextcord.Message) -> None:
        try:
            with open('bingo_msg_history.txt', 'a') as f:
                f.write(str(msg.id) + '\n')
        except Exception as e:
            Console.error(
                'Nie udało się zapisać bingo msg_id',
                exception=e
            )

    @staticmethod
    def __convert_facecolor_to_hex(field) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            *list(map(lambda i: int(i*255), field.get_facecolor()[:3]))
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

        for confetti_file_path in os.listdir(_FIREWORKS_RAW_FOLDER):
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
            'bingo_win.gif', 'GIF', append_images=images,
            save_all=True, duration=100, disposal=2, loop=0
        )

        bingo_gif = nextcord.File('bingo_win.gif')
        await asyncio.sleep(0.12)
        msg = await ctx.reply(
            file=bingo_gif,
            mention_author=False
        )
        self.__add_msg_id_to_history(msg)
        self.__changing_bingo = False

    @commands.command(
        name='bingo',
        brief='Check out field in RPiS bingo!',
        description='''Use: `bingo <field>` where field is a cell,
        example: `bingo A3`

        Use: `bingo new` to generate new bingo.
        The sent message will be the main message now.
        This message can be send only on this channel.

        Use: `bingo show` to send bingo again.

        @AdminOnly
        Use: `bingo ban <user_id>` to prohibit a user from posting on this channel.
        Use: `bingo unban <user_id>` to undo it.
        Use: `bingo info` to send info how to use bingo.
        '''
    )
    @is_channel('RPIS_CHANNEL_ID', 'BOT_CHANNEL_ID')
    async def _bingo(self, ctx: commands.Context, field: str = "", *args) -> None:
        if ctx.channel.id == int(settings.get('BOT_CHANNEL_ID')) and (len(args) == 0 or args[0] != '--s'):
            return await ctx.reply(
                'Jeśli jesteś pewien, że chcesz użyć tego tu, dopisz `--s` na końcu!'
            )

        if field == "":
            return await ctx.reply(
                'Niepoprawne użycie komendy.\n'
                f'Aby dowiedzieć się więcej, napisz - `{BOT_PREFIX}help bingo`',
                mention_author=True
            )

        if field.upper() in ('NEW', 'NOWA'):
            return await self._new_bingo(ctx, *args)

        if field.upper() == 'SHOW':
            return await self._show_bingo_again(ctx)

        if field.upper() in ('BAN', 'UNBAN', 'INFO'):
            admin_role = ctx.guild.get_role(settings.get("ADMIN_ROLE_ID"))
            if admin_role in ctx.author.roles:
                match field.upper():
                    case 'BAN':
                        return await self._ban_user(ctx, *args)
                    case 'UNBAN':
                        return await self._unban_user(ctx, *args)
                    case 'INFO':
                        return await self._show_info(ctx)
            return await ctx.reply(
                f'Tylko {admin_role.mention} może używać tej funkcji!',
                allowed_mentions=AllowedMentions.none(),
                mention_author=True,
            )

        def generate_random_field() -> str:
            letter_id = random.randint(0, _Table.DIMENSION - 1)
            letter = chr(letter_id + 65 + random.randint(0, 1) * 32)
            number = random.randint(1, _Table.DIMENSION)
            return f'{letter}{number}'

        if len(field) != 2:
            return await ctx.reply(
                'Złe użycie funkcji!\n'
                f'Prawidłowe użycie: **{BOT_PREFIX}bingo <kolumna><wiersz>** '
                f'np. **{BOT_PREFIX}bingo {generate_random_field()}**'
            )

        table = _BingoRPiSController.load_bingo()

        try:
            x_field = ord(field[0].upper()) - 65
            y_field = int(field[1])
        except:
            return await ctx.reply(
                'Złe użycie funkcji!\n'
                f'Prawidłowe użycie: **{BOT_PREFIX}bingo <kolumna><wiersz>** '
                f'np. **{BOT_PREFIX}bingo {generate_random_field()}**'
            )

        if not (0 <= x_field < _Table.DIMENSION):
            reason = f'Wartość <kolumna> nie mieści się z zakresu A-{chr(_Table.DIMENSION + 65 - 1)}!'
        elif not (0 < y_field <= _Table.DIMENSION):
            reason = f'Wartość <wiersz> nie mieści się z zakresu 1-{_Table.DIMENSION}!'
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

        field = table[(y_field, x_field)]
        current_facecolor = self.__convert_facecolor_to_hex(field)

        if current_facecolor == _Table.CHECKED_COLOUR:
            field.set_facecolor(_Table.UNCHECKED_COLOUR)
        elif current_facecolor == _Table.UNCHECKED_COLOUR:
            field.set_facecolor(_Table.CHECKED_COLOUR)

        for y in range(1, _Table.DIMENSION + 1):
            row = [table[y, x] for x in range(_Table.DIMENSION)]
            if all(map(lambda i: self.__convert_facecolor_to_hex(i) == _Table.CHECKED_COLOUR, row)):
                table[y, -1].set_facecolor(_Table.ROWS_COLUMNS_CHECKED_COLOUR)
            else:
                table[y, -1].set_facecolor(_Table.ROWS_COLUMNS_COLOUR)

        for x in range(_Table.DIMENSION):
            column = [table[y, x] for y in range(1, _Table.DIMENSION + 1)]
            if all(map(lambda i: self.__convert_facecolor_to_hex(i) == _Table.CHECKED_COLOUR, column)):
                table[0, x].set_facecolor(_Table.ROWS_COLUMNS_CHECKED_COLOUR)
            else:
                table[0, x].set_facecolor(_Table.ROWS_COLUMNS_COLOUR)

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

        await asyncio.sleep(0.12)
        msg = await ctx.reply(file=bingo_png, mention_author=False)
        self.__add_msg_id_to_history(msg)
        self.__changing_bingo = False

    async def __depracte_messeges(self, ctx: commands.Context, old_msg_ids: list[str]) -> None:
        async def deprecate_message(id: str) -> None:
            try:
                _id = int(id)
                msg = await ctx.channel.fetch_message(_id)
                await msg.edit(
                    content="**PRZESTARZAŁE**",
                    allowed_mentions=AllowedMentions.none()
                )
            except:
                ...
        await asyncio.gather(
            *(deprecate_message(i) for i in old_msg_ids)
        )

    async def __send_bingo(self, ctx: commands.Context) -> nextcord.Message:
        message = await ctx.reply(
            'Generowanie bingo, proszę czekać... ',
            mention_author=False
        )

        self.__add_msg_id_to_history(message)
        bingo_png = _BingoRPiSController.generate_new_bingo()
        return await message.edit(
            content='',
            file=bingo_png,
            allowed_mentions=AllowedMentions.none()
        )

    async def _show_info(self, ctx: commands.Context) -> None:
        phrases = ''.join(
            f'{i+1}. {j.split("--")[0]}' for i, j in enumerate(open(
                _BINGO_PHRASES_PATH, 'r',
                encoding='utf-8').readlines())
        )

        phrases2 = ""
        for i in phrases:
            if i == '*':
                phrases2 += '\\'
            phrases2 += i

        embed = Embed(
            title='Nudzi Ci się na lekcji RPiS?',
            description='Zawsze można zagrać w bingo! 😁',
            colour=Colour.blurple()
        ).add_field(
            name='Generowanie nowego bingo:',
            value=f'{BOT_PREFIX}bingo new',
            inline=False,
        ).add_field(
            name='Zaznaczanie pól:',
            value=f'{BOT_PREFIX}bingo <kolumna><wiersz>\n*(np. {BOT_PREFIX}bingo B2)*',
            inline=False,
        ).add_field(
            name='Zaleca się wyznaczenie konkretnej osoby z grupy,',
            value='która będzie podczas lekcji obsługiwała bingo.',
            inline=False,
        ).add_field(
            name='Obecne powiedzonka:',
            value=phrases2,
            inline=False,
        ).add_field(
            name='Aktualizacja!',
            value=(
                "Zmiany:\n"
                "1. Nowe hasła\n"
                "2. Efekt wygranej\n"
                "3. Zmiana kolorów"
            ),
            inline=False,
        ).set_footer(
            text='Uwagi lub propozycje powiedzonek proszę przesyłać do Wiktor J lub Krzysztof K'
        )

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

    async def _new_bingo(self, ctx: commands.Context, *args) -> None:
        if self.__generating_bingo:
            return await ctx.reply(
                'Nie można obecnie wygenerować bingo. '
                'Spróbuj ponownie później.'
            )

        if os.path.exists(_TABLE_PNG_PATH):
            modified_timestamp = os.path.getmtime(_TABLE_PNG_PATH)
            modified_time = dt.datetime.fromtimestamp(modified_timestamp)
            if modified_time + dt.timedelta(minutes=15) > dt.datetime.now():
                if len(args) > 0 and isinstance(args[0], str) and args[0].lower() != '--force':
                    return await ctx.reply(f'Niepoprawny argument: ***{args[0]}***')
                if len(args) == 0 or not isinstance(args[0], str) or args[0].lower() != '--force':
                    return await ctx.reply(
                        'Ostatnie bingo było używane mniej niż 15 min temu.\n'
                        'Jesteś pewny/a, że chcesz wygenerować nowe?\n'
                        f'Jeśli tak, użyj komendy: **{BOT_PREFIX}bingo new --force**\n'
                        'Poprzednia plansza do bingo zostanie napisana i nie będzie można już jej edytować!\n'
                        'Robienie na złość innym może skończyć się banem na tym kanale!'
                    )

        self.__generating_bingo = True

        try:
            with open('bingo_msg_history.txt', 'r') as f:
                old_msg_ids = f.readlines()
            with open('bingo_msg_history.txt', 'w') as f:
                f.write('')
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


def setup(bot: commands.Bot):
    bot.add_cog(BingoRPiSCog(bot))
