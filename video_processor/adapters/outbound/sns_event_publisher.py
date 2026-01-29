"""An outbound adapter that implements the EventPublisher port by publishing events
to an AWS SNS topic."""

import uuid

from boto3 import Session
from boto3.exceptions import Boto3Error

from video_processor.domain.exceptions import EventPublishingError
from video_processor.domain.ports import DomainEventT, EventPublisher
from video_processor.infrastructure.config import SnsEventPublisherSettings


class SnsEventPublisher(EventPublisher):
    """An implementation of the EventPublisher port that publishes events to
    an AWS SNS topic."""

    def __init__(self, boto_session: Session, settings: SnsEventPublisherSettings):
        self._topic_arn = settings.TOPIC_ARN
        self._group_id = settings.GROUP_ID
        self._sns_client = boto_session.client("sns")

    def publish(self, event: DomainEventT) -> None:
        try:
            dedup_id = uuid.uuid4()
            message = event.model_dump_json()
            self._sns_client.publish(
                TopicArn=self._topic_arn,
                Message=message,
                MessageGroupId=self._group_id,
                MessageDeduplicationId=str(dedup_id),
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": event.get_event_type(),
                    }
                },
            )
        except Boto3Error as e:
            raise EventPublishingError(f"Failed to publish event to SNS: {e}") from e
