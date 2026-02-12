import os
import tempfile

from video_processor.domain.exceptions import TempFileManagerError
from video_processor.domain.ports import TempFileManager
from video_processor.domain.value_objects import TempFile


class NamedTempFileManager(TempFileManager):
    """An implementation of the TempFileManager port that uses named temporary files"""

    def create(self, content: bytes, suffix: str = "") -> TempFile:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                return TempFile(path=temp_file.name)
        except (IOError, OSError) as e:
            raise TempFileManagerError(f"Failed to create temporary file: {e}") from e

    def delete(self, temp_file: TempFile) -> None:
        try:
            os.remove(temp_file.path)
        except (IOError, OSError) as e:
            raise TempFileManagerError(f"Failed to delete temporary file: {e}") from e

    def get_size(self, temp_file: TempFile) -> int:
        try:
            return os.path.getsize(temp_file.path)
        except (IOError, OSError) as e:
            raise TempFileManagerError(f"Failed to get file size: {e}") from e
