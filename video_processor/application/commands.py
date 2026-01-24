"""Commands for the Video Processor Application."""

from uuid import UUID

from pydantic import BaseModel, Field


class ProcessVideoCommand(BaseModel):
    """Command to process a video"""

    video_id: UUID = Field(
        ...,
        description="Unique identifier for the processed video.",
    )

    upload_path: str = Field(
        ...,
        description="The path in the storage where the video is uploaded.",
    )
