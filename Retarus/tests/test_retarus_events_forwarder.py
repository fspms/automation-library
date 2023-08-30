import copy
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Thread
from unittest import mock
from unittest.mock import Mock

import orjson
import pytest
from kafka.errors import KafkaTimeoutError

from retarus_modules import retarus_events_forwarder
from retarus_modules.retarus_connector import RetarusConnector
from retarus_modules.retarus_events_forwarder import RetararusEventsForwarder
from tests.data import ORIGINAL_MESSAGE


@pytest.fixture
@mock.patch.object(retarus_events_forwarder, "KafkaProducer")
def forwarder(_, connector, queue):
    return RetararusEventsForwarder(connector, queue, queue_get_limit=1, queue_get_timeout=0.1, queue_get_retries=1)


@pytest.fixture
@mock.patch.object(retarus_events_forwarder, "KafkaProducer")
def forwarder_timeout_error(_, connector, queue):
    forwarder = RetararusEventsForwarder(
        connector, queue, queue_get_limit=1, queue_get_timeout=0.1, queue_get_retries=1
    )
    forwarder.kafka_producer.send.side_effect = KafkaTimeoutError
    return forwarder


def test_forward_on_message(forwarder, queue):
    expected_message = orjson.loads(ORIGINAL_MESSAGE)
    message = copy.deepcopy(expected_message)

    queue.put(message, block=False)
    forwarder.queue = queue

    forwarder.start()
    time.sleep(0.5)
    forwarder.stop()

    for call in forwarder.kafka_producer.send.call_args_list:
        assert call.kwargs["topic"] == "qux"
        assert call.kwargs["value"]["message"] == expected_message


@mock.patch.object(RetarusConnector, "log")
def test_forward_on_message_empty_queue(_, forwarder):
    forwarder.start()
    time.sleep(0.5)
    forwarder.stop()

    forwarder.kafka_producer.send_message_assert_not_called()
    forwarder.connector.log.assert_called_with(message="Empty queue", level="DEBUG")


@mock.patch.object(RetarusConnector, "log_exception")
def test_forward_on_message_kafka_timeout(_, forwarder_timeout_error, queue):
    expected_message = orjson.loads(ORIGINAL_MESSAGE)
    message = copy.deepcopy(expected_message)
    queue.put(message, block=False)

    forwarder_timeout_error.start()
    time.sleep(0.5)
    forwarder_timeout_error.stop()

    forwarder_timeout_error.kafka_producer.send_message_assert_not_called()
    forwarder_timeout_error.connector.log_exception.assert_called_once()
    log_exception_call_args = forwarder_timeout_error.connector.log_exception.call_args_list[0]
    assert isinstance(log_exception_call_args[0][0], KafkaTimeoutError)
    assert log_exception_call_args[1] == {"message": "Error sending the log to Kafka"}


@mock.patch.object(RetarusConnector, "log_exception")
def test_forward_on_message_other_error(_, forwarder, queue):
    expected_message = orjson.loads(ORIGINAL_MESSAGE)
    message = copy.deepcopy(expected_message)
    queue.put(message, block=False)

    with mock.patch.object(RetararusEventsForwarder, "send_messages", side_effect=Exception):
        forwarder.start()
        time.sleep(0.5)
        forwarder.stop()

    forwarder.kafka_producer.send_message_assert_not_called()
    forwarder.connector.log_exception.assert_called_once()
    log_exception_call_args = forwarder.connector.log_exception.call_args_list[0]
    assert isinstance(log_exception_call_args[0][0], Exception)
    assert log_exception_call_args[1] == {"message": "Failed to forward event"}


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
    trigger.log_exception = Mock()
    trigger.log = Mock()

    thread = Thread(target=trigger.run)
    thread.start()
    time.sleep(30)
    trigger.stop()
    thread.join()
    calls = [call.kwargs["events"] for call in trigger.push_events_to_intakes.call_args_list]
    trigger.log_exception.assert_not_called
    assert len(calls) > 0
