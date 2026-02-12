from typing import Iterator

import cv2

from video_processor.domain.exceptions import FrameExtractionError
from video_processor.domain.ports import FrameExtractor
from video_processor.domain.value_objects import FrameSelection, RawFrame, TempFile


class OpenCVFrameExtractor(FrameExtractor):
    """The OpenCVFrameExtractor is an implementation of the FrameExtractor port that
    uses OpenCV to extract frames from video files."""

    def extract(
        self, temp_file: TempFile, frame_selection: FrameSelection
    ) -> Iterator[RawFrame]:
        try:
            capture = cv2.VideoCapture(temp_file.path)
            if not capture.isOpened():
                raise FrameExtractionError(
                    "Failed to open video file for frame extraction."
                )

            for frame_index in frame_selection.indexes:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ret, frame = capture.read()
                if not ret:
                    raise FrameExtractionError(
                        f"Failed to read frame at index {frame_index}."
                    )

                ret_buffer, buffer = cv2.imencode(".jpg", frame)
                if not ret_buffer:
                    raise FrameExtractionError(
                        f"Failed to encode frame at index {frame_index}."
                    )

                yield RawFrame(
                    index=frame_index,
                    filename=f"frame_{frame_index}.jpg",
                    content=buffer.tobytes(),
                )
        finally:
            if capture is not None:
                capture.release()
