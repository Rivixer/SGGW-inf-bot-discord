from abc import ABC
from datetime import datetime
import os
import shutil


class UpdateEmbed(ABC):

    @staticmethod
    def override_file(filename: str) -> None:
        """Override the file in `files/[filename].json
        with the file from `files/preview/[filename].json.
        Move old file to old_files with datetime in name.
        """

        os.replace(
            f'files/{filename}.json',
            f'old_files/{filename}-{datetime.now().strftime("%d-%m-%y_%H-%M-%S-%f")}.json'.replace(' ', '_'),
        )

        shutil.copy(
            f'files/preview/{filename}.json',
            f'files/{filename}.json'
        )
