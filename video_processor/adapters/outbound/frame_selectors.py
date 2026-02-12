from video_processor.domain.exceptions import FrameSelectionError
from video_processor.domain.ports import FrameSelector
from video_processor.domain.value_objects import FrameSelection, VideoMetadata
from video_processor.infrastructure.config import UniformFrameSelectorSettings


class UniformFrameSelector(FrameSelector):
    """A frame selector that selects frames uniformly across the video duration"""

    def __init__(self, settings: UniformFrameSelectorSettings):
        self.porcentage_threshold = settings.PORCENTAGE_THRESHOLD

    def select(self, metadata: VideoMetadata) -> FrameSelection:
        if self.porcentage_threshold <= 0 or self.porcentage_threshold > 1:
            raise FrameSelectionError("porcentage_threshold must be between 0 and 1")

        total_frames = metadata.frame_count
        if total_frames == 0:
            raise FrameSelectionError("Video has no frames to select")

        step = max(1, int(1 / self.porcentage_threshold))
        selected_frames = list(range(0, total_frames, step))
        return FrameSelection(indexes=selected_frames)
