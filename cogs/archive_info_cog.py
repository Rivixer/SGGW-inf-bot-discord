from typing import TypeVar
import matplotlib
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed
import nextcord

from utils.settings import update_settings, settings
from utils.checks import has_admin_role
from main import BOT_PREFIX

T = TypeVar('T', bound=dict[str, dict[str, str | dict[str, str]]])

_MSG_ID_JSON_NAME = 'ARCHIVE_INFO_MSG_ID'


class ArchiveInfoCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def __generate_embeds(self) -> list[Embed]:
        try:
            with open('files/archive_links.json', encoding='utf-8') as f:
                data: T = json.load(f)
        except OSError as e:
            print(e)
            return []

        embeds: list[embed] = list()

        for semestr_name, semestr_data in data.items():
            colour_hex = semestr_data.get('Colour')

            if colour_hex is not None:
                colour_rgb = matplotlib.colors.to_rgb(colour_hex)
                colour = Colour.from_rgb(
                    *map(lambda i: int(i*255), colour_rgb)
                )
            else:
                colour = Colour.light_gray()

            embed = Embed(
                title=semestr_name,
                colour=colour
            )

            for category_name, category_data in semestr_data.items():
                if category_name in ('Footer', 'Colour'):
                    continue

                values: list[str] = []
                for link_name, link_url in category_data.items():
                    values.append(f'[{link_name}]({link_url})')

                embed.add_field(
                    name=f'{category_name}:',
                    value='\n'.join(values),
                    inline=False
                )

            if footer := semestr_data.get('Footer'):
                embed.set_footer(text=footer)

            embeds.append(embed)

        return embeds

    @commands.group(name='archive')
    @has_admin_role()
    async def _archive(self, *args) -> None:
        ctx: commands.Context = args[0]
        await ctx.message.delete()

    @_archive.command(name='send')
    async def _send(self, ctx: commands.Context, *_) -> None:
        embeds = self.__generate_embeds()
        message = await ctx.send(embeds=embeds)
        update_settings(_MSG_ID_JSON_NAME, message.id)

    @_archive.command(name='update')
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

        embeds = self.__generate_embeds()
        await message.edit(embeds=embeds)


def setup(bot: commands.Bot):
    bot.add_cog(ArchiveInfoCog(bot))
