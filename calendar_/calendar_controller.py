from datetime import datetime

from nextcord.interactions import Interaction

from models.embed_controller import EmbedController
from models.controller import Controller
from sggw_bot import SGGWBot

from .calendar_model import CalendarModel
from .calendar_embed import CalendarEmbed


class CalendarController(Controller, EmbedController):

    _model: CalendarModel
    _embed_model: CalendarEmbed

    def __init__(self, bot: SGGWBot) -> None:
        model = CalendarModel(bot)
        embed_model = CalendarEmbed(model)

        Controller.__init__(self, model)
        EmbedController.__init__(self, embed_model)

    def __convert_input_to_datetime(self, date: str, time: str | None) -> datetime:
        if time is None:
            time = '00.00'

        date = date.replace(':', '.').replace('-', '.').replace('/', '.')
        time = time.replace(':', '.').replace('-', '.').replace('/', '.')

        return datetime.strptime(f'{date} {time}', '%d.%m.%Y %H.%M')

    @EmbedController._with_update(
        'Dodawanie nowego wydarzenia...',
        reload_settings_before=True,
        reload_settings_after=True
    )
    async def add_event(
        self,
        interaction: Interaction,
        text: str,
        _date: str,
        _time: str | None
    ) -> None:

        date = self.__convert_input_to_datetime(_date, _time)
        is_all_day = _time is None
        self._model.add_event_to_json(text, date, is_all_day)

    @EmbedController._with_update(
        'Usuwanie wydarzenia...',
        reload_settings_before=True,
        reload_settings_after=True
    )
    async def remove_event(
        self,
        interaction: Interaction,
        index: int
    ) -> None:
        event_to_remove = self._model.events_with_indexes[index]
        self._model.remove_event_from_json(event_to_remove)

    def get_events_with_indexes(self) -> dict[int, str]:
        return {k: v.full_name for k, v in self._model.events_with_indexes.items()}

    async def remove_deprecated_events(self) -> None:
        """|coro|

        Removes events from json that are deprecated.

        Reloads settings and updates embed.
        """

        self._model.reload_settings()
        for event in self._model.calendar_data:
            if event.date < datetime.now().date():
                self._model.remove_event_from_json(event)
        self._model.reload_settings()
        await self._update_embed()
