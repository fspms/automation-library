from office365_connector.consumer import get_o365_pull_contents_cache, get_office365_events
from office365_connector.utils import Office365IntakeSetting

from sekoia.webapi.sqlalchemy import db

from sic.helpers.o365.azure import Office365API
from sic.helpers.o365.errors import FailedToActivateO365Subscription
from sic.models.intake_setting_model import Office365IntakeSetting
from sic.workers import celery
import time
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
from sic.helpers.o365.errors import FailedToActivateO365Subscription
from sic.models.intake_setting_model import Office365IntakeSetting
from sic.settings import SICConfig
from sic.workers import celery
from sic.workers.base import BaseTask
from sic.workers.intakes.metrics import FORWARD_EVENTS_DURATION, OUTCOMING_EVENTS

def office365_activate_subscriptions(self, setting_uuid: str):
    content_types = set(celery.app.config["OFFICE365_SUBSCRIPTIONS_CONTENT_TYPES"].split(","))

    setting = (
        db.session.query(Office365IntakeSetting)
        .options(db.joinedload(Office365IntakeSetting.intake))
        .get(setting_uuid)
    )

    # initialize the client
    client = Office365API(
        client_id=celery.app.config["OFFICE365_CLIENT_ID"],
        client_secret=celery.app.config["OFFICE365_CLIENT_SECRET"],
        tenant_id=str(setting.tenant_uuid),
        publisher_id=celery.app.config["OFFICE365_PUBLISHER_ID"],
    )

    already_enabled_types = set(client.list_subscriptions())
    missing_types = content_types - already_enabled_types

    enabled_types = []
    # Activate missing types
    for content_type in missing_types:
        try:
            client.activate_subscription(content_type)
            enabled_types.append(content_type)
        except FailedToActivateO365Subscription as exp:
            self._logger.warning(
                "Failed to activate subscription", tenant_id=setting.tenant_uuid, content_type=content_type, exp=exp
            )

    # If failed at enabling at least one format, then raise an
    # exception.
    if set(enabled_types) != missing_types:
        raise FailedToActivateO365Subscription()

    setting.validated = True
    db.session.commit()


def office365_pull_contents(setting_uuid: str):
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
