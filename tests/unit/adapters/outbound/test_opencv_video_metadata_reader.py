"""Tests for the OpenCVVideoMetadataReader class"""

import cv2
import pytest
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import OpenCVVideoMetadataReader
from video_processor.domain.exceptions import VideoMetadataReadingError
from video_processor.domain.value_objects import TempFile, VideoMetadata


def test_should_read_video_metadata(mocker: MockerFixture):
    """Given a TempFile containing a video
    When reading the video metadata using OpenCVVideoMetadataReader
    Then it should return a VideoMetadata object with the correct metadata
    """

    # Given
    temp_file_manager = mocker.Mock()
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    temp_file_manager.get_size.return_value = 1024
    reader = OpenCVVideoMetadataReader(temp_file_manager)

    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True

    def mock_get(prop_id):
        if prop_id == cv2.CAP_PROP_FRAME_COUNT:
            return 100
        elif prop_id == cv2.CAP_PROP_FPS:
            return 25.0
        return None

    mock_capture.get.side_effect = mock_get
    mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    # When
    result = reader.read(temp_file)

    # Then
    assert result == VideoMetadata(
        path="temp_video.mp4",
        duration_seconds=4.0,  # 100 frames / 25 fps
        frame_count=100,
        fps=25.0,
        size_in_bytes=1024,
    )

    mock_capture.release.assert_called_once()


def test_should_raise_error_on_video_metadata_reading_failure(mocker: MockerFixture):
    """Given a TempFile containing a video
    When an error occurs during video metadata reading using OpenCVVideoMetadataReader
    Then it should raise a VideoMetadataReadingError with an appropriate message
    """

    # Given
    temp_file_manager = mocker.Mock()
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    reader = OpenCVVideoMetadataReader(temp_file_manager)

    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = False
    mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    # When / Then
    with pytest.raises(VideoMetadataReadingError) as exc_info:
        reader.read(temp_file)

    assert "Failed to open video file for metadata reading." in str(exc_info.value)
    mock_capture.release.assert_called_once()


def test_should_raise_error_on_video_metadata_reading_exception(mocker: MockerFixture):
    """Given a TempFile containing a video
    When an exception occurs during video metadata reading using
        OpenCVVideoMetadataReader
    Then it should raise a VideoMetadataReadingError with an appropriate message
    """

    # Given
    temp_file_manager = mocker.Mock()
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    reader = OpenCVVideoMetadataReader(temp_file_manager)

    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True
    mock_capture.get.side_effect = cv2.error("OpenCV error")
    mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    # When / Then
    with pytest.raises(VideoMetadataReadingError) as exc_info:
        reader.read(temp_file)

    assert "An error occurred while reading video metadata: OpenCV error" in str(
        exc_info.value
    )

    mock_capture.release.assert_called_once()
