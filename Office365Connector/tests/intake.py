import random
from datetime import datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from faker import Faker


class IntakeGenerator:
    faker: Faker

    def create_fake_intake_format(
        self,
        uuid: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        if uuid is None:
            uuid = str(uuid4())

        if name is None:
            name = self.faker.word()

        all_datasources = list(ATTACKDatasource.query.all())

        new_format = IntakeFormat(
            uuid=uuid,
            name=name,
            description=self.faker.sentence(),
            slug=self.faker.word(),
            datasources=random.choices(all_datasources, k=random.randint(1, 5)),
        )

        return self.intake_business._serialize_intake_format(new_format)

    def create_fake_intake(
        self,
        entity,
        format,
        name: str | None = None,
        uuid: str | None = None,
        community_uuid: str | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        created_by_type: str = "avatar",
    ) -> dict[str, Any]:
        if uuid is None:
            uuid = str(uuid4())

        if name is None:
            name = self.faker.word()

        if community_uuid is None:
            community_uuid = entity["community_uuid"]

        if created_by is None:
            created_by = str(uuid4())

        if created_at is None:
            created_at = datetime.utcnow()

        with patch("sekoia.webapi.notification.notification_client.notify_v1"):
            new_intake = Intake(
                intake_key=new_intake_key(),
                community_uuid=community_uuid,
                uuid=uuid,
                name=name,
                entity_uuid=entity["uuid"],
                format_uuid=format["uuid"],
                created_at=created_at,
                created_by=created_by,
                created_by_type=created_by_type,
            )

        return self.intake_business._serialize_intake(new_intake)

    def create_fake_intake_office365_setting(
        self,
        intake_uuid: str,
        community_uuid: str,
        uuid: str | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        created_by_type: str = "avatar",
        short_id: str | None = None,
        tenant_uuid: str | None = None,
        admin_consent: bool = False,
        validated: bool = False,
    ):
        if uuid is None:
            uuid = str(uuid4())

        if created_by is None:
            created_by = str(uuid4())

        if created_at is None:
            created_at = datetime.utcnow()

        if short_id is None:
            short_id = generate_short_id(prefix="IS")

        setting = Office365IntakeSetting(
            uuid=uuid,
            short_id=short_id,
            intake_uuid=intake_uuid,
            community_uuid=community_uuid,
            created_at=created_at,
            created_by=created_by,
            created_by_type=created_by_type,
            tenant_uuid=tenant_uuid,
            admin_consent=admin_consent,
            validated=validated,
        )

        return setting

    def create_fake_intake_sentinel_one_setting(
        self,
        intake_uuid: str,
        community_uuid: str,
        api_key: str,
        management_domain: str,
        last_activity_created_at: str | None = None,
        last_threat_created_at: str | None = None,
        uuid: str | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        created_by_type: str = "avatar",
        validated: bool = False,
    ):
        if uuid is None:
            uuid = str(uuid4())

        if created_by is None:
            created_by = str(uuid4())

        if created_at is None:
            created_at = datetime.utcnow()

        if last_activity_created_at is None:
            last_activity_created_at = f"{datetime.utcnow().isoformat()}Z"

        short_id = generate_short_id(prefix="IS")

        setting = SentinelOneIntakeSetting(
            uuid=uuid,
            intake_uuid=intake_uuid,
            community_uuid=community_uuid,
            created_at=created_at,
            created_by=created_by,
            created_by_type=created_by_type,
            validated=validated,
            api_key=SICConfig.ENCRYPTION_SERVICE.encrypt(api_key),
            management_domain=management_domain,
            short_id=short_id,
            last_activity_created_at=last_activity_created_at,
            last_threat_created_at=last_threat_created_at or f"{datetime.utcnow().isoformat()}Z",
        )

        return setting
