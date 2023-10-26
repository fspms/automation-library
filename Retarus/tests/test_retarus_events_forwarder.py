import copy
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Thread
from unittest import mock
from unittest.mock import Mock

import orjson
import pytest

from retarus_modules.connector import RetarusConnector
from tests.data import ORIGINAL_MESSAGE
from threading import Thread


def test_forward_on_message(connector, queue):
    expected_message = orjson.loads(ORIGINAL_MESSAGE)
    message = copy.deepcopy(expected_message)

    queue.put(message, block=False)
    connector.events_queue = queue

    Thread(target=connector.execute).start()
    time.sleep(0.5)
    connector.stop()

    for call in connector.push_events_to_intakes.call_args_list:
        assert call.kwargs["topic"] == "qux"
        assert call.kwargs["value"]["message"] == expected_message


def test_forward_on_message_empty_queue(connector):
    Thread(target=connector.execute).start()
    time.sleep(10)
    connector.stop()

    connector.push_events_to_intakes.assert_not_called()
    connector.log.assert_called_with(message="Empty queue", level="DEBUG")


@pytest.mark.skipif("{'RETARUS_APIKEY', 'RETARUS_CLUSTER_ID'}.issubset(os.environ.keys()) == False")
def test_forward_events_integration(symphony_storage):
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    trigger = RetarusConnector(data_path=symphony_storage)
    trigger.module.configuration = {}
    trigger.configuration = {
        "cluster_id": os.environ["RETARUS_CLUSTER_ID"],
        "since_time": one_hour_ago,
        "type": "message",
        "intake_key": "12345",
        "kafka_url": "bar",
        "kafka_topic": "qux",
        "ws_url": "https://web.socket",
        "ws_key": "secret",
    }
    trigger.push_events_to_intakes = Mock()
    trigger.log_exception = Mock()
    trigger.log = Mock()

    thread = Thread(target=trigger.run)
    thread.start()
    time.sleep(30)
    trigger.stop()
    thread.join()
    calls = [call.kwargs["events"] for call in trigger.push_events_to_intakes.call_args_list]
    trigger.log_exception.assert_not_called()
    assert len(calls) > 0
