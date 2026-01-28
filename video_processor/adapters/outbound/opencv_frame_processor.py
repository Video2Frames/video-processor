"""OpenCV implementation of FrameProcessor port to extract frames from video files"""

import os
import tempfile
import zipfile

import cv2
import numpy as np

from video_processor.domain.exceptions import FrameProcessingError
from video_processor.domain.ports import FrameProcessor
from video_processor.domain.value_objects import FileContent
from video_processor.infrastructure.config import FrameProcessorSettings


class OpenCVFrameProcessor(FrameProcessor):
    """An implementation of the FrameProcessor port that uses OpenCV
    to extract frames"""

    def __init__(self, settings: FrameProcessorSettings):
        self.max_frames = settings.MAX_FRAMES

    def process_video(self, video_content: FileContent) -> FileContent:
        temp_file_path = None
        capture = None
        zip_file = None
        zip_file_path = None

        try:
            temp_file_path = self._create_temp_video_file(video_content)
            capture = cv2.VideoCapture(temp_file_path)
            self._validate_video_capture(capture)
            frame_count = self._count_frames(capture)
            frame_indexes = self._get_frame_indexes_to_extract(frame_count)
            zip_file, zip_file_path = self._create_temp_zip_file()
            for index, frame_index in enumerate(frame_indexes):
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ret, frame = capture.read()
                if not ret:
                    raise FrameProcessingError(
                        f"Failed to read frame at index {frame_index}."
                    )

                ret_buffer, buffer = cv2.imencode(".jpg", frame)
                if not ret_buffer:
                    raise FrameProcessingError(
                        f"Failed to encode frame at index {frame_index}."
                    )

                frame_filename = f"frame_{index}.jpg"
                zip_file.writestr(frame_filename, buffer.tobytes())

            zip_file.close()
            with open(zip_file_path, "rb") as f:
                return FileContent(
                    path=os.path.basename(zip_file_path),
                    content=f.read(),
                )

        finally:
            if temp_file_path is not None:
                os.remove(temp_file_path)

            if capture is not None:
                capture.release()

            if zip_file is not None:
                zip_file.close()

            if zip_file_path is not None:
                os.remove(zip_file_path)

    def _create_temp_video_file(self, video_content: FileContent) -> str:
        """Create a temporary video file from the given FileContent

        Args:
            video_content (FileContent): The content of the video file.

        Returns:
            str: The path to the temporary video file.
        """

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file.write(video_content.content)
        temp_file.close()
        return temp_file.name

    def _validate_video_capture(self, capture: cv2.VideoCapture) -> None:
        """Validate that the video capture object is opened successfully.

        Args:
            capture (cv2.VideoCapture): The video capture object.

        Raises:
            FrameProcessingError: If the video cannot be opened.
        """
        if not capture.isOpened():
            raise FrameProcessingError("Failed to open video file for processing.")

    def _count_frames(self, capture: cv2.VideoCapture) -> int:
        """Count the number of frames in the video capture object.

        Args:
            capture (cv2.VideoCapture): The video capture object.

        Returns:
            int: The total number of frames in the video.
        """
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    def _get_frame_indexes_to_extract(
        self, total_frames: int
    ) -> np.typing.NDArray[np.int_]:
        """Get the list of frame indexes to extract based on the given interval.

        Args:
            total_frames (int): The total number of frames in the video.

        Returns:
            np.typing.NDArray[np.int_]: The list of frame indexes to extract.
        """

        if self.max_frames is not None:
            frames_to_extract = min(int(total_frames * 0.01), self.max_frames)
            frames_to_extract = max(frames_to_extract, 1)
        else:
            frames_to_extract = total_frames

        frame_indexes = np.linspace(0, total_frames - 1, frames_to_extract, dtype=int)
        return frame_indexes

    def _create_temp_zip_file(self) -> tuple[zipfile.ZipFile, str]:
        """Create a temporary zip file to store extracted frames.

        Returns:
            tuple[zipfile.ZipFile, str]: The temporary zip file object and its filename.
        """
        temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        return zipfile.ZipFile(temp_zip_file.name, mode="w"), temp_zip_file.name
