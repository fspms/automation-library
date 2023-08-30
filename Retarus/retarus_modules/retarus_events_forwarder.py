import uuid
from datetime import datetime, timezone
from queue import Empty, SimpleQueue
from threading import Event, Thread

import dateutil.parser
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError
from sekoia_automation.connector import Connector

from retarus_modules.metrics import OUTCOMING_EVENTS


class RetararusEventsForwarder(Thread):
    """Handler for sending events to the Kafka topic"""

    def __init__(
        self,
        connector: Connector,
        queue: SimpleQueue,
        queue_get_limit: int = 10,
        queue_get_timeout: float = 0.1,
        queue_get_block: bool = True,
        queue_get_retries: int = 10,
    ):
        super().__init__()
        self.connector = connector
        self.configuration = self.connector.configuration
        self.kafka_producer = KafkaProducer(bootstrap_servers=self.configuration.kafka_url)
        self.queue = queue

        # Event used to stop the thread
        self._stop_event = Event()

        # Arguments for the polling of events from the queue
        self.queue_get_limit = queue_get_limit
        self.queue_get_timeout = queue_get_timeout
        self.queue_get_block = queue_get_block
        self.queue_get_retries = queue_get_retries

    @property
    def is_running(self) -> bool:
        """Helper method to check if the stop event has been set

        Returns:
            bool: False if _stop_event is set, True otherwise
        """
        return not self._stop_event.is_set()

    def stop(self):
        """Sets the stop event"""
        self._stop_event.set()

    def send_messages(self, *messages: dict[str, str]):
        """Send one or several messages to Kafka

        Args:
            messages (dict[str, str]): List of messages to send to Kafka
        """
        try:
            for message in messages:
                stub = {
                    "@timestamp": dateutil.parser.parse(message["ts"]).isoformat(),
                    "customer": {"intake_key": self.configuration.intake_key},
                    "message": message,
                    "event": {
                        "id": str(uuid.uuid4()),
                        "created": datetime.now(timezone.utc).isoformat(),
                        "outcome": "failure",
                    },
                }
                self.kafka_producer.send(
                    topic=self.configuration.kafka_topic,
                    value=stub,
                )
            self.kafka_producer.flush()
        except KafkaTimeoutError as ex:
            self.connector.log_exception(ex, message="Error sending the log to Kafka")

    def run(self):
        """Fetches events from the queue, then sends them to Kafka, as long as stop event is unset"""
        while self.is_running:
            try:
                events = self._queue_get_batch()
                if len(events) > 0:
                    self.connector.log(
                        message="Forward an event to the intake",
                        level="info",
                    )
                    OUTCOMING_EVENTS.labels(intake_key=self.configuration.intake_key).inc()
                    self.send_messages(*events)
            except Exception as ex:
                self.connector.log_exception(ex, message="Failed to forward event")

    def _queue_get_batch(self) -> list[dict[str, str]]:
        """Gets a batch of events from the queue

        Several parameters for these batches can be set when initializing the class:
        * queue_get_limit is the max number of messages we want to get for a match
        * queue_get_retries is the max number of retries (empty queue exception) we accept for a given batch
        * queue_get_block is the block parameter of queue.get
        * queue_get_timeout is the timeout parameter of queue.get

        Returns:
            list[dict[str, str]]: Events we got from the queue
        """
        result: list[dict] = []
        i: int = 0
        while len(result) < self.queue_get_limit and i < self.queue_get_retries:
            try:
                result.append(self.queue.get(block=self.queue_get_block, timeout=self.queue_get_timeout))
            except Empty:
                i += 1
                self.connector.log(message="Empty queue", level="DEBUG")
                continue
        return result
