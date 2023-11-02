import random
from uuid import uuid4

from faker import Faker


class EntityGenerator:
    faker: Faker

    def create_fake_entity(
        self,
        name: str | None = None,
        entity_id: int | None = None,
        community_uuid: str | None = None,
        description: str | None = None,
        alerts_generation: str | None = None,
    ) -> Entity:
        if name is None:
            name = self.faker.word()

        if community_uuid is None:
            community_uuid = str(uuid4())

        if entity_id is None:
            entity_id = random.randint(0, 1000)

        new_entity = Entity(
            name=name,
            community_uuid=community_uuid,
            entity_id=entity_id,
            alerts_generation=alerts_generation,
            description=description,
        )

        return new_entity


class CustomerGenerator:
    faker: Faker

    def create_fake_customer(
        self,
        name: str | None = None,
        community_uuid: str | None = None,
        customer_id: str | None = None,
        created_by: str | None = None,
    ) -> Customer:
        new_customer = Customer(
            name=name or self.faker.word(),
            community_uuid=community_uuid or str(uuid4()),
            customer_id=customer_id or self.faker.word(),
            created_by=created_by or str(uuid4()),
        )

        return new_customer
