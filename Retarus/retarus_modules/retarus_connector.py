import os
import queue
import time

from sekoia_automation.connector import Connector, DefaultConnectorConfiguration

from retarus_modules.retarus_events_consumer import RetarusEventsConsumer
from retarus_modules.retarus_events_forwarder import RetararusEventsForwarder


class RetarusConfig(DefaultConnectorConfiguration):
    kafka_url: str
    kafka_topic: str
    ws_url: str
    ws_key: str


class RetarusConnector(Connector):
    configuration: RetarusConfig

    def run(self):  # pragma: no cover
        self.log(message="Retarus Events Trigger has started", level="info")

        # create the events queue
        events_queue_size = int(os.environ.get("QUEUE_SIZE", 10000))
        events_queue: queue.SimpleQueue = queue.SimpleQueue(maxsize=events_queue_size)

        # start the consumer
        consumer = RetarusEventsConsumer(self, events_queue)
        consumer.start()

        # start the event forwarder
        forwarder = RetararusEventsForwarder(self, events_queue)
        forwarder.start()

        while self.running:
            # Wait 5 seconds for the next supervision
            time.sleep(5)

            # if the read queue thread is down, we spawn a new one
            if not forwarder.is_alive() and forwarder.is_running:
                self.log(message="Restart event forwarder", level="warning")
                forwarder = RetararusEventsForwarder(self, events_queue)
                forwarder.start()

            # if the consumer is dead, we spawn a new one
            if not consumer.is_alive() and consumer.is_running:
                self.log(message="Restart event consumer", level="warning")
                consumer = RetarusEventsConsumer(self, events_queue)
                consumer.start()

        # Stop the consumer
        if consumer.is_alive():
            consumer.stop()
            consumer.join(timeout=2)

        # Stop the forwarder
        if forwarder.is_alive():
            forwarder.stop()
            forwarder.join(timeout=5)

        # Stop the connector executor
        self._executor.shutdown(wait=True)
