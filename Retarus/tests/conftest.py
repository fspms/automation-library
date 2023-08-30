from pathlib import Path
from queue import SimpleQueue
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import Mock

import pytest
from sekoia_automation import constants

from retarus_modules.retarus_connector import RetarusConnector


@pytest.fixture
def symphony_storage():
    original_storage = constants.DATA_STORAGE
    constants.DATA_STORAGE = mkdtemp()

    yield Path(constants.DATA_STORAGE)

    rmtree(constants.DATA_STORAGE)
    constants.DATA_STORAGE = original_storage


@pytest.fixture
def connector(symphony_storage):
    trigger = RetarusConnector(data_path=symphony_storage)
    trigger.module.configuration = {}
    trigger.configuration = {
        "kafka_url": "bar",
        "intake_key": "baz",
        "kafka_topic": "qux",
        "ws_url": "https://web.socket",
        "ws_key": "secret",
    }
    trigger.log = Mock()
    trigger.log_exception = Mock()
    trigger.push_events_to_intakes = Mock()
    yield trigger


@pytest.fixture
def queue():
    return SimpleQueue()
