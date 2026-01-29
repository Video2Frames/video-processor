"""Outbound adapters package"""

from .local_input_storage import LocalInputStorage
from .local_output_storage import LocalOutputStorage
from .opencv_frame_processor import OpenCVFrameProcessor
from .print_event_publisher import PrintEventPublisher
from .s3_input_storage import S3InputStorage
from .s3_output_storage import S3OutputStorage
from .sns_event_publisher import SnsEventPublisher

__all__ = [
    "LocalInputStorage",
    "LocalOutputStorage",
    "S3InputStorage",
    "S3OutputStorage",
    "PrintEventPublisher",
    "SnsEventPublisher",
    "OpenCVFrameProcessor",
]
