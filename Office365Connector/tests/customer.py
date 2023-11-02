import random
from typing import Any
from uuid import uuid4

from faker import Faker


class CustomerGenerator:
    faker: Faker

    def create_fake_customer(
        self,
        name: str | None = None,
        customer_id: int | None = None,
        community_uuid: str | None = None,
        description: str | None = None,
        created_by: str | None = None,
        generation_modes: list[Any] | None = None,
    ) -> Customer:
        if name is None:
            name = self.faker.word()

        if community_uuid is None:
            community_uuid = str(uuid4())

        if customer_id is None:
            customer_id = random.randint(0, 1000)

        if created_by is None:
            created_by = str(uuid4())

        new_customer = Customer(
            name=name,
            community_uuid=community_uuid,
            customer_id=customer_id,
            created_by=created_by,
            description=description,
        )

        if generation_modes is not None:
            for generation_mode in generation_modes:
                new_customer.generation_modes.append(generation_mode)

        return new_customer
