"""Events for the Video Processor Domain"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainEvent(BaseModel):
    """Base class for domain events"""

    id: UUID = Field(
        description="Unique identifier for the event", default_factory=uuid4
    )

    occurred_at: datetime = Field(
        description="Timestamp when the event occurred",
        default_factory=lambda: datetime.now(timezone.utc),
    )

    version: int = Field(description="Version of the event", default=1)

    # Make the model immutable as events should be immutable
    model_config = ConfigDict(frozen=True)

    def get_name(self) -> str:
        """Get the name of the event class

        Returns:
            str: The name of the event class
        """
        return self.__class__.__name__


class VideoStatusEvent(DomainEvent):
    """Base class for video status change events"""

    video_id: UUID = Field(
        ..., description="Unique identifier for the processed video."
    )


class VideoProcessingStartedEvent(VideoStatusEvent):
    """Event representing that a video processing has started"""

    processing_started_at: datetime = Field(
        ...,
        description="The timestamp when the video processing started.",
    )


class VideoProcessedEvent(VideoStatusEvent):
    """Event representing that a video has been processed"""

    output_path: str = Field(
        ...,
        description="The path in the storage where the processed frames are stored.",
    )

    processed_at: datetime = Field(
        ...,
        description="The timestamp when the video was processed.",
    )


class VideoProcessingFailedEvent(VideoStatusEvent):
    """Event representing that a video processing has failed"""

    failed_at: datetime = Field(
        ...,
        description="The timestamp when the video processing failed.",
    )

    error_message: str = Field(..., description="Error message describing the failure.")
