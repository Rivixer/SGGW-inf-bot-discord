from typing import TypeVar
import matplotlib
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed

from utils.checks import has_admin_role

T = TypeVar('T', bound=dict[str, dict[str, str | dict[str, str]]])


class ArchiveInfoCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def generate_embeds(self) -> list[Embed]:
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

    @ has_admin_role()
    @ commands.command(name='send_archive_info')
    async def _send_archive_info(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        embeds = self.generate_embeds()
        await ctx.send(embeds=embeds)


def setup(bot: commands.Bot):
    bot.add_cog(ArchiveInfoCog(bot))
