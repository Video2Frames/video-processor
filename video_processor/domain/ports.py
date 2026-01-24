"""Ports for the Video Processor Domain"""

from abc import ABC, abstractmethod
from typing import TypeVar

from .events import DomainEvent
from .value_objects import FileContent

DomainEventT = TypeVar("DomainEventT", bound=DomainEvent)


class FrameProcessor(ABC):
    """The FrameProcessor port defines the interface for processing videos into
    frames."""

    @abstractmethod
    async def process_video(self, video_content: FileContent) -> FileContent:
        """Extract frames from the given video file and return information about the
        resulting ZIP file.

        Args:
            video_content (FileContent): The content of the video file.

        Returns:
            FileContent: The content and path of the resulting ZIP file.

        Raises:
            FrameProcessingError: If an error occurs during frame extraction.
        """


class EventPublisher(ABC):
    """The EventPublisher port defines the interface for publishing domain
    events."""

    @abstractmethod
    async def publish(self, event: DomainEventT) -> None:
        """Publish a domain event.

        Args:
            event (DomainEventT): The domain event to be published.

        Raises:
            EventPublishingError: If an error occurs during event publishing.
        """


class StorageService(ABC):
    """The StorageService port defines the interface for interacting with the
    storage system."""

    @abstractmethod
    async def download_file(self, source_path: str) -> FileContent:
        """Download a file from the storage system.

        Args:
            source_path (str): The source path in the storage system.

        Returns:
            FileContent: The file to be downloaded.

        Raises:
            StorageError: If an error occurs during file download.
        """

    @abstractmethod
    async def upload_file(
        self, file_content: FileContent, destination_path: str
    ) -> None:
        """Upload a file to the storage system.

        Args:
            file_content (FileContent): The file content to be uploaded.
            destination_path (str): The destination path in the storage system.

        Raises:
            StorageError: If an error occurs during file upload.
        """
