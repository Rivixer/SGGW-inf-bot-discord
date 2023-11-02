# pylint: disable=all

import datetime as dt
import json
from pathlib import Path
from typing import Any, Generator

import pytest
from pytest import MonkeyPatch

from sggwbot.calendar import (
    CalendarController,
    CalendarEmbedModel,
    CalendarModel,
    Event,
)

from .mocks import *

TEST_JSON_PATH = Path("test_calendar.json")


@pytest.fixture
def model(monkeypatch: MonkeyPatch) -> Generator[CalendarModel, None, None]:
    open(TEST_JSON_PATH, "w", encoding="utf-8").write("{}")
    monkeypatch.setattr(CalendarModel, "_settings_path", TEST_JSON_PATH)
    yield CalendarModel()
    TEST_JSON_PATH.unlink()


@pytest.fixture
def ctrl(model: CalendarModel) -> CalendarController:
    embed_model = CalendarEmbedModel(model, BotMock(GuildMock()))  # type: ignore
    return CalendarController(model, embed_model)


@pytest.fixture
def datetime() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def _load_data_from_json() -> dict[str, Any]:
    with open(TEST_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_add_event_to_json(model: CalendarModel, datetime: dt.datetime) -> None:
    model.add_event_to_json("test", datetime, "", "", False)
    assert model._events_data == [("test", str(datetime), "", "", False)]
    file_data = _load_data_from_json()
    assert file_data.get("events") == [["test", str(datetime), "", "", False]]


def test_add_event_by_command(ctrl: CalendarController) -> None:
    ctrl.add_event("test", "1.11:2023", "11-22", "prefix", "location")
    event = ("test", str(dt.datetime(2023, 11, 1, 11, 22)), "prefix", "location", False)
    assert ctrl.model._events_data == [event]


def test_read_event_from_json(model: CalendarModel, datetime: dt.datetime) -> None:
    data = {"events": [["test", str(datetime), "prefix", "location", False]]}
    with open(TEST_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    model._load_settings()

    assert model.calendar_data == [Event("test", datetime, "prefix", "location", False)]


def test_remove_event_from_json(model: CalendarModel, datetime: dt.datetime) -> None:
    model.add_event_to_json("test", datetime, "prefix", "location", False)
    model.remove_event_from_json(model.calendar_data[0])
    assert model._events_data == []
    assert model.calendar_data == []
    file_data = _load_data_from_json()
    assert file_data.get("events") == []


def test_is_all_day_event(model: CalendarModel, datetime: dt.datetime) -> None:
    model.add_event_to_json("test", datetime, "", "", True)
    event = model.calendar_data[0]
    assert event.is_all_day is True
    assert event.date.strftime("%H:%M:%S:%f") == "00:00:00:000000"


def test_sort_calendar_data_with_other_time(
    model: CalendarModel, datetime: dt.datetime
) -> None:
    model.add_event_to_json("test1", datetime, "", "", False)
    later = datetime + dt.timedelta(minutes=10)
    model.add_event_to_json("test2", later, "", "", False)
    earlier = datetime - dt.timedelta(minutes=10)
    model.add_event_to_json("test3", earlier, "", "", False)

    expected = ["test3", "test1", "test2"]
    assert [i.description for i in model.calendar_data] == expected


def test_sort_calendar_data_with_other_day(
    model: CalendarModel, datetime: dt.datetime
) -> None:
    event1 = model.add_event_to_json("test1", datetime, "", "", False)
    earlier = datetime - dt.timedelta(days=10)
    event2 = model.add_event_to_json("test2", earlier, "", "", False)
    later = datetime + dt.timedelta(days=10)
    event3 = model.add_event_to_json("test3", later, "", "", False)
    assert model.calendar_data == [event2, event1, event3]


def test_sort_calendar_data_all_day_first(
    model: CalendarModel, datetime: dt.datetime
) -> None:
    event1 = model.add_event_to_json("test1", datetime, "", "", True)
    event2 = model.add_event_to_json("test2", datetime, "", "", False)
    event3 = model.add_event_to_json("test3", datetime, "", "", True)
    assert model.calendar_data == [event1, event3, event2]


def test_get_grouped_events(model: CalendarModel, datetime: dt.datetime) -> None:
    next_day = datetime + dt.timedelta(days=1)
    event1 = model.add_event_to_json("test1", datetime, "", "", True)
    event2 = model.add_event_to_json("test2", next_day, "", "", False)
    event3 = model.add_event_to_json("test3", datetime, "", "", False)
    event4 = model.add_event_to_json("test4", next_day, "", "", False)
    expected = [
        (datetime.date(), [event1, event3]),
        (next_day.date(), [event2, event4]),
    ]
    assert list(model.get_grouped_events()) == expected


def test_convert_input_to_datetime(ctrl: CalendarController) -> None:
    expected = dt.datetime(2023, 12, 1, 12, 34)
    assert ctrl._convert_input_to_datetime("01.12.2023", "12.34") == expected
    assert ctrl._convert_input_to_datetime("1/12/2023", "12/34") == expected
    assert ctrl._convert_input_to_datetime("1:12:2023", "12:34") == expected
    assert ctrl._convert_input_to_datetime("1-12-2023", "12-34") == expected
    no_time = dt.datetime(2023, 12, 1, 0, 0)
    assert ctrl._convert_input_to_datetime("1-12-2023", None) == no_time
    with pytest.raises(ValueError):
        ctrl._convert_input_to_datetime("29-02-2023", "12-34")


def test_expired_events_and_remove_them(
    ctrl: CalendarController, model: CalendarModel, datetime: dt.datetime
) -> None:
    past_datetime = datetime - dt.timedelta(minutes=10)
    future_datetime = datetime + dt.timedelta(minutes=10)
    event1 = model.add_event_to_json("test1", past_datetime, "", "", False)
    assert event1.is_expired() is True
    event2 = model.add_event_to_json("test2", future_datetime, "", "", False)
    assert event2.is_expired() is False
    event3 = model.add_event_to_json("test3", past_datetime, "", "", False)
    assert event3.is_expired() is True
    event4 = model.add_event_to_json("test4", past_datetime, "", "", True)
    assert event4.is_expired() is False
    removed = ctrl.remove_expired_events()
    assert removed == [event1, event3]
    assert model.calendar_data == [event4, event2]


def test_event_full_name_with_time() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 9, 34), "", "", False)
    assert event.full_name == "**test** (9:34)"


def test_event_full_name_only_name() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 0, 0), "", "", True)
    assert event.full_name == "**test**"


def test_event_full_name_with_time_and_not_all_day() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 0, 0), "", "", False)
    assert event.full_name == "**test** (0:00)"


def test_event_full_name_with_prefix() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 0, 0), "prefix", "", True)
    assert event.full_name == "[prefix] **test**"


def test_event_full_name_with_location() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 0, 0), "", "location", True)
    assert event.full_name == "**test** [location]"


def test_event_full_name_with_prefix_and_location() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 0, 0), "prefix", "location", True)
    assert event.full_name == "[prefix] **test** [location]"


def test_event_full_name_with_prefix_and_location_and_time() -> None:
    event = Event("test", dt.datetime(2023, 1, 23, 14, 5), "prefix", "location", False)
    assert event.full_name == "[prefix] **test** [location] (14:05)"


def test_event_wrong_date(datetime: dt.datetime) -> None:
    with pytest.raises(ValueError):
        Event("test", datetime.replace(hour=1), "", "", True)


def test_event_weekday() -> None:
    monday = dt.datetime(2023, 2, 27)
    event = Event("test1", monday, "", "", False)
    assert event.weekday == "poniedziałek"


def test_events_with_indexes(
    ctrl: CalendarController, model: CalendarModel, datetime: dt.datetime
) -> None:
    event1 = model.add_event_to_json("test1", datetime, "prefix", "", True)
    event2 = model.add_event_to_json("test2", datetime, "", "location", True)
    assert ctrl.events_with_indexes == f"1. {event1.full_name}\n2. {event2.full_name}"


def test_remove_event_with_index(
    ctrl: CalendarController, model: CalendarModel, datetime: dt.datetime
) -> None:
    with pytest.raises(IndexError):
        ctrl.remove_event_at_index(0)
    model.add_event_to_json("test1", datetime, "", "", True)
    with pytest.raises(IndexError):
        ctrl.remove_event_at_index(0)
    with pytest.raises(IndexError):
        ctrl.remove_event_at_index(2)
    ctrl.remove_event_at_index(1)
    assert model.calendar_data == []
