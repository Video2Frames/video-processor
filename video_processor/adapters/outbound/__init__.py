"""Outbound adapters package"""

from .local_input_storage import LocalInputStorage
from .local_output_storage import LocalOutputStorage
from .opencv_frame_processor import OpenCVFrameProcessor
from .print_event_publisher import PrintEventPublisher

__all__ = [
    "LocalInputStorage",
    "LocalOutputStorage",
    "PrintEventPublisher",
    "OpenCVFrameProcessor",
]
