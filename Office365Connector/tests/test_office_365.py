import json
from unittest.mock import patch

from prometheus_client import Counter

from office365_connector.connector import Office365Connector


def test_pull_content():
    assert False


@patch.object(Counter, "inc")
def test_forward_events(mock_prometheus, connector, event):
    connector.forward_events([event])
    connector.log.assert_called_once_with("Pushing 1 event(s) to intake", level="info")
    mock_prometheus.assert_called_once()
    connector.push_events_to_intakes.assert_called_once_with([json.dumps(event)])


def test_check_for_duplicates():
    assert False


def test_activate_subscriptions():
    assert False
