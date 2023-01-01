from dataclasses import dataclass
from datetime import datetime, time, date
from typing import Generator

from models.model import Model
from sggw_bot import SGGWBot


@dataclass
class _Event:
    description: str
    date_time: datetime
    is_all_day: bool

    @property
    def weekday(self) -> str:
        return {
            0: "poniedziałek",
            1: "wtorek",
            2: "środa",
            3: "czwartek",
            4: "piątek",
            5: "sobota",
            6: "niedziela",
        }.get(self.date_time.weekday(), '')

    @property
    def date(self) -> date:
        return self.date_time.date()

    @property
    def time(self) -> time:
        return self.date_time.time()

    @property
    def date_str(self) -> str:
        return f"{self.date.strftime('%d.%m.%Y')} ({self.weekday}):"

    @property
    def time_str(self) -> str:
        return self.time.strftime('%H:%M')

    @property
    def full_name(self) -> str:
        return f'{self.date_str} {str(self)}'

    def __str__(self) -> str:
        if self.is_all_day:
            return f'**{self.description}**'
        return f'**{self.description}** ({self.time_str})'


class CalendarModel(Model):

    def __init__(self, bot: SGGWBot) -> None:
        super().__init__(bot)
        super()._load_settings()

    @property
    def calendar_data(self) -> list[_Event]:
        calendar = super().data.get('calendar', [])
        result = []

        for event in calendar:
            description = event[0]
            if not isinstance(event[1], datetime):
                date = datetime.strptime(event[1], '%Y-%m-%d %H:%M:%S')
            else:
                date = event[1]
            is_all_day = event[2]

            result.append(_Event(description, date, is_all_day))

        return result

    @property
    def events_with_indexes(self) -> dict[int, _Event]:
        result = dict()
        for i, event in enumerate(self.calendar_data):
            result[i] = event
        return result

    def add_event_to_json(self, description: str, date_time: datetime, is_all_day: bool) -> None:
        data: list[list[str | datetime | bool]] = self.data.get('calendar', [])
        data.append([description, date_time, is_all_day])
        self.update_json('calendar', data, force=True)

    def remove_event_from_json(self, event: _Event) -> None:
        data: list[list[str | datetime | bool]] = self.data.get('calendar', [])
        data.remove(
            [event.description, str(event.date_time), event.is_all_day]
        )
        self.update_json('calendar', data, force=True)

    def get_events_in_day(self) -> Generator[tuple[str, list[str]], None, None]:
        calendar: dict[date, list[_Event]] = {}

        for event in self.calendar_data:
            try:
                calendar[event.date].append(event)
            except KeyError:
                calendar[event.date] = [event]

        calendar = {k: sorted(v, key=lambda i: i.time)
                    for k, v in calendar.items()}

        calendar_copy = calendar.copy()
        calendar = {k: calendar_copy[k] for k in sorted(calendar_copy.keys())}

        for events in calendar.values():
            yield (events[0].date_str, list(map(str, events)))
