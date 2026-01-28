"""Local storage service implementation"""

import os

from video_processor.domain.exceptions import StorageError
from video_processor.domain.ports import OutputStorage
from video_processor.domain.value_objects import FileContent
from video_processor.infrastructure.config import LocalOutputStorageSettings


class LocalOutputStorage(OutputStorage):
    """LocalOutputStorage is an implementation of the OutputStorage port that
    interacts with the local file system.
    """

    def __init__(self, settings: LocalOutputStorageSettings):
        self._base_path = settings.BASE_PATH

    def upload_file(self, file_content: FileContent, destination_path: str) -> None:
        full_path = os.path.join(self._base_path, destination_path)
        try:
            with open(full_path, "wb") as file:
                file.write(file_content.content)
        except OSError as e:
            raise StorageError(f"Failed to write file at {full_path}") from e
