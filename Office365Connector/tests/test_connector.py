import json
from datetime import datetime
from time import sleep
from threading import Event, Thread
from unittest import skip
from unittest.mock import patch

from _pytest.python_api import raises
from prometheus_client import Counter

from office365_connector.connector import clear_cache, EVENTS_CACHE
from office365_connector.errors import FailedToActivateO365Subscription


@patch.object(Counter, "inc")
def test_forward_events(mock_prometheus, connector, event):
    connector.forward_events([event])
    connector.log.assert_called_once_with("Pushing 1 event(s) to intake", level="info")
    mock_prometheus.assert_called_once()
    connector.push_events_to_intakes.assert_called_once_with([json.dumps(event)])


def test_check_for_duplicates(connector, event, other_event):
    deduplicated = connector.check_for_duplicates(
        [event, {"id": event["id"], "some_field": "some_value"}, other_event, other_event]
    )
    assert deduplicated == [event, other_event]
    assert list(EVENTS_CACHE.keys()) == [event["id"], other_event["id"]]

    deduplicated = connector.check_for_duplicates([event])
    assert deduplicated == []

    EVENTS_CACHE[event["id"]] = datetime.fromtimestamp(0)
    EVENTS_CACHE[other_event["id"]] = datetime.fromtimestamp(0)

    stop_event: Event = Event()
    clear_cache_thread = Thread(target=clear_cache, args=(stop_event, 1))
    clear_cache_thread.start()
    sleep(2)
    stop_event.set()
    clear_cache_thread.join()

    assert EVENTS_CACHE == {}

    deduplicated = connector.check_for_duplicates([event])
    assert deduplicated == [event]


def test_activate_subscriptions(connector):
    connector.configuration.content_types = {"xml", "json"}
    connector.client.list_subscriptions.return_value = ["json"]

    connector.activate_subscriptions()
    connector.client.list_subscriptions.assert_called_once()
    connector.client.activate_subscription.assert_called_once_with("xml")


def test_activate_subscriptions_fail(connector):
    connector.configuration.content_types = {"xml", "json"}
    connector.client.list_subscriptions.return_value = ["json"]
    connector.client.activate_subscription.side_effect = FailedToActivateO365Subscription()

    with raises(FailedToActivateO365Subscription):
        connector.activate_subscriptions()

    connector.client.list_subscriptions.assert_called_once()
    connector.client.activate_subscription.assert_called_once_with("xml")
    connector.log.assert_called_once()


def test_pull_content(connector, event):
    connector.client.list_subscriptions.return_value = ["json"]
    connector.client.get_subscription_contents.return_value = [[{"contentUri": " foo://example.com"}]]
    connector.client.get_content.return_value = [event]

    assert connector.pull_content(datetime.now()) == [event]
