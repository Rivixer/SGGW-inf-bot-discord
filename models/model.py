from pathlib import Path
from typing import Any
from abc import ABC
import json
import re


class Model(ABC):

    __slots__ = (
        '__data',
    )

    __data: dict[str, Any]

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

    def _load_from_settings(self) -> dict[str, Any]:
        """Loads data from <...>_settings.json in a class dictionary.

        Sets __data loaded from the file.

        Returns
        -------
        data: `dict[str, Any]` - Dictionary loaded from json file.

        Raises
        ------
        OSError
            Cannot open json file.
        TypeError
            message_id in json file is invaild.
        """

        with open(self._settings_path, encoding='utf-8') as f:
            self.__data = json.load(f)

        return self.__data

    def update_json(self, key: str, value: Any) -> None:
        """Updates json.

        If the key doesn't exist in the file, raise an error.

        Raises
        ------
        OSError
            Cannot open file.
        KeyError
            Invaild key.
        """

        if key not in self.__data.keys():
            raise KeyError(
                f'Invalid key ({key}) when updating {self._settings_path}.'
            )

        self.__data[key] = value
        with open(self._settings_path, 'w', encoding='utf-8') as f:
            json.dump(self.__data, f, ensure_ascii=True, indent=4)
