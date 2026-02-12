import zipfile
from typing import Iterator

from video_processor.domain.exceptions import FramePackagingError
from video_processor.domain.ports import FramePackager, TempFileManager
from video_processor.domain.value_objects import FileContent, RawFrame, TempFile


class ZIPFramePackager(FramePackager):
    """The FramePackager port defines the interface for packaging extracted frames into
    a ZIP file."""

    def __init__(self, temp_file_manager: TempFileManager):
        self._temp_file_manager = temp_file_manager

    def package(self, frames: Iterator[RawFrame]) -> FileContent:
        temp_file: TempFile | None = None
        try:
            temp_file = self._temp_file_manager.create(b"", suffix=".zip")
            with zipfile.ZipFile(temp_file.path, mode="w") as zip_file:
                for frame in frames:
                    zip_file.writestr(frame.filename, frame.content)

            with open(temp_file.path, "rb") as f:
                return FileContent(path=temp_file.path, content=f.read())
        except (zipfile.BadZipFile, zipfile.LargeZipFile, IOError, OSError) as e:
            raise FramePackagingError(
                f"An error occurred during frame packaging: {e}"
            ) from e
        finally:
            if temp_file is not None:
                self._temp_file_manager.delete(temp_file)
