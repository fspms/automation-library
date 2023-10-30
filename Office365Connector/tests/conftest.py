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
    trigger = Office365Connector(data_path=symphony_storage)
    trigger.module.configuration = {}
    trigger.configuration = {
    }
    trigger.log = Mock()
    trigger.log_exception = Mock()
    trigger.push_events_to_intakes = Mock()
    yield trigger

@pytest.fixture
def event():
    raise NotImplementedError