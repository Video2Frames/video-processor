"""Test cases for domain entities"""

from uuid import UUID

import pytest

from video_processor.domain.entities import Video
from video_processor.domain.events import VideoProcessingStartedEvent
from video_processor.domain.exceptions import InvalidStatusTransitionError
from video_processor.domain.value_objects import VideoProcessingStatus


def test_should_start_processing_if_status_is_pending():
    """Given a video with PENDING status
    When start_processing is called
    Then the status should change to PROCESSING
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    assert video.status == VideoProcessingStatus.PENDING

    # When
    video.start_processing()
    events = video.collect_events()

    # Then
    assert video.status == VideoProcessingStatus.PROCESSING
    assert len(events) == 1
    assert isinstance(events[0], VideoProcessingStartedEvent)
    assert events[0].video_id == video_id
    assert events[0].processing_started_at is not None


def test_should_not_start_processing_if_status_is_not_pending():
    """Given a video with a status other than PENDING
    When start_processing is called
    Then an InvalidStatusTransitionError should be raised
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    video._status = VideoProcessingStatus.PROCESSING

    # When / Then
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        video.start_processing()

    assert str(exc_info.value) == (
        f"Invalid status transition for video {video_id}: PROCESSING -> PROCESSING"
    )


def test_should_complete_processing_if_status_is_processing():
    """Given a video with PROCESSING status
    When complete_processing is called
    Then the status should change to COMPLETED
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    video._status = VideoProcessingStatus.PROCESSING

    # When
    video.complete_processing()
    events = video.collect_events()

    # Then
    assert video.status == VideoProcessingStatus.COMPLETED
    assert len(events) == 1
    assert events[0].video_id == video_id
    assert events[0].output_path == f"s3://video2frames-extracted-frames/{video_id}.zip"


def test_should_not_complete_processing_if_status_is_not_processing():
    """Given a video with a status other than PROCESSING
    When complete_processing is called
    Then an InvalidStatusTransitionError should be raised
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    video._status = VideoProcessingStatus.PENDING

    # When / Then
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        video.complete_processing()

    assert str(exc_info.value) == (
        f"Invalid status transition for video {video_id}: PENDING -> COMPLETED"
    )


def test_should_fail_processing_if_status_is_processing():
    """Given a video with PROCESSING status
    When fail_processing is called
    Then the status should change to FAILED
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    video._status = VideoProcessingStatus.PROCESSING

    # When
    video.fail_processing(error_message="An error occurred")
    events = video.collect_events()

    # Then
    assert video.status == VideoProcessingStatus.FAILED
    assert len(events) == 1
    assert events[0].video_id == video_id
    assert events[0].error_message == "An error occurred"


def test_should_not_fail_processing_if_status_is_not_processing_or_pending():
    """Given a video with a status other than PROCESSING or PENDING
    When fail_processing is called
    Then an InvalidStatusTransitionError should be raised
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video = Video(video_id=video_id, upload_path="/path/to/video.mp4")
    video._status = VideoProcessingStatus.COMPLETED

    # When / Then
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        video.fail_processing(error_message="An error occurred")

    assert str(exc_info.value) == (
        f"Invalid status transition for video {video_id}: COMPLETED -> FAILED"
    )
