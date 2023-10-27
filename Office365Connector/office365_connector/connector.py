from datetime import datetime
from time import sleep
import uuid
from sekoia_automation.connector import Connector
from office365_connector.settings import Office365IntakeSetting
from sekoia.common.utils import generate_short_id
from pathlib import Path

class Office365Connector(Connector):
    def __init__(
        self,
        intake_uuid: str,
        intake_community_uuid: str,
        data_path: Path | None = None,
    ):
        super().__init__(data_path=data_path)
        self.settings = Office365IntakeSetting(
            uuid=uuid.uuid4(),
            short_id=generate_short_id(prefix="IS"),
            intake_uuid=intake_uuid,
            community_uuid=intake_community_uuid,
            created_at=datetime.utcnow(),
            created_by=self.profile.identity,
            created_by_type=self.profile.type,
        )

    def pull_content(self) -> list[dict]:
        pass

    def forward_events(self, events: list[dict]):
        self.log(f"Pushing {len(events)} events to intake", level="info")
        self.push_events_to_intakes(events)

    def check_for_duplicates(self, events: list[dict]) -> list[dict]:
        pass

    def run(self):
        while self.running:
            events = self.pull_content()
            deduplicated_events = self.check_for_duplicates(events)
            self.forward_events(events)
            sleep(300)
            
        # Stop the connector executor
        self._executor.shutdown(wait=True)
