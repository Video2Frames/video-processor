"""Use cases for Video Processor Application"""

import logging

from video_processor.application.commands import ProcessVideoCommand
from video_processor.domain.entities import Video
from video_processor.domain.exceptions import (
    EventPublishingError,
    FrameProcessingError,
    InvalidStatusTransitionError,
    StorageError,
)
from video_processor.domain.ports import EventPublisher, FrameProcessor, StorageService
from video_processor.domain.value_objects import FileContent

logger = logging.getLogger(__name__)


class ProcessVideoUseCase:
    """Use case for processing a video."""

    def __init__(
        self,
        storage_service: StorageService,
        frame_processor: FrameProcessor,
        event_publisher: EventPublisher,
    ):
        self._storage_service = storage_service
        self._frame_processor = frame_processor
        self._event_publisher = event_publisher

    def execute(self, command: ProcessVideoCommand) -> Video:
        """Execute the use case to process a video.

        Args:
            command (ProcessVideoCommand): The command containing video details.

        Returns:
            Video: The processed video entity.
        """

        logger.info("Starting the use case to process video ID %s", command.video_id)
        video = Video(video_id=command.video_id, upload_path=command.upload_path)
        self._start_processing(video)
        video_content = self._download_video(video)
        zip_content = self._process_frames(video, video_content)
        self._upload_output_file(video=video, file_content=zip_content)
        self._complete_processing(video)
        return video

    def _start_processing(self, video: Video) -> None:
        """Start processing the given video.

        Args:
            video (Video): The video entity to start processing.

        Raises:
            InvalidStatusTransitionError: If the status transition is invalid.
        """

        try:
            video.start_processing()
            logger.info("Video ID %s processing started", video.video_id)
        except InvalidStatusTransitionError as e:
            err_class = e.__class__.__name__
            err_prefix = (
                f"Video ID {video.video_id} processing start failed due to {err_class}"
            )
            video.fail_processing(error_message=f"{err_prefix}: {str(e)}")
            logger.error(err_prefix, exc_info=True)
            raise e
        finally:
            self._publish_events(video)

    def _download_video(self, video: Video) -> FileContent:
        """Download the video content from storage.

        Args:
            video (Video): The video entity containing upload path.

        Returns:
            FileContent: The downloaded video content.

        Raises:
            StorageError: If an error occurs during file download.
        """

        try:
            video_content: FileContent = self._storage_service.download_file(
                video.upload_path
            )

            logger.info("Video ID %s downloaded from storage", video.video_id)
            return video_content
        except StorageError as e:
            err_class = e.__class__.__name__
            err_prefix = f"Video ID {video.video_id} download failed due to {err_class}"
            video.fail_processing(error_message=f"{err_prefix}: {str(e)}")
            logger.error(err_prefix, exc_info=True)
            self._publish_events(video)
            raise e

    def _process_frames(self, video: Video, video_content: FileContent) -> FileContent:
        """Process the video to extract frames.

        Args:
            video (Video): The video entity being processed.
            video_content (FileContent): The content of the video file.

        Returns:
            FileContent: The processed frames as a zip file.

        Raises:
            FrameProcessingError: If an error occurs during frame extraction.
        """

        try:
            zip_content = self._frame_processor.process_video(
                video_content=video_content
            )
            logger.info("Video ID %s frame processing completed", video.video_id)
            return zip_content
        except FrameProcessingError as e:
            err_class = e.__class__.__name__
            err_prefix = (
                f"Video ID {video.video_id} frame processing failed due to {err_class}"
            )
            video.fail_processing(error_message=f"{err_prefix}: {str(e)}")
            logger.error(err_prefix, exc_info=True)
            self._publish_events(video)
            raise e

    def _upload_output_file(self, video: Video, file_content: FileContent) -> None:
        """Upload the processed frames to storage.

        Args:
            video (Video): The video entity being processed.
            file_content (FileContent): The ZIP file content to be uploaded.

        Raises:
            StorageError: If an error occurs during file upload.
        """

        try:
            self._storage_service.upload_file(
                file_content=file_content, destination_path=video.output_path
            )

            logger.info("Video ID %s uploaded to storage", video.video_id)
        except StorageError as e:
            err_class = e.__class__.__name__
            err_prefix = f"Video ID {video.video_id} upload failed due to {err_class}"
            video.fail_processing(error_message=f"{err_prefix}: {str(e)}")
            logger.error(err_prefix, exc_info=True)
            self._publish_events(video)
            raise e

    def _complete_processing(self, video: Video) -> None:
        """Complete the processing of the video.

        Args:
            video (Video): The video entity being processed.

        Raises:
            InvalidStatusTransitionError: If the status transition is invalid.
        """

        try:
            video.complete_processing()
            logger.info("Video ID %s processing completed", video.video_id)
        except InvalidStatusTransitionError as e:
            err_class = e.__class__.__name__
            err_prefix = (
                f"Video ID {video.video_id} processing completion failed "
                f"due to {err_class}"
            )
            video.fail_processing(error_message=f"{err_prefix}: {str(e)}")
            logger.error(err_prefix, exc_info=True)
            raise e
        finally:
            self._publish_events(video)

    def _publish_events(self, video: Video) -> None:
        """Publish domain events for the video.

        Args:
            video (Video): The video entity containing events.
        """

        for event in video.collect_events():
            try:
                self._event_publisher.publish(event)
            except EventPublishingError as e:
                logger.error(
                    "Failed to publish event %s due to %s",
                    event,
                    e.__class__.__name__,
                    exc_info=True,
                )

                raise e
