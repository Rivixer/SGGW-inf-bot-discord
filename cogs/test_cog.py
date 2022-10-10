import os
from nextcord.ext import commands

from utils.checks import has_admin_role, is_bot_channel
from utils.settings import load_settings


class TestCog(commands.Cog):
    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print('Bot załadowany!')

    @has_admin_role()
    @is_bot_channel()
    @commands.command(name='print')
    async def _print(self, _, *args) -> None:
        print('\n'.join(args))

    @has_admin_role()
    @is_bot_channel()
    @commands.command(name='reload_settings')
    async def _print(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        try:
            load_settings()
        except Exception as e:
            await ctx.send(f'{ctx.author.mention} {e}', delete_after=5)
        else:
            await ctx.send(f'Przeładowano ustawienia.', delete_after=3)

    @has_admin_role()
    @is_bot_channel()
    @commands.group(name='cogs')
    async def _cogs(self, *args) -> None:
        ctx: commands.Context = args[0]
        await ctx.message.delete()

    async def __load_cog(self, ctx: commands.Context, cog_path: str) -> None:
        try:
            self.__bot.load_extension(cog_path)
        except Exception as e:
            return await ctx.send(
                f'Cog \'{cog_path}\' cannot be loaded.\n'
                f'Reason: {e}',
                delete_after=5
            )

        await ctx.send(f'Pomyślnie przeładowano/załadowano {cog_path}', delete_after=5)
        print(
            f'{ctx.author.display_name} podłączył {cog_path}'
        )

    @_cogs.command(name='load')
    async def _load(self, ctx: commands.Context, name: str | None = None, *_) -> None:
        cog_path = f'cogs.{name.lower()}_cog'
        await self.__load_cog(ctx, cog_path)

    @_cogs.command(name='reload')
    async def _reload(self, ctx: commands.Context, name: str | None = None, *_) -> None:
        if name is None:
            return await ctx.send('Gimme cog name!', delete_after=5)

        cog_path = f'cogs.{name.lower()}_cog'

        try:
            self.__bot.unload_extension(cog_path)
            print(
                f'{ctx.author.display_name} odłączył {cog_path}'
            )
        except Exception as e:
            return await ctx.send(
                f'Cog \'{cog_path}\' not found.\n'
                f'Reason: {e}\n\n'
                'Available cogs:\n' +
                ('\n'.join(
                    path for path in os.listdir(
                        'cogs/') if path.endswith('_cog.py')
                )),
                delete_after=15
            )

        await self.__load_cog(ctx, cog_path)


def setup(bot: commands.Bot):
    bot.add_cog(TestCog(bot))
