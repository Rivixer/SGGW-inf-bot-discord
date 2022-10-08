from datetime import datetime
from typing import TypeVar
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed

from utils.checks import has_admin_role

T = TypeVar('T', bound=dict[str, dict[str, str]])


class InformationsCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def __add_council_field(self, embed: Embed) -> None:
        try:
            with open('files/council.json', encoding='utf-8') as f:
                council: T = json.load(f)
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

    def __add_info_field(self, embed: Embed) -> None:
        try:
            with open('files/info.json', encoding='utf-8') as f:
                info: T = json.load(f)
        except OSError as e:
            return print(e)

        for info_name, info_data in info.items():
            embed.add_field(
                name=f'{info_name}:',
                value='\n'.join(f'{k}: {v}' for k, v in info_data.items()),
                inline=False
            )

    def __add_link_fields(self, embed: Embed) -> None:
        try:
            with open('files/links.json', encoding='utf-8') as f:
                council: T = json.load(f)
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

    @has_admin_role()
    @commands.command(name='send_info')
    async def _send_info(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

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

        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(InformationsCog(bot))
