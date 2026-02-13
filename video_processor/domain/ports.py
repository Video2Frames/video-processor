"""Ports for the Video Processor Domain"""

from abc import ABC, abstractmethod
from typing import Iterator, TypeVar

from .events import DomainEvent
from .value_objects import (
    FileContent,
    FrameSelection,
    RawFrame,
    TempFile,
    VideoMetadata,
)

DomainEventT = TypeVar("DomainEventT", bound=DomainEvent)


class EventPublisher(ABC):
    """The EventPublisher port defines the interface for publishing domain
    events."""

    @abstractmethod
    def publish(self, event: DomainEventT) -> None:
        """Publish a domain event.

        Args:
            event (DomainEventT): The domain event to be published.

        Raises:
            EventPublishingError: If an error occurs during event publishing.
        """


class InputStorage(ABC):
    """The storage port to interacting with the input storage system"""

    @abstractmethod
    def download_file(self, source_path: str) -> FileContent:
        """Download a file from the storage system.

        Args:
            source_path (str): The source path in the storage system.

        Returns:
            FileContent: The file to be downloaded.

        Raises:
            StorageError: If an error occurs during file download.
        """


class OutputStorage(ABC):
    """The storage port to interacting with the output storage system"""

    @abstractmethod
    def upload_file(self, file_content: FileContent, destination_path: str) -> None:
        """Upload a file to the storage system.

        Args:
            file_content (FileContent): The file content to be uploaded.
            destination_path (str): The destination path in the storage system.

        Raises:
            StorageError: If an error occurs during file upload.
        """


class VideoMetadataReader(ABC):
    """The VideoMetadataReader port defines the interface for reading metadata from
    video files."""

    @abstractmethod
    def read(self, temp_file: TempFile) -> VideoMetadata:
        """Read metadata from the given video file.

        Args:
            temp_file (TempFile): The temporary file containing the video.


        Returns:
            VideoMetadata: The metadata of the video.


        Raises:
            VideoMetadataReadingError: If an error occurs during video metadata reading.
        """


class VideoValidator(ABC):
    """The VideoValidator port defines the interface for validating video
    file metadata."""

    @abstractmethod
    def validate(self, metadata: VideoMetadata) -> None:
        """Validate the given video file metadata.

        Args:
            metadata (VideoMetadata): The metadata of the video file.

        Raises:
            VideoValidationError: If the video file metadata is invalid.
        """


class FrameSelector(ABC):
    """The FrameSelector port defines the interface for selecting frames to be
    extracted from a video."""

    @abstractmethod
    def select(self, metadata: VideoMetadata) -> FrameSelection:
        """Select frames to be extracted from the video based on its metadata.

        Args:
            metadata (VideoMetadata): The metadata of the video file.

        Returns:
            FrameSelection: The selection of frames to be extracted.

        Raises:
            FrameSelectionError: If an error occurs during frame selection.
        """


class FrameExtractor(ABC):
    """The FrameExtractor port defines the interface for extracting frames
    from a video."""

    @abstractmethod
    def extract(
        self, temp_file: TempFile, frame_selection: FrameSelection
    ) -> Iterator[RawFrame]:
        """Extract frames from the given video file based on the specified
        frame selection.

        Args:
            temp_file (TempFile): The temporary file containing the video.
            frame_selection (FrameSelection): The selection of frames to be extracted.

        Returns:
            Iterator[RawFrame]: An iterator of raw frames extracted from the video.

        Raises:
            FrameExtractionError: If an error occurs during frame extraction.
        """


class FramePackager(ABC):
    """The FramePackager port defines the interface for packaging extracted frames into
    a ZIP file."""

    @abstractmethod
    def package(self, frames: Iterator[RawFrame]) -> FileContent:
        """Package the given frames into a ZIP file.

        Args:
            frames (Iterator[RawFrame]): An iterator of raw frames to be packaged.

        Returns:
            FileContent: The content and path of the resulting ZIP file.

        Raises:
            FramePackagingError: If an error occurs during frame packaging.
        """


class TempFileManager(ABC):
    """The TempFileManager port defines the interface for managing temporary files."""

    @abstractmethod
    def create(self, content: bytes, suffix: str = "") -> TempFile:
        """Create a temporary file with the given content.

        Args:
            content (bytes): The content to be written to the temporary file.
            suffix (str, optional): The suffix for the temporary file. Defaults to "".

        Returns:
            TempFile: The created temporary file.

        Raises:
            TempFileManagerError: If an error occurs during temporary file creation.
        """

    @abstractmethod
    def delete(self, temp_file: TempFile) -> None:
        """Delete the specified temporary file.

        Args:
            temp_file (TempFile): The temporary file to be deleted.

        Raises:
            TempFileManagerError: If an error occurs during temporary file deletion.
        """

    @abstractmethod
    def get_size(self, temp_file: TempFile) -> int:
        """Get the size of the specified temporary file.

        Args:
            temp_file (TempFile): The temporary file for which to get the size.

        Returns:
            int: The size of the temporary file in bytes.

        Raises:
            TempFileManagerError: If an error occurs while getting the file size.
        """
