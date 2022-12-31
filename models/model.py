from datetime import datetime
from pathlib import Path
from typing import Any
from abc import ABC
import shutil
import json
import re

from sggw_bot import SGGWBot


class Model(ABC):

    __slots__ = (
        '__data',
        '_bot'
    )

    __data: dict[str, Any]
    _bot: SGGWBot

    def __init__(self, bot: SGGWBot) -> None:
        self._bot = bot

    @property
    def _settings_path(self) -> Path:
        """Returns settings filename."""

        filename = re.sub(
            '(?<!^)(?=[A-Z])', '_',
            self.__class__.__name__[:-5]
        ).lower() + '_settings'

        module = self.__class__.__module__.replace('.', '\\')
        return Path(module).parent / f'{filename}.json'

    @property
    def data(self) -> dict[str, Any]:
        """Returns data loaded from settings.json"""
        return self.__data

    @property
    def bot(self) -> SGGWBot:
        return self._bot

    def _load_settings(self, *, create_if_not_exists: bool = True) -> dict[str, Any]:
        """Loads data from <...>_settings.json in a class dictionary.

        Sets __data loaded from the file.

        If create_if_not_exists is True, creates file if it doesn't exist.

        Returns
        -------
        data: `dict[str, Any]` - Dictionary loaded from json file.

        Raises
        ------
        OSError
            Cannot open json file.
        """

        if create_if_not_exists and not self._settings_path.exists():
            with open(self._settings_path, 'w') as f:
                f.write('{}')

        with open(self._settings_path, encoding='utf-8') as f:
            self.__data = json.load(f)

        return self.__data

    def reload_settings(self) -> dict[str, Any]:
        """Reload data from <...>_settings.json in a class dictionary.

        Sets __data loaded from the file.

        Returns
        -------
        data: `dict[str, Any]` - Dictionary loaded from json file.

        Raises
        ------
        OSError
            Cannot open json file.
        """

        with open(self._settings_path, encoding='utf-8') as f:
            self.__data = json.load(f)

        return self.__data

    def update_json(self, key: str, value: Any, *, force: bool = False) -> None:
        """Updates json.

        If the key doesn't exist in the file and `force` is False, raise an error.

        Moves the old json file to `old_settings/`.
        If the folder does not exist, creates it.

        Raises
        ------
        OSError
            Cannot open file.
        KeyError
            Invaild key.
        """

        if not force and key not in self.__data.keys():
            raise KeyError(
                f'Invalid key ({key}) when updating {self._settings_path}.'
            )

        old_folder = Path('old_settings/')
        if not old_folder.exists():
            old_folder.mkdir()

        now = datetime.now().strftime('%d%m%Y-%H%M%S')
        shutil.copy(
            self._settings_path,
            old_folder / f'{self.__class__.__name__}-{now}'
        )

        self.__data[key] = value
        with open(self._settings_path, 'w', encoding='utf-8') as f:
            json.dump(self.__data, f, ensure_ascii=True, indent=4, default=str)
