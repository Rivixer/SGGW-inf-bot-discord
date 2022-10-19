import json
import os
from typing import Any

from utils.console import Console

_MSG_SAMPLE = {
    "MSG_ID": 'int',
    "CHANNEL_ID": 'int'
}

_SETTINGS_SAMPLE = {
    "ADMIN_ROLE_ID": 'int',
    "BOT_CHANNEL_ID": 'int',
    "GR_1_ID": 'int',
    "GR_2_ID": 'int',
    "GR_3_ID": 'int',
    "GR_4_ID": 'int',
    "GR_5_ID": 'int',
    "GUEST_ROLE_ID": 'int',
    "INFO_MSG": _MSG_SAMPLE,
    "ROLES_MSG": _MSG_SAMPLE,
    "ARCHIVE_INFO_MSG": _MSG_SAMPLE,
    "CALENDAR_MSG": _MSG_SAMPLE
}

_SETTINGS_PATH = 'settings.json'

settings: dict[str, Any]


"""
If settings.json does not exist, quit the program
and create its prototype.

If settings.json exists but nothing was filled,
quit the program.

If read failed, print exception content to the console
and quit the program.
"""


def load_settings():

    if not os.path.exists(_SETTINGS_PATH):
        with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(_SETTINGS_SAMPLE, f, ensure_ascii=True, indent=4)
        Console.critical_error(
            'File settings.json doesn\'t exist. '
            'A prototype of it has been created.'
            'Fill it up and run the program again',
            OSError()
        )

    try:
        global settings
        with open(_SETTINGS_PATH, encoding='utf-8') as f:
            settings = json.load(f)
    except Exception as e:
        Console.critical_error('Coś poszło nie tak z ładowaniem ustawień', e)

    if settings == _SETTINGS_SAMPLE:
        Console.critical_error(f'{_SETTINGS_PATH} is not filled.')


load_settings()


def update_settings(key: str, value: Any) -> None:
    """If something went wrong, print content to the console."""
    settings[key] = value

    try:
        with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            return json.dump(settings, f, ensure_ascii=True, indent=4)
    except Exception as e:
        Console.important_error(
            'Coś poszło nie tak z updateowaniem ustawień', e
        )
