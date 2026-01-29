"""Video uploaded event listener entrypoint module"""

import logging
import signal

from boto3 import Session

from video_processor.adapters.inbound import VideoUploadedListener
from video_processor.adapters.outbound import (
    OpenCVFrameProcessor,
    S3InputStorage,
    S3OutputStorage,
    SnsEventPublisher,
)
from video_processor.application.use_cases import ProcessVideoUseCase
from video_processor.infrastructure.config import (
    AWSSettings,
    FrameProcessorSettings,
    S3InputStorageSettings,
    S3OutputStorageSettings,
    SnsEventPublisherSettings,
    VideoUploadedListenerSettings,
)

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handles graceful shutdown on SIGTERM and SIGINT signals"""

    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGTERM, self._exit_gracefully)
        signal.signal(signal.SIGINT, self._exit_gracefully)

    def _exit_gracefully(self, signum, frame):
        logger.info("Received shutdown signal %d", signum)
        self.shutdown = True


def main():
    """Run the video uploaded event listener"""

    aws_settings = AWSSettings()
    video_uploaded_listener_settings = VideoUploadedListenerSettings()
    # input_storage_settings = LocalInputStorageSettings()
    # output_storage_settings = LocalOutputStorageSettings()
    input_storage_settings = S3InputStorageSettings()
    output_storage_settings = S3OutputStorageSettings()
    frame_processor_settings = FrameProcessorSettings()
    event_publisher_settings = SnsEventPublisherSettings()
    shutdown_handler = GracefulShutdown()
    frame_processor = OpenCVFrameProcessor(settings=frame_processor_settings)
    boto_session = Session(
        aws_access_key_id=aws_settings.ACCESS_KEY_ID,
        aws_secret_access_key=aws_settings.SECRET_ACCESS_KEY,
        region_name=aws_settings.REGION_NAME,
        aws_account_id=aws_settings.ACCOUNT_ID,
    )

    # event_publisher = PrintEventPublisher()
    event_publisher = SnsEventPublisher(
        boto_session=boto_session, settings=event_publisher_settings
    )

    # input_storage = LocalInputStorage(settings=input_storage_settings)
    # output_storage = LocalOutputStorage(settings=output_storage_settings)
    input_storage = S3InputStorage(
        boto_session=boto_session, settings=input_storage_settings
    )

    output_storage = S3OutputStorage(
        boto_session=boto_session, settings=output_storage_settings
    )

    process_video_use_case = ProcessVideoUseCase(
        input_storage=input_storage,
        output_storage=output_storage,
        frame_processor=frame_processor,
        event_publisher=event_publisher,
    )

    listener = VideoUploadedListener(
        boto_session=boto_session,
        use_case=process_video_use_case,
        settings=video_uploaded_listener_settings,
    )

    listener.listen(shutdown_event=shutdown_handler)


if __name__ == "__main__":
    import logging.config

    logging.config.fileConfig("logging.ini", disable_existing_loggers=False)
    main()
