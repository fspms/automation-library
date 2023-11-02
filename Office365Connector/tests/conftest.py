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
def client():
    client = Mock()
    client.activate_subscription = Mock()
    client.get_subscription_contents = Mock()
    client.list_subscriptions = Mock()
    client.get_content = Mock()
    yield client


@pytest.fixture
def connector(symphony_storage, client, monkeypatch):
    connector = Office365Connector(data_path=symphony_storage)
    connector.module.configuration = {}
    connector.configuration = {
        "intake_key": "foo",
        "client_secret": "bar",
        "uuid": "0000",
        "intake_uuid": "2222",
        "community_uuid": "3333",
        "client_id": "0",
        "publisher_id": "1",
        "tenant_id": "2",
        "content_types": {"json"},
    }
    connector.log = Mock()
    connector.log_exception = Mock()
    connector.push_events_to_intakes = Mock()

    # Need the heavy artillery to override a property in a fixture
    monkeypatch.setattr("office365_connector.connector.Office365Connector.client", client)
    yield connector


@pytest.fixture
def event():
    yield {"id": 42}


@pytest.fixture
def other_event():
    yield {"id": 9000}
