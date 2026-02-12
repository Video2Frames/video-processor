import logging
from typing import Iterator, NoReturn

from video_processor.application.commands import ProcessVideoCommand
from video_processor.domain.entities import Video
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
from video_processor.domain.ports import (
    EventPublisher,
    FrameExtractor,
    FramePackager,
    FrameSelector,
    InputStorage,
    OutputStorage,
    TempFileManager,
    VideoMetadataReader,
    VideoValidator,
)
from video_processor.domain.value_objects import (
    FileContent,
    FrameSelection,
    RawFrame,
    TempFile,
    VideoMetadata,
)

logger = logging.getLogger(__name__)


class ProcessVideoUseCase:
    """Use case for processing a video."""

    def __init__(
        self,
        input_storage: InputStorage,
        output_storage: OutputStorage,
        event_publisher: EventPublisher,
        video_metadata_reader: VideoMetadataReader,
        frame_selector: FrameSelector,
        frame_extractor: FrameExtractor,
        frame_packager: FramePackager,
        temp_file_manager: TempFileManager,
        video_validators: list[VideoValidator],
    ):
        self._input_storage = input_storage
        self._output_storage = output_storage
        self._event_publisher = event_publisher
        self._video_metadata_reader = video_metadata_reader
        self._frame_selector = frame_selector
        self._frame_extractor = frame_extractor
        self._frame_packager = frame_packager
        self._temp_file_manager = temp_file_manager
        self._video_validators = video_validators

    def execute(self, command: ProcessVideoCommand) -> Video:
        """Execute the use case to process a video.

        Args:
            command (ProcessVideoCommand): The command containing video details.

        Returns:
            Video: The processed video entity.
        """

        temp_video_file: TempFile | None = None
        logger.info("Starting the use case to process video ID %s", command.video_id)
        try:
            video = Video(video_id=command.video_id, upload_path=command.upload_path)
            self._start_processing(video)
            video_content = self._download_video(video)
            temp_video_file = self._create_temp_file(video, video_content)
            video_metadata = self._get_video_metadata(video, temp_video_file)
            self._validate_video(video, video_metadata)
            frame_selection = self._select_frames(video, video_metadata)
            raw_frames = self._extract_frames(video, temp_video_file, frame_selection)
            zip_content = self._package_frames(video, raw_frames)
            self._upload_output_file(video=video, file_content=zip_content)
            self._complete_processing(video)
            return video
        finally:
            if temp_video_file:
                self._delete_temp_file(temp_video_file)

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
        except InvalidStatusTransitionError as exc:
            self._fail_processing(video, exc)
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
            video_content: FileContent = self._input_storage.download_file(
                video.upload_path
            )

            logger.info("Video ID %s downloaded from storage", video.video_id)
            return video_content
        except StorageError as exc:
            self._fail_processing(video, exc)

    def _create_temp_file(self, video: Video, video_content: FileContent) -> TempFile:
        """Create a temporary file for the video content.

        Args:
            video (Video): The video entity for which to create the temp file.
            video_content (FileContent): The content of the video to write to the
                temp file.

        Returns:
            TempFile: The created temporary file.

        Raises:
            TempFileManagerError: If an error occurs during temp file creation.
        """

        suffix = video_content.path.split(".")[-1] if "." in video_content.path else ""
        try:
            temp_file = self._temp_file_manager.create(
                content=video_content.content, suffix=suffix
            )

            logger.info(
                "Temporary file created for video ID %s at path %s",
                video.video_id,
                temp_file.path,
            )

            return temp_file
        except TempFileManagerError as exc:
            self._fail_processing(video, exc)

    def _get_video_metadata(self, video: Video, temp_file: TempFile) -> VideoMetadata:
        """Get metadata of the video.

        Args:
            video (Video): The video entity for which to get metadata.
            temp_file (TempFile): The temporary file containing the video content.

        Returns:
            VideoMetadata: The metadata of the video.

        Raises:
            VideoMetadataReadingError: If an error occurs during metadata reading.
        """

        try:
            metadata = self._video_metadata_reader.read(temp_file)
            logger.info("Metadata read for video ID %s: %s", video.video_id, metadata)
            return metadata
        except VideoMetadataReadingError as exc:
            self._fail_processing(video, exc)

    def _validate_video(self, video: Video, metadata: VideoMetadata) -> None:
        """Validate the video against defined validators.

        Args:
            video (Video): The video entity to validate.
            metadata (VideoMetadata): The metadata of the video to use for validation.

        Raises:
            VideoValidationError: If any validation fails.
        """

        for validator in self._video_validators:
            try:
                validator.validate(metadata)
                logger.info(
                    "Video ID %s passed validation with %s",
                    video.video_id,
                    validator.__class__.__name__,
                )
            except VideoValidationError as exc:
                self._fail_processing(video, exc)

    def _select_frames(self, video: Video, metadata: VideoMetadata) -> FrameSelection:
        """Select frames from the video based on its metadata.

        Args:
            video (Video): The video entity for which to select frames.
            metadata (VideoMetadata): The metadata of the video to use for
                frame selection.
        Returns:
            FrameSelection: The selected frames for processing.
        Raises:
            FrameSelectionError: If an error occurs during frame selection.
        """

        try:
            frame_selection = self._frame_selector.select(metadata)
            logger.info(
                "Frames selected for video ID %s: %s",
                video.video_id,
                ", ".join([str(index) for index in frame_selection.indexes]),
            )
            return frame_selection
        except FrameSelectionError as exc:
            self._fail_processing(video, exc)

    def _extract_frames(
        self, video: Video, temp_file: TempFile, frame_selection: FrameSelection
    ) -> Iterator[RawFrame]:
        """Extract frames from the video based on the selected frames.

        Args:
            video (Video): The video entity for which to extract frames.
            temp_file (TempFile): The temporary file containing the video content.
            frame_selection (FrameSelection): The selected frames to extract.
        Returns:
            Iterator[RawFrame]: An iterator over the extracted raw frames.
        Raises:
            FrameExtractionError: If an error occurs during frame extraction.
        """

        try:
            raw_frames = self._frame_extractor.extract(temp_file, frame_selection)
            logger.info("Frames extracted for video ID %s", video.video_id)
            return raw_frames
        except FrameExtractionError as exc:
            self._fail_processing(video, exc)

    def _package_frames(
        self, video: Video, raw_frames: Iterator[RawFrame]
    ) -> FileContent:
        """Package the extracted frames into a zip file.

        Args:
            video (Video): The video entity for which to package frames.
            raw_frames (Iterator[RawFrame]): The extracted raw frames to package.

        Returns:
            FileContent: The content of the packaged frames as a zip file.

        Raises:
            FramePackagingError: If an error occurs during frame packaging.
        """

        try:
            zip_content = self._frame_packager.package(raw_frames)
            logger.info(
                "Frames packaged for video ID %s into zip file at path %s",
                video.video_id,
                zip_content.path,
            )
            return zip_content
        except FramePackagingError as exc:
            self._fail_processing(video, exc)

    def _upload_output_file(self, video: Video, file_content: FileContent) -> None:
        """Upload the processed frames to storage.

        Args:
            video (Video): The video entity being processed.
            file_content (FileContent): The ZIP file content to be uploaded.

        Raises:
            StorageError: If an error occurs during file upload.
        """

        try:
            self._output_storage.upload_file(
                file_content=file_content, destination_path=video.output_path
            )

            logger.info("Video ID %s uploaded to storage", video.video_id)
        except StorageError as e:
            self._fail_processing(video, e)

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
            self._fail_processing(video, e)
        finally:
            self._publish_events(video)

    def _fail_processing(self, video: Video, error: Exception) -> NoReturn:
        """Fail the processing of the video due to an error.

        Args:
            video (Video): The video entity to fail processing.
            error (Exception): The exception that caused the failure.
        """

        err_class = error.__class__.__name__
        err_prefix = f"Video ID {video.video_id} processing failed due to {err_class}"
        video.fail_processing(error_message=f"{err_prefix}: {str(error)}")
        logger.error(err_prefix, exc_info=True)
        self._publish_events(video)
        raise error

    def _delete_temp_file(self, temp_file: TempFile) -> None:
        """Delete the temporary file.

        Args:
            temp_file (TempFile): The temporary file to delete.

        Raises:
            TempFileManagerError: If an error occurs during temp file deletion.
        """

        try:
            self._temp_file_manager.delete(temp_file)
            logger.info("Temporary file at path %s deleted", temp_file.path)
        except TempFileManagerError as exc:
            logger.warning(
                "Failed to delete temporary file at path %s due to %s",
                temp_file.path,
                exc.__class__.__name__,
                exc_info=True,
            )
