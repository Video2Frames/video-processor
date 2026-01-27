"""Local storage service implementation"""

import os

from video_processor.domain.exceptions import StorageError
from video_processor.domain.ports import InputStorage
from video_processor.domain.value_objects import FileContent


class LocalInputStorage(InputStorage):
    """LocalInputStorage is an implementation of the InputStorage port that
    interacts with the local file system.
    """

    def __init__(self, base_path: str):
        self._base_path = base_path

    def download_file(self, source_path: str) -> FileContent:
        full_path = os.path.join(self._base_path, source_path)

        try:
            with open(full_path, "rb") as file:
                content = file.read()
        except OSError as e:
            raise StorageError(f"Failed to read file at {full_path}") from e

        return FileContent(path=full_path, content=content)
