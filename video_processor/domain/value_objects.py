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

    file_path: str
    file_content: bytes
