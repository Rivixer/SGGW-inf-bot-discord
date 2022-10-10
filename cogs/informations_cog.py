from datetime import datetime
from typing import TypeVar
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed
import nextcord

from utils.settings import update_settings, settings
from utils.checks import has_admin_role
from main import BOT_PREFIX


_T = TypeVar('_T', bound=dict[str, dict[str, str]])

_MSG_ID_JSON_NAME = 'INFO_MSG_ID'


class InformationsCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def __add_council_field(self, embed: Embed) -> None:
        try:
            with open('files/council.json', encoding='utf-8') as f:
                council: _T = json.load(f)
        except OSError as e:
            return print(e)

        users: list[str] = list()

        for user_role_name, user_data in council.items():
            user_name = user_data.get('Name')
            user_id = user_data.get('UserID')
            user = self.__bot.get_user(user_id)

            if user is not None:
                users.append(f'{user_role_name}: {user_name} ({user.mention})')
            else:
                users.append(f'{user_role_name}: {user_name}')

        embed.add_field(
            name='Trójka / Rada:',
            value='\n'.join(users),
            inline=False
        )

    def __add_info_field(self, embed: Embed, second: bool = False) -> None:
        try:
            with open(f'files/info{"2" if second else ""}.json', encoding='utf-8') as f:
                info: _T = json.load(f)
        except OSError as e:
            return print(e)

        for info_name, info_data in info.items():
            embed.add_field(
                name=f'{info_name}:',
                value=info_data,
                inline=False
            )

    def __add_link_fields(self, embed: Embed) -> None:
        try:
            with open('files/links.json', encoding='utf-8') as f:
                council: _T = json.load(f)
        except OSError as e:
            return print(e)

        for category_name, category_data in council.items():

            values: list[str] = list()
            for link_name, link_url in category_data.items():
                values.append(f'[{link_name}]({link_url})')

            embed.add_field(
                name=f'{category_name}:',
                value='\n'.join(values),
                inline=False
            )

    def __generate_embed(self, ctx: commands.Context) -> Embed:
        embed = Embed(
            title='Informacje',
            description=f'Aktualizacja: {datetime.now().strftime("%d.%m.%Y %H:%M")}',
            colour=Colour.red()
        )

        if guild_icon := ctx.guild.icon:
            embed.set_thumbnail(url=guild_icon.url)

        self.__add_council_field(embed)
        self.__add_info_field(embed)
        self.__add_link_fields(embed)
        self.__add_info_field(embed, True)

        embed.set_footer(
            text='Zalecane jest ustawienie pseudonimu z imieniem i 1. literą nazwiska.'
        )

        return embed

    @commands.group(name='info')
    @has_admin_role()
    async def _info(self, *args) -> None:
        ctx: commands.Context = args[0]
        await ctx.message.delete()

    @_info.command(name='send')
    async def _send(self, ctx: commands.Context, *_) -> None:
        embed = self.__generate_embed(ctx)
        message = await ctx.send(embed=embed)
        update_settings(_MSG_ID_JSON_NAME, message.id)

    @_info.command(name='update')
    async def _update(self, ctx: commands.Context, *_) -> None:
        message_id = settings.get(_MSG_ID_JSON_NAME)

        try:
            message = await ctx.channel.fetch_message(message_id)
        except (nextcord.NotFound, nextcord.HTTPException):
            return await ctx.send(
                f'{ctx.author.mention} Nie znaleziono wiadmomości do zaktualizowania. '
                f'Zaktualizuj settings.json lub użyj komendy \'{BOT_PREFIX}info send\'.',
                delete_after=10
            )

        embed = self.__generate_embed(ctx)
        await message.edit(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(InformationsCog(bot))
