"""Tests for the VideoUploadedListener class"""

import json
import uuid

import pytest
from botocore.exceptions import ClientError as BotoCoreClientError
from pytest_mock import MockerFixture

from video_processor.adapters.inbound.video_uploaded_listener import (
    VideoUploadedListener,
)


def test_should_process_and_delete_message_on_success(mocker: MockerFixture):
    """Given a valid SQS message containing a VideoUploadedEvent
    When the listener consumes the message
    Then it should call the use case with a ProcessVideoCommand and delete the message
    """

    # Given
    settings = mocker.Mock()
    settings.QUEUE_NAME = "test-queue"
    settings.WAIT_TIME_SECONDS = 1
    settings.VISIBILITY_TIMEOUT_SECONDS = 5
    settings.MAX_NUMBER_OF_MESSAGES_PER_BATCH = 1
    use_case = mocker.Mock()
    boto_session = mocker.Mock()
    listener = VideoUploadedListener(boto_session, use_case, settings)
    video_id = uuid.uuid4()
    upload_path = "s3://bucket/key.mp4"
    inner_message = json.dumps({"video_id": str(video_id), "upload_path": upload_path})
    body = json.dumps({"Message": inner_message})
    message = mocker.Mock()
    message.body = body
    message.message_id = "msg-1"
    message.delete = mocker.Mock()
    queue = mocker.Mock()
    queue.receive_messages.return_value = [message]

    # When
    messages = listener._consume(queue)

    # Then
    assert messages == [message]
    assert use_case.execute.call_count == 1
    cmd = use_case.execute.call_args[0][0]
    assert str(cmd.video_id) == str(video_id)
    assert cmd.upload_path == upload_path
    message.delete.assert_called_once()


def test_should_raise_when_receive_messages_throws_boto_error(mocker: MockerFixture):
    """Given the SQS client raises a boto ClientError when receiving messages
    When the listener attempts to consume messages
    Then it should propagate the BotoCoreClientError
    """

    # Given
    settings = mocker.Mock()
    settings.QUEUE_NAME = "test-queue"
    settings.WAIT_TIME_SECONDS = 1
    settings.VISIBILITY_TIMEOUT_SECONDS = 5
    settings.MAX_NUMBER_OF_MESSAGES_PER_BATCH = 1
    use_case = mocker.Mock()
    boto_session = mocker.Mock()
    listener = VideoUploadedListener(boto_session, use_case, settings)
    queue = mocker.Mock()
    error = BotoCoreClientError({"Error": {}}, "ReceiveMessage")
    queue.receive_messages.side_effect = error

    # When / Then
    with pytest.raises(BotoCoreClientError):
        listener._consume(queue)


def test_should_delete_message_when_processing_raises_exception(mocker: MockerFixture):
    """Given a valid SQS message but the use case raises an exception
    When the listener processes the message
    Then it should still delete the message to avoid retries
    """

    # Given
    settings = mocker.Mock()
    settings.QUEUE_NAME = "test-queue"
    settings.WAIT_TIME_SECONDS = 1
    settings.VISIBILITY_TIMEOUT_SECONDS = 5
    settings.MAX_NUMBER_OF_MESSAGES_PER_BATCH = 1
    use_case = mocker.Mock()
    use_case.execute.side_effect = Exception("processing failed")
    boto_session = mocker.Mock()
    listener = VideoUploadedListener(boto_session, use_case, settings)
    video_id = uuid.uuid4()
    upload_path = "s3://bucket/key.mp4"
    inner_message = json.dumps({"video_id": str(video_id), "upload_path": upload_path})
    body = json.dumps({"Message": inner_message})
    message = mocker.Mock()
    message.body = body
    message.message_id = "msg-2"
    message.delete = mocker.Mock()
    queue = mocker.Mock()
    queue.receive_messages.return_value = [message]

    # When
    messages = listener._consume(queue)

    # Then: _handle_message swallows exceptions, so _consume should return normally
    assert messages == [message]
    assert use_case.execute.call_count == 1
    message.delete.assert_called_once()
