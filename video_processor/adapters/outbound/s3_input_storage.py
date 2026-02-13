"""S3 Input Storage Adapter"""

from boto3 import Session
from boto3.exceptions import Boto3Error
from botocore.errorfactory import ClientError

from video_processor.domain.exceptions import StorageError
from video_processor.domain.ports import InputStorage
from video_processor.domain.value_objects import FileContent
from video_processor.infrastructure.config import S3InputStorageSettings


class S3InputStorage(InputStorage):
    """S3InputStorage is an implementation of the InputStorage port that
    interacts with S3 storage.
    """

    def __init__(self, boto_session: Session, settings: S3InputStorageSettings):
        self._bucket_name = settings.BUCKET_NAME
        self._s3_client = boto_session.client("s3")

    def download_file(self, source_path: str) -> FileContent:
        try:
            response = self._s3_client.get_object(
                Bucket=self._bucket_name, Key=source_path
            )
            content = response["Body"].read()
            return FileContent(path=source_path, content=content)
        except (Boto3Error, ClientError) as e:
            raise StorageError(f"Failed to download file from S3: {e}") from e
