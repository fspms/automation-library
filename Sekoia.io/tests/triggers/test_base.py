import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from requests import HTTPError
from websocket import WebSocketBadStatusException

from sekoiaio.triggers.alerts import _SEKOIANotificationBaseTrigger


@pytest.fixture
def base_trigger(module_configuration):
    base_trigger = _SEKOIANotificationBaseTrigger()
    base_trigger.module.configuration = module_configuration
    base_trigger.module._community_uuid = "cc93fe3f-c26b-4eb1-82f7-082209cf1892"
    base_trigger.log = Mock()
    base_trigger.log_exception = Mock()

    yield base_trigger


def test_sekoianotificationbasetrigger_handler_dispatch_invalid_messages(base_trigger):
    invalid_messages = [
        {},
        {"event_type": "unknown_type"},
        {"event_type": "unknown-type"},
        {"event_version": "2"},
    ]

    for message in invalid_messages:
        base_trigger.handler_dispatcher(json.dumps(message))


def test_sekoianotificationbasetrigger_handler_dispatch_invalid_json(base_trigger):
    base_trigger.handler_dispatcher("dfdfg")


def test_sekoianotificationbasetrigger_liveapi_url(base_trigger):
    base_trigger.module.configuration["base_url"] = "https://app.sekoia.io"
    assert base_trigger.liveapi_url == "wss://app.sekoia.io/live/"


def test_sekoianotificationbasetrigger_liveapi_url_api(base_trigger):
    base_trigger.module.configuration["base_url"] = "https://api.sekoia.io"
    assert base_trigger.liveapi_url == "wss://app.sekoia.io/live/"


def test_sekoianotificationbasetrigger_liveapi_url_test(base_trigger):
    base_trigger.module.configuration["base_url"] = "wss://app.test.sekoia.io"
    assert base_trigger.liveapi_url == "wss://app.test.sekoia.io/live/"


def test_sekoianotificationbasetrigger_liveapi_url_other(base_trigger):
    base_trigger.module.configuration["liveapi_url"] = "wss://other"
    assert base_trigger.liveapi_url == "wss://other"


def test_sekoianotificationbasetrigger_liveapi_url_other_generated(base_trigger):
    base_trigger.module.configuration["base_url"] = "https://fra2.app.sekoia.io"
    assert base_trigger.liveapi_url == "wss://fra2.app.sekoia.io/live/"


def test_on_error(base_trigger):
    base_trigger.on_error(None, Exception())
    base_trigger.log_exception.assert_called_once()
    base_trigger.log_exception.reset_mock()
    base_trigger.on_error(None, Exception())
    base_trigger.log_exception.assert_not_called()


def test_ping(base_trigger):
    base_trigger.on_ping(None, None)
    base_trigger.log.assert_called_once()


def test_pong(base_trigger):
    base_trigger.on_pong(None, None)
    base_trigger.log.assert_called_once()


def test_run_forbidden(base_trigger, requests_mock):
    requests_mock.get("http://fake.url//v1/me", status_code=403)
    with pytest.raises(HTTPError):
        base_trigger.run()
        assert base_trigger._error_count == 5


def test_run(base_trigger, requests_mock):
    requests_mock.get("http://fake.url//v1/me", status_code=200)
    base_trigger.stop()
    try:
        base_trigger.run()
    except Exception:
        pytest.fail("Should not have raised any exception")
    base_trigger.stop()


def test_stop(base_trigger):
    base_trigger.stop()
    assert base_trigger.running is False
