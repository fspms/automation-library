from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import Mock

import pytest
from sekoia_automation import constants
from office365_connector.connector import Office365Connector


@pytest.fixture
def symphony_storage():
    original_storage = constants.DATA_STORAGE
    constants.DATA_STORAGE = mkdtemp()

    yield Path(constants.DATA_STORAGE)

    rmtree(constants.DATA_STORAGE)
    constants.DATA_STORAGE = original_storage


@pytest.fixture
def connector(symphony_storage):
    connector = Office365Connector(data_path=symphony_storage)
    connector.module.configuration = {}
    connector.configuration = {
        "uuid": "0000",
        "tenant_uuid": "1111",
        "intake_uuid": "2222",
        "community_uuid": "3333",
        "client_id": 0,
        "client_secret": "foo",
        "publisher_id": 1,
        "content_types": ["json"],
    }
    connector.log = Mock()
    connector.log_exception = Mock()
    connector.push_events_to_intakes = Mock()
    yield connector


@pytest.fixture
def event():
    yield {"id": 42}
