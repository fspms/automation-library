import time
from json import JSONDecodeError

import pytest
from websocket import WebSocketTimeoutException

from retarus_modules.retarus_events_consumer import RetarusEventsConsumer


@pytest.fixture
def consumer(connector, queue):
    return RetarusEventsConsumer(connector, queue)


def test_consumer_on_error(consumer, connector):
    error_message = "Oups!"
    consumer.on_error(None, Exception(error_message))
    consumer.on_error(None, WebSocketTimeoutException())

    assert connector.log.call_count == 2

    assert connector.log.call_args_list[0].kwargs["message"] == f"Websocket error: {error_message}"
    assert connector.log.call_args_list[0].kwargs["level"] == "error"

    assert connector.log.call_args_list[1].kwargs["message"] == "Websocket timed out"
    assert connector.log.call_args_list[1].kwargs["level"] == "warning"


def test_consumer_on_close(consumer, connector):
    consumer.on_close(None)
    connector.log.assert_called_once_with(message="Closing socket connection", level="info")


def test_consumer_on_message(consumer):
    assert consumer.queue.empty()

    message_str = '{"data": "foo"}'
    message_dict = {"data": "foo"}
    consumer.on_message(None, message_str)

    assert consumer.queue.get_nowait() == message_dict


def test_consumer_on_message_json_error(consumer, connector):
    assert consumer.queue.empty()

    consumer.on_message(None, "invalid json")

    log_arguments = connector.log_exception.call_args_list[0]
    connector.log_exception.assert_called_once
    assert isinstance(log_arguments.args[0], JSONDecodeError)
    assert log_arguments.kwargs["message"] == "Failed to consume event"


def test_stop_consumer(consumer):
    consumer.start()

    assert consumer.is_alive()
    assert not consumer._stop_event.is_set()

    consumer.stop()
    time.sleep(0.5)
    assert not consumer.is_alive()
    assert consumer._stop_event.is_set()
