from video_processor.domain.exceptions import FrameSelectionError
from video_processor.domain.ports import FrameSelector
from video_processor.domain.value_objects import FrameSelection, VideoMetadata
from video_processor.infrastructure.config import UniformFrameSelectorSettings


class UniformFrameSelector(FrameSelector):
    """A frame selector that selects frames uniformly across the video duration"""

    def __init__(self, settings: UniformFrameSelectorSettings):
        self.percentage_threshold = settings.PERCENTAGE_THRESHOLD

    def select(self, metadata: VideoMetadata) -> FrameSelection:
        if self.percentage_threshold <= 0 or self.percentage_threshold > 1:
            raise FrameSelectionError("percentage_threshold must be between 0 and 1")

        total_frames = metadata.frame_count
        if total_frames == 0:
            raise FrameSelectionError("Video has no frames to select")

        desired_count = max(1, int(total_frames * self.percentage_threshold))
        # If the desired count is 1, we can just select the first frame to
        # avoid division by zero in the calculation of indexes
        if desired_count == 1:
            return FrameSelection(indexes=[0])

        indexes = [
            int(i * (total_frames - 1) / (desired_count - 1))
            for i in range(desired_count)
        ]

        return FrameSelection(indexes=indexes)
