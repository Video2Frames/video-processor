"""Tests for the UniformFrameSelector class"""

import pytest
from pytest_mock import MockerFixture

from video_processor.adapters.outbound.frame_selectors import UniformFrameSelector
from video_processor.domain.exceptions import FrameSelectionError
from video_processor.domain.value_objects import FrameSelection, VideoMetadata


def test_should_select_20_frames_for_200_frames_with_10_percent_threshold(
    mocker: MockerFixture,
):
    """Given a video with 200 frames and a percentage threshold of 10%
    When selecting frames using the UniformFrameSelector
    Then it should return a FrameSelection with 20 indexes uniformly distributed across
        the video duration
    """

    # Given
    settings = mocker.Mock()
    settings.PERCENTAGE_THRESHOLD = 0.1
    selector = UniformFrameSelector(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=200,
        fps=20.0,
        size_in_bytes=10 * 1024 * 1024,  # 10 MB
    )

    # When
    selection = selector.select(metadata)

    assert isinstance(selection, FrameSelection)
    assert len(selection.indexes) == 20
    assert selection.indexes[0] == 0
    assert selection.indexes[-1] == 500


def test_should_select_first_frame_if_total_frames_is_1(mocker: MockerFixture):
    """Given a video with 1 frame and a percentage threshold of 10%
    When selecting frames using the UniformFrameSelector
    Then it should return a FrameSelection with the index of the single frame
    """

    # Given
    settings = mocker.Mock()
    settings.PERCENTAGE_THRESHOLD = 0.1
    selector = UniformFrameSelector(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=1,
        fps=20.0,
        size_in_bytes=10 * 1024 * 1024,  # 10 MB
    )

    # When
    selection = selector.select(metadata)

    assert isinstance(selection, FrameSelection)
    assert len(selection.indexes) == 1
    assert selection.indexes[0] == 0


def test_should_raise_error_for_invalid_percentage_threshold(mocker: MockerFixture):
    """Given a percentage threshold that is not between 0 and 1
    When selecting frames using the UniformFrameSelector
    Then it should raise a FrameSelectionError
    """

    # Given
    settings = mocker.Mock()
    settings.PERCENTAGE_THRESHOLD = -0.5  # Invalid threshold
    selector = UniformFrameSelector(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=200,
        fps=20.0,
        size_in_bytes=10 * 1024 * 1024,  # 10 MB
    )

    # When / Then
    with pytest.raises(FrameSelectionError) as exc_info:
        selector.select(metadata)

    assert "percentage_threshold must be between 0 and 1" == str(exc_info.value)


def test_should_raise_error_for_video_with_no_frames(mocker: MockerFixture):
    """Given a video with no frames
    When selecting frames using the UniformFrameSelector
    Then it should raise a FrameSelectionError
    """

    # Given
    settings = mocker.Mock()
    settings.PERCENTAGE_THRESHOLD = 0.1
    selector = UniformFrameSelector(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=0,  # No frames
        fps=20.0,
        size_in_bytes=10 * 1024 * 1024,  # 10 MB
    )

    # When / Then
    with pytest.raises(FrameSelectionError) as exc_info:
        selector.select(metadata)

    assert "Video has no frames to select" == str(exc_info.value)
