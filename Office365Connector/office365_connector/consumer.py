import time
from office365_connector.utils import Office365IntakeSetting
from collections.abc import Iterator
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import orjson
from dateutil.parser import isoparse
from sekoia.common.kafka.producer import ConfluentProducer
from sekoia.webapi.sqlalchemy import db

from sic.helpers.cache import get_cache
from sic.helpers.ecs import generate_ecs_stub_dict
from sic.helpers.o365.azure import Office365API
from sic.models.intake_setting_model import Office365IntakeSetting
from sic.settings import SICConfig
from sic.workers import celery
from sic.workers.intakes.metrics import FORWARD_EVENTS_DURATION, OUTCOMING_EVENTS


@lru_cache
def get_o365_pull_contents_cache():
    cache_o365_pulled_contents = get_cache("o365_pulled_contents")
    return cache_o365_pulled_contents


def office365_pull_contents(self, setting_uuid: str):
    """Retrieve Office365 events via Microsoft APIs.

    For the given O365 intake, this task will retrieve all
    subscriptions from Microsoft and for each subscription, it will
    ask for the last content. Each content is a data stored on a blob
    storage which contains multiple events.

    This task is tracking the last date of pull to avoid asking
    Microsoft to return all events each time. If this task is first
    run for an intake key, retrieve events from the last 3 hours.

    Redis is also used to track each event individally to avoid
    duplication (we have already seen duplicate events in the same
    blob and in multiple blobs too).

    """
    start_time = time.time()

    setting = (
        db.session.query(Office365IntakeSetting)
        .options(db.joinedload(Office365IntakeSetting.intake))
        .get(setting_uuid)
    )
    intake_key = str(setting.intake.intake_key)
    tenant_uuid = str(setting.tenant_uuid)

    # No need to keep the SQL transaction openned.
    db.session.close()

    kafka_producer = ConfluentProducer(SICConfig.KAFKA_EVENTS_OUTPUT_TOPIC)
    cache_client = get_o365_pull_contents_cache().client

    # The default is to retrieve events for the last 3 hours if this
    # is the first execution.
    last_pull_date = cache_client.get(f"o365_{intake_key}_last_pull")
    try:
        start_date = datetime.fromisoformat(last_pull_date)
    except Exception:
        start_date = datetime.utcnow() - timedelta(hours=3)

    for date, event in get_office365_events(tenant_uuid, start_date):
        # We keep track of each event individually.
        event_redis_key = f"o365_pulled_content_{intake_key}_{event['Id']}"
        if cache_client.exists(event_redis_key):
            continue
        cache_client.set(event_redis_key, value=1, ex=6 * 60 * 60)

        kafka_producer.send(
            generate_ecs_stub_dict(
                intake_key=intake_key,
                message=orjson.dumps(event).decode("utf-8"),
                timestamp=isoparse(date),
            )
        )
        OUTCOMING_EVENTS.labels(intake_key=intake_key, datasource="office365").inc()

    kafka_producer.flush()
    FORWARD_EVENTS_DURATION.labels(intake_key=intake_key, datasource="office365").observe(time.time() - start_time)


def get_office365_events(tenant_uuid: str, start_date: datetime) -> Iterator[tuple[str, dict[str, Any]]]:
    # initialize the client
    client = Office365API(
        client_id=celery.app.config["OFFICE365_CLIENT_ID"],
        client_secret=celery.app.config["OFFICE365_CLIENT_SECRET"],
        tenant_id=tenant_uuid,
        publisher_id=celery.app.config["OFFICE365_PUBLISHER_ID"],
    )

    # get the active subscriptions
    content_types = client.list_subscriptions()
    for content_type in content_types:
        # Get the paginated contents from a subscription
        for contents in client.get_subscription_contents(
            content_type, start_time=start_date - timedelta(minutes=10), end_time=datetime.utcnow()
        ):
            for content in contents:
                date = content["contentCreated"]
                events = client.get_content(content["contentUri"])

                for event in events:
                    yield date, event
