"""Tests for the S3InputStorage class"""

import pytest
from botocore.errorfactory import ClientError
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import S3InputStorage
from video_processor.domain.exceptions import StorageError
from video_processor.domain.value_objects import FileContent


def test_should_download_file_from_s3(mocker: MockerFixture):
    """Given a valid source path
    When downloading a file using S3InputStorage
    Then it should return a FileContent object with the path and content of the file
    """

    # Given
    file_path = "test/path/file.txt"
    file_content = b"file-content"
    bucket_name = "test-bucket"
    mock_s3_client = mocker.Mock()
    mock_s3_client.get_object.return_value = {
        "Body": mocker.Mock(read=mocker.Mock(return_value=file_content))
    }

    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_s3_client
    settings = mocker.Mock()
    settings.BUCKET_NAME = bucket_name
    storage = S3InputStorage(boto_session=boto_session, settings=settings)

    # When
    result = storage.download_file(file_path)

    # Then
    assert isinstance(result, FileContent)
    assert result.path == file_path
    assert result.content == file_content
    boto_session.client.assert_called_once_with("s3")
    mock_s3_client.get_object.assert_called_once_with(Bucket=bucket_name, Key=file_path)


def test_should_raise_error_on_download_failure(mocker: MockerFixture):
    """Given a valid source path
    When an error occurs during file download using S3InputStorage
    Then it should raise a StorageError with an appropriate message
    """

    # Given
    file_path = "test/path/file.txt"
    bucket_name = "test-bucket"
    mock_s3_client = mocker.Mock()
    mock_s3_client.get_object.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "NoSuchKey",
                "Message": "The specified key does not exist.",
            }
        },
        operation_name="GetObject",
    )

    boto_session = mocker.Mock()
    boto_session.client.return_value = mock_s3_client
    settings = mocker.Mock()
    settings.BUCKET_NAME = bucket_name
    storage = S3InputStorage(boto_session=boto_session, settings=settings)

    # When / Then
    with pytest.raises(StorageError) as exc_info:
        storage.download_file(file_path)

    expected_str = (
        "Failed to download file from S3: An error occurred (NoSuchKey) when calling "
        "the GetObject operation: The specified key does not exist."
    )

    assert str(exc_info.value) == expected_str
    boto_session.client.assert_called_once_with("s3")
    mock_s3_client.get_object.assert_called_once_with(Bucket=bucket_name, Key=file_path)
