import os

from nextcord.message import Message
from nextcord.ext import commands

from utils.checks import has_admin_role, is_bot_channel
from utils.settings import load_settings
from utils.console import Console


class TestCog(commands.Cog):
    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        Console.info('Bot załadowany')

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.content:
            Console.message(
                message.content,
                f'{message.author.display_name}/{message.author}/{message.channel}'
            )

    @has_admin_role()
    @is_bot_channel()
    @commands.command(
        name='print',
        brief='Print message content to the console',
        description='''Only on the bot-channel. Only for debug.'''
    )
    async def _print(self, _, *args) -> None:
        print('\n'.join(args))

    @has_admin_role()
    @is_bot_channel()
    @commands.command(
        name='reload_settings',
        brief='Reload settings from json',
        description='Only on the bot-channel'
    )
    async def _reload_settings(self, ctx: commands.Context, *_) -> None:
        try:
            load_settings()
        except Exception as e:
            Console.important_error('Nie udało się przeładować ustawień', e)
            await ctx.send(f'{ctx.author.mention} {e}')
        else:
            await ctx.send(f'{ctx.author.mention} Przeładowano ustawienia.')

    @has_admin_role()
    @is_bot_channel()
    @commands.group(name='cogs', brief='Discord alias for `category`')
    async def _cogs(self, *_) -> None:
        pass

    async def __load_cog(self, ctx: commands.Context, cog_path: str) -> None:
        try:
            self.__bot.load_extension(cog_path)
        except Exception as e:
            return await ctx.send(
                f'Cog \'{cog_path}\' cannot be loaded.\n'
                f'Reason: {e}'
            )

        await ctx.send(f'Pomyślnie przeładowano/załadowano {cog_path}')
        Console.cogs(f'{ctx.author.display_name} podłączył {cog_path}')

    @_cogs.command(
        name='load',
        brief='Load cog',
        description='''Only on the bot-channel.
        If cog name not exists, send all cog names.
        '''
    )
    async def _load(self, ctx: commands.Context, name: str | None = None, *_) -> None:
        cog_path = f'cogs.{name.lower()}_cog'
        await self.__load_cog(ctx, cog_path)

    @_cogs.command(
        name='reload',
        brief='Reload cog',
        description='''Only on the bot-channel.
        If cog name not exists, send all cog names.
        If cog is not loaded, send an info.
        '''
    )
    async def _reload(self, ctx: commands.Context, name: str | None = None, *_) -> None:
        if name is None:
            return await ctx.send('Gimme cog name!')

        cog_path = f'cogs.{name.lower()}_cog'

        try:
            self.__bot.unload_extension(cog_path)
            Console.cogs(f'{ctx.author.display_name} odłączył {cog_path}')
        except Exception as e:
            return await ctx.send(
                f'Cog \'{cog_path}\' not found.\n'
                f'Reason: {e}\n\n'
                'Available cogs:\n' +
                ('\n'.join(
                    path[:-7] for path in os.listdir(
                        'cogs/') if path.endswith('_cog.py')
                ))
            )

        await self.__load_cog(ctx, cog_path)


def setup(bot: commands.Bot):
    bot.add_cog(TestCog(bot))
