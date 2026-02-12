from video_processor.domain.exceptions import VideoMetadataReadingError
from video_processor.domain.ports import VideoMetadata
from video_processor.infrastructure.config import VideoValidatorsSettings


class VideoSizeValidator:
    """A validator for validating the size of a video file"""

    def __init__(self, settings: VideoValidatorsSettings):
        self.max_size_in_bytes = settings.MAX_SIZE_IN_BYTES

    def validate(self, video_metadata: VideoMetadata) -> None:
        """Validate the size of the video file.

        Args:
            video_metadata (VideoMetadata): The metadata of the video file to be
                validated.

        Raises:
            VideoMetadataReadingError: If the size of the video file exceeds the
                maximum allowed size.
        """
        if video_metadata.size_in_bytes > self.max_size_in_bytes:
            raise VideoMetadataReadingError(
                f"Video file size {video_metadata.size_in_bytes} bytes exceeds the "
                f"maximum allowed size of {self.max_size_in_bytes} bytes."
            )
