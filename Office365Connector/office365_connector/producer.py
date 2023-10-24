from office365_connector.utils import Office365IntakeSetting

from sekoia.webapi.sqlalchemy import db

from sic.helpers.o365.azure import Office365API
from sic.helpers.o365.errors import FailedToActivateO365Subscription
from sic.models.intake_setting_model import Office365IntakeSetting
from sic.workers import celery

def office365_activate_subscriptions(self, setting_uuid: str):
    content_types = set(celery.app.config["OFFICE365_SUBSCRIPTIONS_CONTENT_TYPES"].split(","))

    setting = (
        db.session.query(Office365IntakeSetting)
        .options(db.joinedload(Office365IntakeSetting.intake))
        .get(setting_uuid)
    )

    # initialize the client
    client = Office365API(
        client_id=celery.app.config["OFFICE365_CLIENT_ID"],
        client_secret=celery.app.config["OFFICE365_CLIENT_SECRET"],
        tenant_id=str(setting.tenant_uuid),
        publisher_id=celery.app.config["OFFICE365_PUBLISHER_ID"],
    )

    already_enabled_types = set(client.list_subscriptions())
    missing_types = content_types - already_enabled_types

    enabled_types = []
    # Activate missing types
    for content_type in missing_types:
        try:
            client.activate_subscription(content_type)
            enabled_types.append(content_type)
        except FailedToActivateO365Subscription as exp:
            self._logger.warning(
                "Failed to activate subscription", tenant_id=setting.tenant_uuid, content_type=content_type, exp=exp
            )

    # If failed at enabling at least one format, then raise an
    # exception.
    if set(enabled_types) != missing_types:
        raise FailedToActivateO365Subscription()

    setting.validated = True
    db.session.commit()