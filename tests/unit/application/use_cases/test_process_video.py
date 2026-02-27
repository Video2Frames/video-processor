"""Test ProcessVideo use case"""

from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from video_processor.application.commands import ProcessVideoCommand
from video_processor.application.use_cases import ProcessVideoUseCase
from video_processor.domain.events import (
    VideoProcessedEvent,
    VideoProcessingFailedEvent,
    VideoProcessingStartedEvent,
)
from video_processor.domain.exceptions import (
    EventPublishingError,
    FrameExtractionError,
    FramePackagingError,
    FrameSelectionError,
    InvalidStatusTransitionError,
    StorageError,
    TempFileManagerError,
    VideoMetadataReadingError,
    VideoValidationError,
)
from video_processor.domain.value_objects import (
    FileContent,
    FrameSelection,
    RawFrame,
    TempFile,
    VideoMetadata,
    VideoProcessingStatus,
)


def test_should_process_video(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase
    Then it should extract frames, package them, store them, and publish an event
        indicating the video has been processed
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])
    frames_iter = iter(
        [
            RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
            RawFrame(index=30, filename="frame_30.jpg", content=b"jpg-bytes-30"),
            RawFrame(index=60, filename="frame_60.jpg", content=b"jpg-bytes-60"),
        ]
    )

    zip_file_content = b"fake-zip-content"
    zip_file = FileContent(path="frames.zip", content=zip_file_content)
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(return_value=frames_iter)
    frame_packager.package = mocker.Mock(return_value=zip_file)

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    process_video_use_case.execute(command)

    # Then
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_called_once_with(frames_iter)
    output_storage_mock.upload_file.assert_called_once_with(
        file_content=zip_file,
        destination_path="12345678-1234-5678-1234-567812345678.zip",
    )

    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessedEvent) is True


def test_should_raise_invalid_transition_error_when_starting_processing(
    mocker: MockerFixture,
):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and an InvalidStatusTransitionError is raised
    Then it should raise the error and not publish any events
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    upload_path = "uploads/video123.mp4"

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    start_processing_mock = mocker.patch(
        "video_processor.application.use_cases.Video.start_processing",
        side_effect=InvalidStatusTransitionError(
            video_id=video_id,
            current_status=VideoProcessingStatus.COMPLETED,
            attempted_status=VideoProcessingStatus.PROCESSING,
        ),
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(InvalidStatusTransitionError) as exc:
        process_video_use_case.execute(command)

    # Then
    expected_message = (
        f"Invalid status transition for video {str(video_id)}: "
        f"COMPLETED -> PROCESSING"
    )

    assert str(exc.value) == expected_message
    start_processing_mock.assert_called_once_with()
    input_storage_mock.download_file.assert_not_called()
    temp_file_manager.create.assert_not_called()
    video_metadata_reader_mock.read.assert_not_called()
    video_validator_mock.validate.assert_not_called()
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_not_called()
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 1
    assert isinstance(published_events[0].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_download_file_storage_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a StorageError is raised during file
        download
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    upload_path = "uploads/video123.mp4"

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(
        side_effect=StorageError("Failed to download file")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(StorageError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to download file"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_not_called()
    video_metadata_reader_mock.read.assert_not_called()
    video_validator_mock.validate.assert_not_called()
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_not_called()
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_temp_file_creation_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a TempFileManagerError is raised during
        temp file creation
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(
        side_effect=TempFileManagerError("Failed to create temp file")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(TempFileManagerError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to create temp file"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )
    video_metadata_reader_mock.read.assert_not_called()
    video_validator_mock.validate.assert_not_called()
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_not_called()
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_video_metadata_reading_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a VideoMetadataReadingError is raised
        during video metadata reading
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(
        side_effect=VideoMetadataReadingError("Failed to read video metadata")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(VideoMetadataReadingError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to read video metadata"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_not_called()
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_video_validation_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a VideoValidationError is raised
        during video validation
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(
        side_effect=VideoValidationError("Video failed validation")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(VideoValidationError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Video failed validation"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_frame_selection_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a FrameSelectionError is raised
        during frame selection
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(
        side_effect=FrameSelectionError("Failed to select frames")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(FrameSelectionError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to select frames"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_frame_extraction_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a FrameExtractionError is raised
        during frame extraction
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(
        side_effect=FrameExtractionError("Failed to extract frames")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(FrameExtractionError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to extract frames"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_frame_packaging_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a FramePackagingError is raised
        during frame packaging
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])
    frames_iter = iter(
        [
            RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
            RawFrame(index=30, filename="frame_30.jpg", content=b"jpg-bytes-30"),
            RawFrame(index=60, filename="frame_60.jpg", content=b"jpg-bytes-60"),
        ]
    )

    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(return_value=frames_iter)
    frame_packager.package = mocker.Mock(
        side_effect=FramePackagingError("Failed to package frames")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(FramePackagingError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to package frames"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_called_once_with(frames_iter)
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_fail_with_upload_output_file_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a StorageError is raised during output
        file upload
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])
    frames_iter = iter(
        [
            RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
            RawFrame(index=30, filename="frame_30.jpg", content=b"jpg-bytes-30"),
            RawFrame(index=60, filename="frame_60.jpg", content=b"jpg-bytes-60"),
        ]
    )

    zip_file_content = b"fake-zip-content"
    zip_file = FileContent(path="frames.zip", content=zip_file_content)
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(return_value=frames_iter)
    frame_packager.package = mocker.Mock(return_value=zip_file)
    output_storage_mock.upload_file = mocker.Mock(
        side_effect=StorageError("Failed to upload output file")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(StorageError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to upload output file"
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_called_once_with(frames_iter)
    output_storage_mock.upload_file.assert_called_once_with(
        file_content=zip_file,
        destination_path="12345678-1234-5678-1234-567812345678.zip",
    )

    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_raises_invalid_transition_error_when_completing_processing(
    mocker: MockerFixture,
):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and an InvalidStatusTransitionError is raised
        when marking the video as processed
    Then it should raise the error and publish a VideoProcessingFailedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])
    frames_iter = iter(
        [
            RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
            RawFrame(index=30, filename="frame_30.jpg", content=b"jpg-bytes-30"),
            RawFrame(index=60, filename="frame_60.jpg", content=b"jpg-bytes-60"),
        ]
    )

    zip_file_content = b"fake-zip-content"
    zip_file = FileContent(path="frames.zip", content=zip_file_content)
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(return_value=frames_iter)
    frame_packager.package = mocker.Mock(return_value=zip_file)
    output_storage_mock.upload_file = mocker.Mock(return_value=None)

    complete_processing_mock = mocker.patch(
        "video_processor.application.use_cases.Video.complete_processing",
        side_effect=InvalidStatusTransitionError(
            video_id=video_id,
            current_status=VideoProcessingStatus.COMPLETED,
            attempted_status=VideoProcessingStatus.COMPLETED,
        ),
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(InvalidStatusTransitionError) as exc:
        process_video_use_case.execute(command)

    # Then
    expected_message = (
        f"Invalid status transition for video {str(video_id)}: "
        f"COMPLETED -> COMPLETED"
    )

    assert str(exc.value) == expected_message
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_called_once_with(frames_iter)
    output_storage_mock.upload_file.assert_called_once_with(
        file_content=zip_file,
        destination_path="12345678-1234-5678-1234-567812345678.zip",
    )

    complete_processing_mock.assert_called_once_with()
    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessingFailedEvent) is True


def test_should_raise_event_publishing_error_when_publishing_event(
    mocker: MockerFixture,
):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and an EventPublishingError is raised
        when publishing the VideoProcessingFailedEvent
    Then it should raise the error
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path="uploads/video123.mp4",
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    event_publisher_mock.publish = mocker.Mock(
        side_effect=EventPublishingError("Failed to publish event")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    with pytest.raises(EventPublishingError) as exc:
        process_video_use_case.execute(command)

    # Then
    assert str(exc.value) == "Failed to publish event"
    input_storage_mock.download_file.assert_not_called()
    temp_file_manager.create.assert_not_called()
    video_metadata_reader_mock.read.assert_not_called()
    video_validator_mock.validate.assert_not_called()
    frame_selector_mock.select.assert_not_called()
    frame_extractor_mock.extract.assert_not_called()
    frame_packager.package.assert_not_called()
    output_storage_mock.upload_file.assert_not_called()
    temp_file_manager.delete.assert_not_called()

    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 1
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True


def test_should_not_fail_with_temp_file_deletion_error(mocker: MockerFixture):
    """Given a valid ProcessVideoCommand
    When executing the ProcessVideoUseCase and a TempFileManagerError is raised during
        temp file deletion
    Then it should not raise the error and should publish a VideoProcessedEvent
    """

    # Given
    video_id = UUID("12345678-1234-5678-1234-567812345678")
    video_content_bytes = b"fake-video-content"
    upload_path = "uploads/video123.mp4"
    video_content = FileContent(path=upload_path, content=video_content_bytes)
    temp_file = TempFile(path="temp_video.mp4")
    metadata = VideoMetadata(
        path=upload_path,
        duration_seconds=60.0,
        frame_count=1800,
        fps=30.0,
        size_in_bytes=len(video_content_bytes),
    )

    frame_selection = FrameSelection(indexes=[0, 30, 60])
    frames_iter = iter(
        [
            RawFrame(index=0, filename="frame_0.jpg", content=b"jpg-bytes-0"),
            RawFrame(index=30, filename="frame_30.jpg", content=b"jpg-bytes-30"),
            RawFrame(index=60, filename="frame_60.jpg", content=b"jpg-bytes-60"),
        ]
    )

    zip_file_content = b"fake-zip-content"
    zip_file = FileContent(path="frames.zip", content=zip_file_content)
    command = ProcessVideoCommand(
        video_id=video_id,
        upload_path=upload_path,
    )

    input_storage_mock = mocker.Mock()
    output_storage_mock = mocker.Mock()
    event_publisher_mock = mocker.Mock()
    video_metadata_reader_mock = mocker.Mock()
    video_validator_mock = mocker.Mock()
    frame_selector_mock = mocker.Mock()
    frame_extractor_mock = mocker.Mock()
    frame_packager = mocker.Mock()
    temp_file_manager = mocker.Mock()

    input_storage_mock.download_file = mocker.Mock(return_value=video_content)
    temp_file_manager.create = mocker.Mock(return_value=temp_file)
    video_metadata_reader_mock.read = mocker.Mock(return_value=metadata)
    video_validator_mock.validate = mocker.Mock(return_value=None)
    frame_selector_mock.select = mocker.Mock(return_value=frame_selection)
    frame_extractor_mock.extract = mocker.Mock(return_value=frames_iter)
    frame_packager.package = mocker.Mock(return_value=zip_file)
    output_storage_mock.upload_file = mocker.Mock(return_value=None)
    temp_file_manager.delete = mocker.Mock(
        side_effect=TempFileManagerError("Failed to delete temp file")
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage_mock,
        output_storage=output_storage_mock,
        event_publisher=event_publisher_mock,
        video_metadata_reader=video_metadata_reader_mock,
        frame_selector=frame_selector_mock,
        frame_extractor=frame_extractor_mock,
        frame_packager=frame_packager,
        temp_file_manager=temp_file_manager,
        video_validators=[video_validator_mock],
    )

    # When
    process_video_use_case.execute(command)

    # Then
    input_storage_mock.download_file.assert_called_once_with(upload_path)
    temp_file_manager.create.assert_called_once_with(
        content=video_content_bytes, suffix="mp4"
    )

    video_metadata_reader_mock.read.assert_called_once_with(temp_file)
    video_validator_mock.validate.assert_called_once_with(metadata)
    frame_selector_mock.select.assert_called_once_with(metadata)
    frame_extractor_mock.extract.assert_called_once_with(temp_file, frame_selection)
    frame_packager.package.assert_called_once_with(frames_iter)
    output_storage_mock.upload_file.assert_called_once_with(
        file_content=zip_file,
        destination_path="12345678-1234-5678-1234-567812345678.zip",
    )

    temp_file_manager.delete.assert_called_once_with(temp_file)
    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessedEvent) is True
