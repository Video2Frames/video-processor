import cv2

from video_processor.domain.exceptions import (
    TempFileManagerError,
    VideoMetadataReadingError,
)
from video_processor.domain.ports import TempFileManager, VideoMetadataReader
from video_processor.domain.value_objects import TempFile, VideoMetadata


class OpenCVVideoMetadataReader(VideoMetadataReader):
    """An implementation of the VideoMetadataReader port that uses OpenCV to read video
    metadata"""

    def __init__(self, temp_file_manager: TempFileManager):
        self._temp_file_manager = temp_file_manager

    def read(self, temp_file: TempFile) -> VideoMetadata:
        """Read metadata from the given video file.

        Args:
            temp_file (TempFile): The temporary file containing the video.

        Returns:
            VideoMetadata: The metadata of the video.

        Raises:
            VideoMetadataReadingError: If an error occurs during video metadata reading.
        """

        try:
            capture = cv2.VideoCapture(temp_file.path)
            if not capture.isOpened():
                raise VideoMetadataReadingError(
                    "Failed to open video file for metadata reading."
                )

            frames_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = capture.get(cv2.CAP_PROP_FPS)
            duration_seconds = capture.get(cv2.CAP_PROP_FRAME_COUNT) / capture.get(
                cv2.CAP_PROP_FPS
            )

            return VideoMetadata(
                path=temp_file.path,
                duration_seconds=duration_seconds,
                frame_count=frames_count,
                fps=fps,
                size_in_bytes=self._temp_file_manager.get_size(temp_file),
            )
        except (
            cv2.error,
            TempFileManagerError,
        ) as e:
            raise VideoMetadataReadingError(
                f"An error occurred while reading video metadata: {e}"
            ) from e
        finally:
            if capture is not None:
                capture.release()
