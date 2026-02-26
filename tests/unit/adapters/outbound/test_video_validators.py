"""Tests for Video Validators"""

import pytest
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import VideoSizeValidator
from video_processor.domain.exceptions import VideoValidationError
from video_processor.domain.ports import VideoMetadata


def test_should_do_nothing_if_video_size_is_within_limit(mocker: MockerFixture):
    """Given a video metadata with size within the allowed limit
    When validating the video size using VideoSizeValidator
    Then it should not raise any exceptions
    """

    # Given
    settings = mocker.Mock()
    settings.MAX_SIZE_IN_BYTES = 10 * 1024 * 1024  # 10 MB
    validator = VideoSizeValidator(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=200,
        fps=20.0,
        size_in_bytes=5 * 1024 * 1024,  # 5 MB
    )

    # When / Then
    validator.validate(metadata)


def test_should_raise_error_if_video_size_exceeds_limit(mocker: MockerFixture):
    """Given a video metadata with size exceeding the allowed limit
    When validating the video size using VideoSizeValidator
    Then it should raise a VideoMetadataReadingError with an appropriate message
    """

    # Given
    settings = mocker.Mock()
    settings.MAX_SIZE_IN_BYTES = 10 * 1024 * 1024  # 10 MB
    validator = VideoSizeValidator(settings)
    metadata = VideoMetadata(
        path="test_video.mp4",
        duration_seconds=10.0,
        frame_count=200,
        fps=20.0,
        size_in_bytes=15 * 1024 * 1024,  # 15 MB
    )

    # When / Then
    with pytest.raises(VideoValidationError) as exc_info:
        validator.validate(metadata)

    assert str(exc_info.value) == (
        "Video file size 15728640 bytes exceeds the maximum allowed size of "
        "10485760 bytes."
    )
