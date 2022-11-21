from nextcord.embeds import Embed
from nextcord.colour import Colour

from utils.console import Console


def updates_embed() -> Embed:
    embed = Embed(
        title='AKTUALIZACJA BINGO',
        description='Poniżej najważniejsze zmiany.',
        colour=Colour.orange()
    ).add_field(
        name='PRZYŚPIESZENIE DZIAŁANIA',
        value='o ok. 80ms',
        inline=False
    ).add_field(
        name='EMBED Z KOMENDAMI',
        value='tych komend jest już tak dużo,\n'
        'że od czasu warto je sobie przypomnieć,\n'
        'wiadomość będzie automatycznie wysyłana',
        inline=False
    ).add_field(
        name='EMBED Z AKTUALIZACJAMI',
        value='czyli to co właśnie czytasz',
        inline=False
    )

    try:
        with open('bingo/version.txt') as f:
            embed.set_footer(
                text=f.readline()
            )
    except Exception as e:
        Console.error(
            "Nie udało się ustawić wersji w embedzie",
            exception=e
        )

    return embed
