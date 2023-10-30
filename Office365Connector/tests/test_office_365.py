
from unittest.mock import patch

from office365_connector.connector import Office365Connector


@patch.object(Office365Connector, "log")
@patch.object(Office365Connector, "push_events_to_intakes")
def test_pull_content(mock_push_events, mock_log, event):
    assert False


def test_forward_events():
    assert False


def test_check_for_duplicates():
    assert False


def test_activate_subscriptions():
    assert False
