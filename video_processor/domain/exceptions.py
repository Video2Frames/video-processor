"""Exceptions for the Video Processor Domain"""

from uuid import UUID

from .value_objects import VideoProcessingStatus


class VideoProcessorError(Exception):
    """Base exception class for Video Processor domain errors."""


class InvalidStatusTransitionError(VideoProcessorError):
    """Exception raised when an invalid status transition is attempted."""

    def __init__(
        self,
        video_id: UUID,
        current_status: VideoProcessingStatus,
        attempted_status: VideoProcessingStatus,
    ) -> None:
        self.video_id = video_id
        self.current_status = current_status
        self.attempted_status = attempted_status

        message = (
            f"Invalid status transition for video {video_id}: "
            f"{current_status.value} -> {attempted_status.value}"
        )

        super().__init__(message)


class StorageError(VideoProcessorError):
    """Exception for StorageService port errors."""


class FrameProcessingError(VideoProcessorError):
    """Exception for FrameProcessor port errors."""


class EventPublishingError(VideoProcessorError):
    """Exception for EventPublisher port errors."""


class VideoMetadataReadingError(VideoProcessorError):
    """Exception for errors that occur while reading video metadata."""


class VideoValidationError(VideoProcessorError):
    """Exception for errors that occur while validating video metadata."""


class FrameSelectionError(VideoProcessorError):
    """Exception for errors that occur while selecting frames."""


class FrameExtractionError(VideoProcessorError):
    """Exception for errors that occur while extracting frames."""


class FramePackagingError(VideoProcessorError):
    """Exception for errors that occur while packaging frames."""


class TempFileManagerError(VideoProcessorError):
    """Exception for errors that occur while managing temporary files."""
