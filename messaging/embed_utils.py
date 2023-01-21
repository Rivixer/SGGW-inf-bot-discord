from typing import Any
import json

from nextcord.colour import Colour
from nextcord.embeds import Embed
import nextcord

from utils.attachment import AttachmentUtils


class EmbedUtils:

    @staticmethod
    def embed_prototype() -> nextcord.File:
        """Returns `nextcord.File` with prototype_embed.json."""

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

        with open('prototype_json.json', 'w', encoding='utf-8') as f:
            json.dump(prototype, f, indent=4)

        return nextcord.File('prototype_json.json')

    @staticmethod
    async def convert_attachment_to_embed(file: nextcord.Attachment) -> nextcord.Embed:
        """Converts `nextcord.Attachment` to `nextcord.Embed`.

        Temporarily saves the file in `'temp/attachment_url'`.
        """

        attachment_utils = AttachmentUtils(file)

        try:
            path = await attachment_utils.save_temporarily()

            with open(path, 'r', encoding='utf-8') as f:
                data: dict = json.load(f)

            try:
                return nextcord.Embed.from_dict(data)
            except:
                pass

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

            return embed
        finally:
            attachment_utils.delete()

    @staticmethod
    def get_embed_from_message(message: nextcord.Message) -> Embed | None:
        try:
            return message.embeds[0]
        except:
            return None
