"""Local storage service implementation"""

import os

from video_processor.domain.exceptions import StorageError
from video_processor.domain.ports import InputStorage
from video_processor.domain.value_objects import FileContent
from video_processor.infrastructure.config import LocalInputStorageSettings


class LocalInputStorage(InputStorage):
    """LocalInputStorage is an implementation of the InputStorage port that
    interacts with the local file system.
    """

    def __init__(self, settings: LocalInputStorageSettings):
        self._base_path = settings.BASE_PATH

    def download_file(self, source_path: str) -> FileContent:
        full_path = os.path.join(self._base_path, source_path)
        try:
            with open(full_path, "rb") as file:
                content = file.read()
        except OSError as e:
            raise StorageError(f"Failed to read file at {full_path}") from e

        return FileContent(path=full_path, content=content)
