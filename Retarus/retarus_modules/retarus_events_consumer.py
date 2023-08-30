from queue import SimpleQueue
from threading import Event, Thread
from typing import Tuple

import orjson
from sekoia_automation.connector import Connector
from websocket import WebSocketApp, WebSocketTimeoutException


class RetarusEventsConsumer(Thread):
    """Handler for receiving events from a websocket"""

    def __init__(self, connector: Connector, queue: SimpleQueue):
        super().__init__()
        self.connector = connector
        self.queue = queue
        self.configuration = connector.configuration

        # Event used to stop the thread
        self._stop_event = Event()

    def stop(self):
        """Sets the stop event"""
        self._stop_event.set()

    def create_websocket(self) -> Tuple[WebSocketApp, Thread]:
        """Creates a WebSocket inside a Thread

        Returns:
            Tuple[WebSocketApp, Thread]: The websocket we opened, The thread in which it will run
        """
        websocket = WebSocketApp(
            url=self.configuration.ws_url,
            header=[f"Authorization: Bearer {self.configuration.ws_key}"],
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        websocket_thread = Thread(target=websocket.run_forever)
        websocket_thread.daemon = True

        return websocket, websocket_thread

    def on_message(self, _, event: str) -> None:
        """Callback method called when the websocket receives a message

        It will send the received message to the queue for consumtpion by the forwarder

        Args:
            _ (_type_): _description_
            event (str): Message received on the websocket
        """
        try:
            message = orjson.loads(event)
            self.queue.put(message)
        except orjson.JSONDecodeError as ex:
            self.connector.log_exception(ex, message="Failed to consume event")

    def on_error(self, _, error: Exception):
        """Callback method called when the websocket encounters an exception

        We log the exception using the Connector's logger, as a warning if it is a timeout, as an error otherwise

        Args:
            _ (_type_): _description_
            error (Exception): Exception encountered
        """
        if isinstance(error, WebSocketTimeoutException):
            # add a gentler message for timeout
            self.connector.log(message="Websocket timed out", level="warning")
        else:
            self.connector.log(message=f"Websocket error: {error}", level="error")

    def on_close(self, *_):
        """Callback method called when the websocket is closed"""
        self.connector.log(message="Closing socket connection", level="info")

    def run(self):
        """Start the websocket thread then wait for the stop event to be set and close the websocket when it happens"""
        self.connector.log(message=f"Connection to stream {self.configuration.ws_url}", level="info")

        websocket, websocket_thread = self.create_websocket()
        websocket_thread.start()

        self._stop_event.wait()

        websocket.close()
