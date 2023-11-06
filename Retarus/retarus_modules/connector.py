import json
import os
import queue
import time

import uuid
from datetime import datetime, timezone
from pathlib import Path

import dateutil.parser

from retarus_modules.configuration import RetarusConfig
from retarus_modules.metrics import OUTGOING_EVENTS
from sekoia_automation.connector import Connector

from retarus_modules.consumer import RetarusEventsConsumer


class RetarusConnector(Connector):
    configuration: RetarusConfig

    def __init__(
        self,
        data_path: Path | None = None,
        queue_get_limit: int = 10,
        queue_get_timeout: float = 0.1,
        queue_get_block: bool = True,
        queue_get_retries: int = 10,
    ):
        super().__init__(data_path=data_path)
        # create the events queue
        self.events_queue: queue.Queue = queue.Queue(maxsize=int(os.environ.get("QUEUE_SIZE", 10000)))

        # Arguments for the polling of events from the queue
        self.queue_get_limit = queue_get_limit
        self.queue_get_timeout = queue_get_timeout
        self.queue_get_block = queue_get_block
        self.queue_get_retries = queue_get_retries

    def run(self):  # pragma: no cover
        self.log(message="Retarus Events Trigger has started", level="info")

        # start the consumer
        consumer = RetarusEventsConsumer(self.configuration, self.events_queue, self.log, self.log_exception)
        consumer.start()

        while self.running:
            # Wait 5 seconds for the next supervision
            time.sleep(5)

            # if the consumer is dead, we spawn a new one
            if not consumer.is_alive() and consumer.is_running:
                self.log(message="Restart event consumer", level="warning")
                consumer = RetarusEventsConsumer(self.configuration, self.events_queue, self.log, self.log_exception)
                consumer.start()

            # Send events to Symphony
            events = self._queue_get_batch()
            if len(events) > 0:
                self.log(
                    message="Forward an event to the intake",
                    level="info",
                )
                OUTGOING_EVENTS.labels(intake_key=self.configuration.intake_key).inc()
                self.forward_messages(*events)

        # Stop the consumer
        if consumer.is_alive():
            consumer.stop()
            consumer.join(timeout=2)

        # Stop the connector executor
        self._executor.shutdown(wait=True)

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
                result.append(self.events_queue.get(block=self.queue_get_block, timeout=self.queue_get_timeout))
            except queue.Empty:
                i += 1
                self.log(message="Empty queue", level="DEBUG")
                continue
        return result

    def forward_messages(self, *messages: dict[str, str]):
        """Send one or several messages to Symphony

        Args:
            messages (dict[str, str]): List of messages to send to Symphony
        """
        # TODO: change this, no need for creating stubs, forward events can take the messages as is 
        # Just need to dump to string 
        raise NotImplementedError
        stubs = []
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
            stubs.append(json.dumps(stub))
        self.push_events_to_intakes(stubs)
