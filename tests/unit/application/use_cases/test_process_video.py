"""Test ProcessVideo use case"""

from uuid import UUID

from pytest_mock import MockerFixture

from video_processor.application.commands import ProcessVideoCommand
from video_processor.application.use_cases import ProcessVideoUseCase
from video_processor.domain.events import (
    VideoProcessedEvent,
    VideoProcessingStartedEvent,
)
from video_processor.domain.value_objects import (
    FileContent,
    FrameSelection,
    RawFrame,
    TempFile,
    VideoMetadata,
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

    published_events = event_publisher_mock.publish.call_args_list
    assert len(published_events) == 2
    assert isinstance(published_events[0].args[0], VideoProcessingStartedEvent) is True
    assert isinstance(published_events[1].args[0], VideoProcessedEvent) is True
