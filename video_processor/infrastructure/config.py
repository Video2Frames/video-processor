"""Application configuration module"""

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_PATH = "config/video_processor.env"
ENV_FILE_ENCODING = "utf-8"


class AWSSettings(BaseSettings):
    """AWS integration settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="AWS_",
        extra="ignore",
    )

    REGION_NAME: str = "us-east-1"
    ACCOUNT_ID: str
    ACCESS_KEY_ID: str
    SECRET_ACCESS_KEY: str


class VideoUploadedListenerSettings(BaseSettings):
    """Video uploaded listener settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="VIDEO_UPLOADED_LISTENER_",
        extra="ignore",
    )

    QUEUE_NAME: str = "video_processing"
    WAIT_TIME_SECONDS: int = 20
    MAX_NUMBER_OF_MESSAGES_PER_BATCH: int = 1
    VISIBILITY_TIMEOUT_SECONDS: int = 300


class LocalInputStorageSettings(BaseSettings):
    """Local input storage settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="LOCAL_INPUT_STORAGE_",
        extra="ignore",
    )

    BASE_PATH: str = "local_storage/input"


class LocalOutputStorageSettings(BaseSettings):
    """Local output storage settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="LOCAL_OUTPUT_STORAGE_",
        extra="ignore",
    )

    BASE_PATH: str = "local_storage/output"


class S3InputStorageSettings(BaseSettings):
    """S3 input storage settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="S3_INPUT_STORAGE_",
        extra="ignore",
    )

    BUCKET_NAME: str


class S3OutputStorageSettings(BaseSettings):
    """S3 output storage settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="S3_OUTPUT_STORAGE_",
        extra="ignore",
    )

    BUCKET_NAME: str


class SnsEventPublisherSettings(BaseSettings):
    """SNS event publisher settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="SNS_EVENT_PUBLISHER_",
        extra="ignore",
    )

    TOPIC_ARN: str
    GROUP_ID: str = "videos"


class UniformFrameSelectorSettings(BaseSettings):
    """Uniform frame selector settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="UNIFORM_FRAME_SELECTOR_",
        extra="ignore",
    )

    PORCENTAGE_THRESHOLD: float = 0.01


class VideoValidatorsSettings(BaseSettings):
    """Video validators settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding=ENV_FILE_ENCODING,
        env_prefix="VIDEO_VALIDATORS_",
        extra="ignore",
    )

    MAX_SIZE_IN_BYTES: int = 250 * 1024 * 1024  # 250 MB limit
