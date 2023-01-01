from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from models.embed_model import EmbedModel

from .calendar_model import CalendarModel


class CalendarEmbed(EmbedModel):

    _model: CalendarModel

    def generate_embed(self) -> Embed:
        embed = super().generate_embed()

        for day, events in self._model.get_events_in_day():
            embed.add_field(
                name=day,
                value='\n'.join(events),
                inline=False
            )

        return embed

    @property
    def reactions(self) -> list[Emoji | str]:
        return []
