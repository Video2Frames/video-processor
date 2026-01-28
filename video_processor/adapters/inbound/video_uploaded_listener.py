"""Module for handling inbound video upload events."""

import json
import logging
from uuid import UUID

from boto3 import Session
from botocore.exceptions import ClientError as BotoCoreClientError
from pydantic import BaseModel

from video_processor.application.commands import ProcessVideoCommand
from video_processor.application.use_cases import ProcessVideoUseCase
from video_processor.infrastructure.config import VideoUploadedListenerSettings

logger = logging.getLogger(__name__)


class VideoUploadedEvent(BaseModel):
    """Event representing a video upload."""

    video_id: UUID
    upload_path: str


class VideoUploadedListener:
    """Listener for video uploaded events."""

    def __init__(
        self,
        boto_session: Session,
        use_case: ProcessVideoUseCase,
        settings: VideoUploadedListenerSettings,
    ):
        self._use_case = use_case
        self._boto_session = boto_session
        self._queue_name = settings.QUEUE_NAME
        self._wait_time = settings.WAIT_TIME_SECONDS
        self._visibility_timeout = settings.VISIBILITY_TIMEOUT_SECONDS
        self._max_messages = settings.MAX_NUMBER_OF_MESSAGES_PER_BATCH

    def listen(self, shutdown_event=None) -> None:
        """Listen for video uploaded events and process them."""

        sqs_resource = self._boto_session.resource("sqs")
        queue = sqs_resource.get_queue_by_name(QueueName=self._queue_name)
        while True:
            if shutdown_event and shutdown_event.shutdown:
                logger.info("Shutdown requested, stopping listener")
                break

            messages = self._consume(queue=queue)
            if not messages:
                logger.debug("No messages received in %d seconds", self._wait_time)
                continue

    def _consume(self, queue):
        try:
            messages = queue.receive_messages(
                MessageAttributeNames=["All"],
                MaxNumberOfMessages=self._max_messages,
                WaitTimeSeconds=self._wait_time,
                VisibilityTimeout=self._visibility_timeout,
            )

        except BotoCoreClientError as error:
            logger.error(
                "Couldn't receive messages from queue: %s", queue, exc_info=True
            )

            raise error

        for message in messages:
            self._handle_message(message)

        return messages

    def _handle_message(self, message) -> None:
        """Handle a video uploaded message.

        Args:
            message: The SQS message containing the video uploaded event data.
        """

        try:
            body = message.body
            body_dict = json.loads(body)
            video_uploaded_event = VideoUploadedEvent.model_validate_json(
                body_dict["Message"]
            )

            command = ProcessVideoCommand(
                video_id=video_uploaded_event.video_id,
                upload_path=video_uploaded_event.upload_path,
            )

            self._use_case.execute(command)
            message.delete()
            logger.info("Processed and deleted message ID: %s", message.message_id)

        except Exception:  # pylint: disable=W0718
            logger.error(
                "Failed to process message ID: %s",
                message.message_id,
                exc_info=True,
            )

            message.delete()
            logger.warning(
                "Deleted message ID: %s to avoid retries", message.message_id
            )
