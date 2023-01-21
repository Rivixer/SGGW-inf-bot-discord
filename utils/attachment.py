from dataclasses import dataclass, field
from pathlib import Path

from nextcord.message import Attachment
from nextcord.file import File

from utils.console import Console


@dataclass
class AttachmentUtils:

    __attachment: Attachment
    __file_path: Path = field(init=False)

    def __post_init__(self) -> None:
        try:
            url = self.__attachment.url.split('discordapp.com')[1]
            url = url.replace('\\', '_').replace('/', '_')
        except Exception as e:
            url = 'temp'
            Console.warn(
                'Ścieżka do tymczasowego zapisu pliku '
                f'`{self.__attachment.url}` to `temp/temp`.\n'
                f'Powód: {e}'
            )

        self.__file_path = self.__temp_path / url

    @property
    def __temp_path(self) -> Path:
        path = Path('temp/')
        if not path.exists():
            path.mkdir()
        return path

    async def save_temporarily(self) -> Path:
        """Saves the file in `temp/<attachment_url>`.

        If attachment_url is weird, saves the file in `temp/temp`

        Returns `Path` where the file is stored.
        """

        await self.__attachment.save(self.__file_path)
        return self.__file_path

    def delete(self) -> None:
        """Deletes the file stored with `save_temporarily` function.

        If something went wrong, function does nothing.
        """

        self.__file_path.unlink(True)
