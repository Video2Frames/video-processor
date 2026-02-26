"""Tests for the S3OutputStorage class"""

import pytest
from botocore.errorfactory import ClientError
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import S3OutputStorage
from video_processor.domain.exceptions import StorageError
from video_processor.domain.value_objects import FileContent


def test_should_upload_file_to_s3(mocker: MockerFixture):
    """Given a valid file content and path
    When uploading a file using S3OutputStorage
    Then it should upload the file to S3 without errors
    """

    # Given
    file_path = "test/path/file.txt"
    file_content_bytes = b"file-content"
    bucket_name = "test-bucket"
    mock_s3_client = mocker.Mock()
    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_s3_client
    settings = mocker.Mock()
    settings.BUCKET_NAME = bucket_name
    storage = S3OutputStorage(boto_session=boto_session, settings=settings)
    file_content = FileContent(path=file_path, content=file_content_bytes)

    # When
    storage.upload_file(file_content=file_content, destination_path=file_path)

    # Then
    boto_session.client.assert_called_once_with("s3")
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=file_path,
        Body=file_content_bytes,
    )


def test_should_raise_error_on_upload_failure(mocker: MockerFixture):
    """Given a valid file content and path
    When an error occurs during file upload using S3OutputStorage
    Then it should raise a StorageError with an appropriate message
    """

    # Given
    file_path = "test/path/file.txt"
    file_content_bytes = b"file-content"
    bucket_name = "test-bucket"
    mock_s3_client = mocker.Mock()
    mock_s3_client.put_object.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "Access Denied",
            }
        },
        operation_name="PutObject",
    )

    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_s3_client
    settings = mocker.Mock()
    settings.BUCKET_NAME = bucket_name
    storage = S3OutputStorage(boto_session=boto_session, settings=settings)
    file_content = FileContent(path=file_path, content=file_content_bytes)

    # When / Then
    with pytest.raises(StorageError) as exc_info:
        storage.upload_file(file_content=file_content, destination_path=file_path)

    assert "Failed to upload file to S3" in str(exc_info.value)
    assert "Access Denied" in str(exc_info.value)
    boto_session.client.assert_called_once_with("s3")
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=file_path,
        Body=file_content_bytes,
    )
