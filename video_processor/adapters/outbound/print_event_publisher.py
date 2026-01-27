"""An outbound adapter that implements the EventPublisher port by printing events to
the console."""

from video_processor.domain.ports import DomainEventT, EventPublisher


class PrintEventPublisher(EventPublisher):
    """An implementation of the EventPublisher port that prints events to the
    console."""

    def publish(self, event: DomainEventT) -> None:
        """Publish a domain event by printing it to the console.

        Args:
            event: The domain event to be published.
        """
        print(f"Event published: {event.model_dump_json()}")
