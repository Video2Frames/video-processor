"""Tests for the OpenCVFrameExtractor class"""

import cv2
import pytest
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import OpenCVFrameExtractor
from video_processor.domain.exceptions import FrameExtractionError
from video_processor.domain.value_objects import FrameSelection, RawFrame, TempFile


def test_should_extract_frames(mocker: MockerFixture):
    """Given a TempFile containing a video and a FrameSelection with specific indexes
    When extracting frames using OpenCVFrameExtractor
    Then it should return an iterator of RawFrame objects corresponding to the
        requested indexes
    """

    # Given
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    extractor = OpenCVFrameExtractor()
    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True
    frame_obj_0 = object()
    frame_obj_1 = object()
    mock_capture.read.side_effect = [(True, frame_obj_0), (True, frame_obj_1)]
    mock_videocap = mocker.patch("cv2.VideoCapture", return_value=mock_capture)
    mock_buffer1 = mocker.Mock()
    mock_buffer1.tobytes.return_value = b"jpg-bytes-0"
    mock_buffer2 = mocker.Mock()
    mock_buffer2.tobytes.return_value = b"jpg-bytes-5"
    mock_imencode = mocker.patch(
        "cv2.imencode", side_effect=[(True, mock_buffer1), (True, mock_buffer2)]
    )

    frame_selection = FrameSelection(indexes=[0, 5])

    # When
    frames = list(
        extractor.extract(temp_file=temp_file, frame_selection=frame_selection)
    )

    # Then
    assert len(frames) == 2
    assert frames == [
        RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
        RawFrame(index=5, filename="frame_5.jpg", content=b"jpg-bytes-5"),
    ]

    mock_videocap.assert_called_once_with("temp_video.mp4")
    assert mock_capture.set.call_count == 2
    assert mock_capture.set.call_args_list == [
        mocker.call(cv2.CAP_PROP_POS_FRAMES, 0),
        mocker.call(cv2.CAP_PROP_POS_FRAMES, 5),
    ]

    assert mock_capture.read.call_count == 2
    assert mock_capture.read.call_args_list == [mocker.call(), mocker.call()]

    assert mock_imencode.call_count == 2
    assert mock_imencode.call_args_list == [
        mocker.call(".jpg", obj) for obj in [frame_obj_0, frame_obj_1]
    ]


def test_should_raise_error_on_video_open_failure(mocker: MockerFixture):
    """Given a TempFile containing a video and a FrameSelection with specific indexes
    When the video file cannot be opened using OpenCVFrameExtractor
    Then it should raise a FrameExtractionError with an appropriate message
    """

    # Given
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    extractor = OpenCVFrameExtractor()
    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = False
    mock_videocap = mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    frame_selection = FrameSelection(indexes=[0])

    # When / Then
    with pytest.raises(FrameExtractionError) as exc_info:
        list(extractor.extract(temp_file=temp_file, frame_selection=frame_selection))

    assert str(exc_info.value) == "Failed to open video file for frame extraction."

    mock_videocap.assert_called_once_with("temp_video.mp4")
    mock_capture.release.assert_called_once()


def test_should_raise_error_on_frame_extraction_failure(mocker: MockerFixture):
    """Given a TempFile containing a video and a FrameSelection with specific indexes
    When an error occurs during frame extraction using OpenCVFrameExtractor
    Then it should raise a FrameExtractionError with an appropriate message
    """

    # Given
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    extractor = OpenCVFrameExtractor()
    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True
    mock_capture.read.return_value = (False, None)
    mock_videocap = mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    frame_selection = FrameSelection(indexes=[0])

    # When / Then
    with pytest.raises(FrameExtractionError) as exc_info:
        list(extractor.extract(temp_file=temp_file, frame_selection=frame_selection))

    assert str(exc_info.value) == "Failed to read frame at index 0."

    mock_videocap.assert_called_once_with("temp_video.mp4")
    mock_capture.set.assert_called_once_with(cv2.CAP_PROP_POS_FRAMES, 0)
    mock_capture.read.assert_called_once()
    mock_capture.release.assert_called_once()


def test_should_raise_error_on_frame_encoding_failure(mocker: MockerFixture):
    """Given a TempFile containing a video and a FrameSelection with specific indexes
    When an error occurs during frame encoding using OpenCVFrameExtractor
    Then it should raise a FrameExtractionError with an appropriate message
    """

    # Given
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    extractor = OpenCVFrameExtractor()
    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True
    frame_obj = object()
    mock_capture.read.return_value = (True, frame_obj)
    mock_videocap = mocker.patch("cv2.VideoCapture", return_value=mock_capture)
    mock_imencode = mocker.patch("cv2.imencode", return_value=(False, None))

    frame_selection = FrameSelection(indexes=[0])

    # When / Then
    with pytest.raises(FrameExtractionError) as exc_info:
        list(extractor.extract(temp_file=temp_file, frame_selection=frame_selection))

    assert str(exc_info.value) == "Failed to encode frame at index 0."

    mock_videocap.assert_called_once_with("temp_video.mp4")
    mock_capture.set.assert_called_once_with(cv2.CAP_PROP_POS_FRAMES, 0)
    mock_capture.read.assert_called_once()
    mock_imencode.assert_called_once_with(".jpg", frame_obj)
    mock_capture.release.assert_called_once()


def test_should_raise_error_on_cv2_exception(mocker: MockerFixture):
    """Given a TempFile containing a video and a FrameSelection with specific indexes
    When an OpenCV error occurs during frame extraction using OpenCVFrameExtractor
    Then it should raise a FrameExtractionError with an appropriate message
    """

    # Given
    temp_file = TempFile(path="temp_video.mp4", content=b"")
    extractor = OpenCVFrameExtractor()
    mock_capture = mocker.Mock()
    mock_capture.isOpened.return_value = True
    mock_capture.read.side_effect = cv2.error("OpenCV error")
    mock_videocap = mocker.patch("cv2.VideoCapture", return_value=mock_capture)

    frame_selection = FrameSelection(indexes=[0])

    # When / Then
    with pytest.raises(FrameExtractionError) as exc_info:
        list(extractor.extract(temp_file=temp_file, frame_selection=frame_selection))

    assert "An error occurred during frame extraction: OpenCV error" in str(
        exc_info.value
    )

    mock_videocap.assert_called_once_with("temp_video.mp4")
    mock_capture.set.assert_called_once_with(cv2.CAP_PROP_POS_FRAMES, 0)
    mock_capture.read.assert_called_once()
    mock_capture.release.assert_called_once()
