"""Value objects for the Video Processor Domain"""

from enum import Enum, unique

from pydantic import BaseModel, ConfigDict


@unique
class VideoProcessingStatus(str, Enum):
    """Enumeration of possible statuses for processed videos."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileContent(BaseModel):
    """Value object representing file content and its path."""

    model_config = ConfigDict(frozen=True)

    path: str
    content: bytes


class VideoMetadata(BaseModel):
    """Value object representing metadata of a video."""

    model_config = ConfigDict(frozen=True)

    path: str
    duration_seconds: float
    frame_count: int
    fps: float
    size_in_bytes: int


class FrameSelection(BaseModel):
    """Value object representing the selection of frames to be extracted from a
    video."""

    model_config = ConfigDict(frozen=True)

    indexes: list[int]


class RawFrame(BaseModel):
    """Value object representing a raw frame extracted from a video."""

    model_config = ConfigDict(frozen=True)

    index: int
    filename: str
    content: bytes


class TempFile(BaseModel):
    """Value object representing a temporary file."""

    model_config = ConfigDict(frozen=True)

    path: str
