from typing import Any
import json

from nextcord.interactions import Interaction
from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.ext import commands
import nextcord

from sggw_bot import SGGWBot


class EmbedCog(commands.Cog):

    __slots__ = (
        '__bot'
    )

    __bot: SGGWBot

    def __init__(self, bot: SGGWBot):
        self.__bot = bot

    @nextcord.slash_command(
        name='embed',
        description="Manage an embed.",
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _embed(self, *_) -> None:
        pass

    @_embed.subcommand(name='prototype', description="Get prototype of embed in json.")
    async def _prototype(self, interaction: Interaction) -> None:
        prototype = {
            'title': 'title',
            'description': 'description',
            'colour': 'blurple',
            'thumbnail': None,
            'footer': {
                'text': None,
                'icon_url': None
            },
            'fields': [
                {
                    'name': 'name',
                    'value': 'value',
                    'inline': False
                }
            ]
        }

        try:
            with open('prototype_json.json', 'w', encoding='utf-8') as f:
                json.dump(prototype, f, indent=4)

            file = nextcord.File('prototype_json.json')
            await interaction.response.send_message(
                file=file, ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )

    @_embed.subcommand(name='send', description="Send embed in this channel.")
    async def _send(self, interaction: Interaction, file: nextcord.Attachment, preview: bool) -> None:
        try:
            await file.save('prototype_json.json')

            with open('prototype_json.json', 'r', encoding='utf-8') as f:
                data: dict = json.load(f)

            get_colour = getattr(Colour, data.get('colour', Colour.default))

            embed = Embed(
                title=data.get('title'),
                description=data.get('description'),
                colour=get_colour()
            )

            if data.get('thumbnail'):
                embed.set_thumbnail(data.get('thumbnail'))

            field: dict[str, Any]
            for field in data.get('fields', []):
                embed.add_field(
                    name=field.get('name'),
                    value=field.get('value'),
                    inline=field.get('inline', False)
                )

            embed.set_footer(
                text=data.get('footer', {}).get('text'),
                icon_url=data.get('footer', {}).get('icon_url')
            )

            if preview:
                await interaction.response.send_message(
                    embed=embed, ephemeral=preview
                )
            else:
                await interaction.channel.send(embed=embed)  # type: ignore

        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )


def setup(bot: SGGWBot):
    bot.add_cog(EmbedCog(bot))
