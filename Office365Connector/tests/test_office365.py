from unittest.mock import patch

import requests_mock
from faker import Faker

from sic.api.intakes.business import Business as IntakeBusiness
from sic.services.generation_mode_service import generation_mode_service
from sic.workers.intakes.office365.tasks import (
    office365_activate_subscriptions,
    office365_activity_pull,
    office365_pull_contents,
)
from tests.generator.customer import CustomerGenerator
from tests.generator.entity import EntityGenerator
from tests.generator.intake import IntakeGenerator
from tests.workers.base import WorkerBaseTestCase


class O365TasksTestCase(WorkerBaseTestCase, IntakeGenerator, CustomerGenerator, EntityGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None
        self.faker = Faker()
        self.intake_business = IntakeBusiness(None)

    @requests_mock.Mocker()
    def test_office365_pull_contents(self, mock_o365):
        # arrange
        community_uuid = "c47fc68c-4ee5-4a01-bf50-412d33881b13"
        tenant_id = "5a081dcf-3a2a-426b-938d-9ec84f259b5d"
        content_type = "Audit.SharePoint"

        generation_mode = generation_mode_service.create(name=self.faker.word(), description=self.faker.sentence())
        self.create_fake_customer(community_uuid=community_uuid, generation_modes=[generation_mode])
        entity = self.create_fake_entity(community_uuid=community_uuid, alerts_generation=generation_mode.uuid)
        intake_format = self.create_fake_intake_format()
        intake = self.create_fake_intake(
            entity=entity.to_dict(),
            format=intake_format,
            community_uuid=community_uuid,
        )
        setting = self.create_fake_intake_office365_setting(
            intake_uuid=intake["uuid"],
            community_uuid=community_uuid,
            tenant_uuid=tenant_id,
            validated=True,
        )

        # act
        with patch("sic.workers.intakes.office365.tasks.office365_pull_contents") as pull_contents:
            office365_activity_pull()
            pull_contents.apply_async.assert_called_with(kwargs={"setting_uuid": str(setting.uuid)})

    @requests_mock.Mocker()
    def test_office365_activity_pull(self, mock_o365):
        # arrange
        community_uuid = "c47fc68c-4ee5-4a01-bf50-412d33881b13"
        tenant_id = "5a081dcf-3a2a-426b-938d-9ec84f259b5d"
        content_type = "Audit.SharePoint"

        # flake8: noqa
        content_uri = "https://manage.office.com/api/v1.0/f28ab78a-d401-4060-8012-736e373933eb/activity/feed/audit/492638008028$492638008028$f28ab78ad40140608012736e373933ebspo2015043022$4a81a7c326fc4aed89c62e6039ab833b$04"
        content = {
            "contentType": "Audit.SharePoint",
            "contentId": "492638008028$492638008028$f28ab78ad40140608012736e373933ebspo2015043022$4a81a7c326fc4aed89c62e6039ab833b$04",
            "contentUri": content_uri,
            "contentCreated": "2015-05-23T17:35:00.000Z",
            "contentExpiration": "2015-05-30T17:35:00.000Z",
        }
        # flake8: qa

        generation_mode = generation_mode_service.create(name=self.faker.word(), description=self.faker.sentence())
        self.create_fake_customer(community_uuid=community_uuid, generation_modes=[generation_mode])
        entity = self.create_fake_entity(community_uuid=community_uuid, alerts_generation=generation_mode.uuid)
        intake_format = self.create_fake_intake_format()
        intake = self.create_fake_intake(
            entity=entity.to_dict(),
            format=intake_format,
            community_uuid=community_uuid,
        )
        setting = self.create_fake_intake_office365_setting(
            intake_uuid=intake["uuid"],
            community_uuid=community_uuid,
            tenant_uuid=tenant_id,
            validated=True,
        )

        mock_o365.get(
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.get(
            "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
            status_code=200,
            json={"access_token": "access_token", "token_type": "Bearer", "expires_in": 0},
        )
        mock_o365.get(
            f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/list",
            status_code=200,
            json=[
                {
                    "contentType": content_type,
                    "status": "enabled",
                    "webhook": {
                        "status": "enabled",
                        "address": "https://webhook.myapp.com/o365/",
                        "authId": "o365activityapinotification",
                        "expiration": None,
                    },
                }
            ],
        )
        # flake8: noqa
        mock_o365.get(
            f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/content?contentType={content_type}",
            status_code=200,
            json=[
                {
                    "contentType": "Audit.SharePoint",
                    "contentId": "492638008028$492638008028$f28ab78ad40140608012736e373933ebspo2015043022$4a81a7c326fc4aed89c62e6039ab833b$04",
                    "contentUri": "https://manage.office.com/api/v1.0/f28ab78a-d401-4060-8012-736e373933eb/activity/feed/audit/492638008028$492638008028$f28ab78ad40140608012736e373933ebspo2015043022$4a81a7c326fc4aed89c62e6039ab833b$04",
                    "contentCreated": "2015-05-23T17:35:00.000Z",
                    "contentExpiration": "2015-05-30T17:35:00.000Z",
                },
            ],
        )
        # flake8: qa

        mock_o365.get(
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.get(
            "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
            status_code=200,
            json={"access_token": "access_token", "token_type": "Bearer", "expires_in": 0},
        )
        mock_o365.get(
            content_uri,
            status_code=200,
            json=[
                {
                    "CreationTime": "2015-06-29T20:03:19",
                    "Id": "80c76bd2-9d81-4c57-a97a-accfc3443dca",
                    "Operation": "PasswordLogonInitialAuthUsingPassword",
                    "OrganizationId": "41463f53-8812-40f4-890f-865bf6e35190",
                    "RecordType": 9,
                    "ResultStatus": "failed",
                    "UserKey": "1153977025279851686@contoso.onmicrosoft.com",
                    "UserType": 0,
                    "Workload": "AzureActiveDirectory",
                    "ClientIP": "134.170.188.221",
                    "ObjectId": "admin@contoso.onmicrosoft.com",
                    "UserId": "admin@contoso.onmicrosoft.com",
                    "AzureActiveDirectoryEventType": 0,
                    "ExtendedProperties": [
                        {
                            "Name": "LoginError",
                            "Value": "-2147217390;PP_E_BAD_PASSWORD;The entered and stored passwords do not match.",
                        }
                    ],
                    "Client": "Exchange",
                    "LoginStatus": -2147217390,
                    "UserDomain": "contoso.onmicrosoft.com",
                },
                {
                    "CreationTime": "2015-06-29T20:03:34",
                    "Id": "4e655d3f-35fa-42e0-b050-264b2d255c7a",
                    "Operation": "PasswordLogonInitialAuthUsingPassword",
                    "OrganizationId": "41463f53-8812-40f4-890f-865bf6e35190",
                    "RecordType": 9,
                    "ResultStatus": "success",
                    "UserKey": "1153977025279851686@contoso.onmicrosoft.com",
                    "UserType": 0,
                    "Workload": "AzureActiveDirectory",
                    "ClientIP": "134.170.188.221",
                    "ObjectId": "admin@contoso.onmicrosoft.com",
                    "UserId": "admin@contoso.onmicrosoft.com",
                    "AzureActiveDirectoryEventType": 0,
                    "Client": "Exchange",
                    "LoginStatus": 0,
                    "UserDomain": "contoso.onmicrosoft.com",
                },
            ],
        )

        # act
        with patch(
            "sic.workers.intakes.office365.tasks.get_o365_pull_contents_cache",
            **{"return_value.client.exists.return_value": False, "return_value.client.set.return_value": True},
        ) as mock_redis:
            with patch("sic.workers.intakes.office365.tasks.ConfluentProducer") as kafka_mock:
                office365_pull_contents(setting_uuid=str(setting.uuid))

                mock_redis.return_value.client.exists.assert_called()
                mock_redis.return_value.client.set.assert_called()
                kafka_mock.return_value.send.assert_called()

        # act 2
        with patch(
            "sic.workers.intakes.office365.tasks.get_o365_pull_contents_cache",
            **{
                "return_value.sismember.return_value": True,
            },
        ) as mock_redis:
            with patch("sic.workers.intakes.office365.tasks.ConfluentProducer") as kafka_mock:
                office365_pull_contents(setting_uuid=str(setting.uuid))

                mock_redis.return_value.client.exists.assert_called()
                mock_redis.return_value.client.set.assert_not_called()

                kafka_mock.return_value.send.assert_not_called()

    @requests_mock.Mocker()
    def test_office365_activate_subscriptions(self, mock_o365):
        # arrange
        community_uuid = "c47fc68c-4ee5-4a01-bf50-412d33881b13"
        tenant_id = "5a081dcf-3a2a-426b-938d-9ec84f259b5d"

        generation_mode = generation_mode_service.create(name=self.faker.word(), description=self.faker.sentence())
        self.create_fake_customer(community_uuid=community_uuid, generation_modes=[generation_mode])
        entity = self.create_fake_entity(community_uuid=community_uuid, alerts_generation=generation_mode.uuid)
        intake_format = self.create_fake_intake_format()
        intake = self.create_fake_intake(
            entity=entity.to_dict(),
            format=intake_format,
            community_uuid=community_uuid,
        )
        setting = self.create_fake_intake_office365_setting(
            intake_uuid=intake["uuid"],
            community_uuid=community_uuid,
            tenant_uuid=tenant_id,
            validated=True,
        )

        mock_o365.get(
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.get(
            "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
            status_code=200,
            json={
                "token_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
                "authorization_endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize",
            },
        )
        mock_o365.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
            status_code=200,
            json={"access_token": "access_token", "token_type": "Bearer", "expires_in": 0},
        )
        mock_o365.get(
            f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/list",
            status_code=200,
            json=[
                {
                    "contentType": "Audit.SharePoint",
                    "status": "enabled",
                    "webhook": {
                        "status": "enabled",
                        "address": "https://webhook.myapp.com/o365/",
                        "authId": "o365activityapinotification",
                        "expiration": None,
                    },
                }
            ],
        )
        mock_o365.post(
            f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/start",
            status_code=200,
            json={
                "contentType": "Audit.Azure",
                "status": "enabled",
                "webhook": {
                    "status": "enabled",
                    "address": "https://webhook.myapp.com/o365/",
                    "authId": "o365activityapinotification",
                    "expiration": None,
                },
            },
        )

        # act
        with patch("sic.workers.intakes.office365.tasks.office365_pull_contents"):
            office365_activate_subscriptions(setting.uuid)
