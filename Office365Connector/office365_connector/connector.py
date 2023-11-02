import json
from datetime import datetime, timedelta
from functools import lru_cache
from threading import Event, Thread
from time import sleep
import time
from sekoia_automation.connector import Connector
from office365_connector.errors import FailedToActivateO365Subscription
from office365_connector.office365_api import Office365API
from office365_connector.configuration import Office365Configuration
from pathlib import Path

from prometheus_client import Counter, Histogram

EVENTS_CACHE = {}

# Declare prometheus metrics
prom_namespace = "sicconfapi_intakes"

OUTGOING_EVENTS = Counter(
    name="forwarded_events",
    documentation="Number of events forwarded to SEKOIA.IO",
    namespace=prom_namespace,
    labelnames=["datasource", "intake_key"],
)

FORWARD_EVENTS_DURATION = Histogram(
    name="forward_events_duration",
    documentation="Duration to collect and forward events",
    namespace=prom_namespace,
    labelnames=["datasource", "intake_key"],
)


def clear_cache(stop_event: Event):
    while not stop_event.is_set():
        for event_id, insertion_timestamp in EVENTS_CACHE.items():
            if datetime.now() - insertion_timestamp < timedelta(hours=6):
                del EVENTS_CACHE[event_id]
        sleep(600)


class Office365Connector(Connector):
    configuration: Office365Configuration

    def __init__(
        self,
        data_path: Path | None = None,
    ):
        super().__init__(data_path=data_path)
        self.client = Office365API(
            client_id=str(self.configuration.client_id),
            client_secret=self.configuration.client_secret,
            tenant_id=self.configuration.tenant_uuid,
            publisher_id=str(self.configuration.publisher_id),
        )

    def pull_content(self, last_pull_date: datetime) -> list[dict]:
        pulled_events: list[dict] = []

        content_types = self.client.list_subscriptions()
        for content_type in content_types:
            # Get the paginated contents from a subscription
            for contents in self.client.get_subscription_contents(
                content_type, start_time=last_pull_date, end_time=datetime.utcnow()
            ):
                for content in contents:
                    events = self.client.get_content(content["contentUri"])
                    for event in events:
                        pulled_events.append(event)

        return pulled_events

    def forward_events(self, events: list[dict]):
        self.log(f"Pushing {len(events)} event(s) to intake", level="info")
        OUTGOING_EVENTS.labels(intake_key=self.configuration.intake_key, datasource="office365").inc()

        serialized_events: list[str] = [json.dumps(event) for event in events]
        self.push_events_to_intakes(serialized_events)

    def check_for_duplicates(self, events: list[dict]) -> list[dict]:
        deduplicated_events: list[dict] = []
        for event in events:
            if not self._event_in_cache(event["id"]):
                deduplicated_events.append(event)
                EVENTS_CACHE[event["id"]] = datetime.now()
        return deduplicated_events

    @lru_cache
    def _event_in_cache(self, event_id: str) -> bool:
        return event_id in EVENTS_CACHE

    def activate_subscriptions(self):
        already_enabled_types = set(self.client.list_subscriptions())
        missing_types = self.configuration.content_types - already_enabled_types

        enabled_types = []
        # Activate missing types
        for content_type in missing_types:
            try:
                self.client.activate_subscription(content_type)
                enabled_types.append(content_type)
            except FailedToActivateO365Subscription as exp:
                self._logger.warning(
                    "Failed to activate subscription",
                    tenant_id=self.configuration.tenant_uuid,
                    content_type=content_type,
                    exp=exp,
                )

        # If failed at enabling at least one format, then raise an
        # exception.
        if set(enabled_types) != missing_types:
            raise FailedToActivateO365Subscription()

    def run(self):
        stop_event: Event = Event()
        clear_cache_thread = Thread(target=clear_cache, args=(stop_event,))
        clear_cache_thread.start()

        self.activate_subscriptions()

        last_pull_date = datetime.utcnow() - timedelta(hours=3)

        while self.running:
            start_time = time.time()

            events = self.pull_content(last_pull_date)
            deduplicated_events = self.check_for_duplicates(events)
            self.forward_events(deduplicated_events)

            FORWARD_EVENTS_DURATION.labels(intake_key=self.configuration.intake_key, datasource="office365").observe(
                time.time() - start_time
            )

            last_pull_date = datetime.utcnow()
            sleep(60)

        # Stop the connector executor
        stop_event.set()
        clear_cache_thread.join()
        self._executor.shutdown(wait=True)
