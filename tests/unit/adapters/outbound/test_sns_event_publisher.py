"""Tests for the SnsEventPublisher class"""

from datetime import datetime
from uuid import UUID

import pytest
from botocore.errorfactory import ClientError
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import SnsEventPublisher
from video_processor.domain.events import VideoProcessingStartedEvent
from video_processor.domain.exceptions import EventPublishingError


def test_should_publish_event_to_sns(mocker: MockerFixture):
    """Given a valid DomainEvent
    When publishing the event using SnsEventPublisher
    Then it should call the SNS client's publish method with the correct parameters
    """

    # Given
    event_id = UUID("12345678-1234-5678-1234-567812345678")
    mock_sns_client = mocker.Mock()
    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_sns_client
    settings = mocker.Mock()
    settings.TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:my-topic"
    settings.GROUP_ID = "my-group"
    publisher = SnsEventPublisher(boto_session=boto_session, settings=settings)
    event = VideoProcessingStartedEvent(
        id=event_id,
        version=1,
        video_id=UUID("12345678-1234-5678-1234-567812345678"),
        processing_started_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    # When
    publisher.publish(event)

    # Then
    boto_session.client.assert_called_once_with("sns")
    mock_sns_client.publish.assert_called_once_with(
        TopicArn=settings.TOPIC_ARN,
        Message=event.model_dump_json(),
        MessageGroupId=settings.GROUP_ID,
        MessageDeduplicationId=mocker.ANY,
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": event.get_event_type(),
            }
        },
    )


def test_should_raise_error_on_publish_failure(mocker: MockerFixture):
    """Given a valid DomainEvent
    When an error occurs during publishing using SnsEventPublisher
    Then it should raise an EventPublishingError with an appropriate message
    """

    # Given
    mock_sns_client = mocker.Mock()
    mock_sns_client.publish.side_effect = ClientError(
        error_response={
            "Error": {"Code": "InternalError", "Message": "An internal error occurred"}
        },
        operation_name="Publish",
    )
    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_sns_client
    settings = mocker.Mock()
    settings.TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:my-topic"
    settings.GROUP_ID = "my-group"
    publisher = SnsEventPublisher(boto_session=boto_session, settings=settings)
    event = VideoProcessingStartedEvent(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        version=1,
        video_id=UUID("12345678-1234-5678-1234-567812345678"),
        processing_started_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    # When / Then
    with pytest.raises(EventPublishingError) as exc_info:
        publisher.publish(event)

    assert "Failed to publish event to SNS" in str(exc_info.value)
