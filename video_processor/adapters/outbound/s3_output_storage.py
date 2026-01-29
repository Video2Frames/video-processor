"""S3 Output Storage Adapter"""

from boto3 import Session
from boto3.exceptions import Boto3Error

from video_processor.domain.exceptions import StorageError
from video_processor.domain.ports import OutputStorage
from video_processor.domain.value_objects import FileContent
from video_processor.infrastructure.config import S3OutputStorageSettings


class S3OutputStorage(OutputStorage):
    """S3OutputStorage is an implementation of the OutputStorage port that
    interacts with S3 storage.
    """

    def __init__(self, boto_session: Session, settings: S3OutputStorageSettings):
        self._bucket_name = settings.BUCKET_NAME
        self._s3_client = boto_session.client("s3")

    def upload_file(self, file_content: FileContent, destination_path: str) -> None:
        try:
            self._s3_client.put_object(
                Bucket=self._bucket_name,
                Key=destination_path,
                Body=file_content.content,
            )
        except Boto3Error as e:
            raise StorageError(f"Failed to upload file to S3: {e}") from e
