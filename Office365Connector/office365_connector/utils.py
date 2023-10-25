"""
This module defines the model for intakes configurations.
"""

from urllib.parse import urlparse
import uuid
from datetime import datetime

from sekoia.common.utils import generate_short_id
from sekoia.webapi.sqlalchemy import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref


INTAKE_SETTINGS_UUID = "intake_settings.uuid"
OFFICE365_AUTHORITY_DEFAULT = "https://login.microsoftonline.com/common"
OFFICE365_URL_BASE = "https://manage.office.com/api/v1.0/{tenant_id}/activity/feed"
OFFICE365_ACTIVE_SUBSCRIPTION_STATUS = "enabled"


def normalize_url(url: str, tenant_id: str | None = None) -> str:
    """
    Normalize the url

    :param str url: The url to normalize
    :return: The normalized url
    :rtype: str
    """
    uri = urlparse(url)

    if tenant_id is None:
        parts = uri.path.split("/")
        if len(parts) > 0:
            tenant_id = parts[1]
        else:
            tenant_id = "common"

    return urlunsplit((uri.scheme, uri.hostname, tenant_id, None, None))


class IntakeSetting(db.Model):
    """Represents an abstract view of an intake configuration. This model
    stores metadata about the intake configuration.  Configuration
    could be specialized in a subclass, such as for Office 365.

    """

    __tablename__ = "intake_settings"

    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, primary_key=True, nullable=False)
    short_id = db.Column(db.String(), nullable=False, index=True, default=lambda: generate_short_id(prefix="IS"))
    type = db.Column(db.String(50))

    # Intake
    intake_uuid = db.Column(db.String(36), db.ForeignKey("intakes.uuid"), nullable=False)
    intake = db.relationship("Intake", backref=backref("settings", cascade="delete, delete-orphan", uselist=False))

    # Community
    community_uuid = db.Column(db.String(36), db.ForeignKey("customer.community_uuid"), nullable=False)
    customer = db.relationship("Customer", primaryjoin="IntakeSetting.community_uuid == Customer.community_uuid")

    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.String(36), nullable=False)
    created_by_type = db.Column(db.String, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(36), nullable=True)
    updated_by_type = db.Column(db.String, nullable=True)

    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": type}
    __public_fields__ = []
    __encrypted_fields__ = []


class Office365IntakeSetting(IntakeSetting):
    """Represents an Office 365 intake configuration. It stores data
    required to retrieve data from Microsoft Office 365 Management
    Activity API.

    """

    __tablename__ = "intake_settings_office365"

    uuid = db.Column(UUID(as_uuid=True), db.ForeignKey(INTAKE_SETTINGS_UUID), primary_key=True)

    tenant_uuid = db.Column(UUID(as_uuid=True), index=True)

    # Did we have the admin consent from Microsoft API?
    admin_consent = db.Column(db.Boolean, nullable=False, default=False)

    # Did we succeed at retrieving logs from Microsoft?
    validated = db.Column(db.Boolean, nullable=False, default=False)

    __mapper_args__ = {"polymorphic_identity": "office365"}


def create_setting_office365(intake_uuid: str):
    """Return the intake setting for Office365

    :param str intake_uuid: The identifier of the intake the setting belong to
    :raise: sic.exceptions.IntakeDoesNotExistsError
    :raise: sic.exceptions.IntakeSettingDoesNotExistsError
    """
    # check the existence of the intake
    intake = self._get_intake(intake_uuid)

    enrich_current_action(
        name="intake-office365-creation",
        communities=intake.community_uuid,
        parameters={"intake": {"uuid": str(intake.uuid), "name": intake.name}},
    )

    # check if the office 365 setting already exist
    setting = Office365IntakeSetting.query.filter_by(intake_uuid=intake.uuid).first()
    if setting is not None:
        raise IntakeSettingAlreadyExistError(intake_uuid=intake_uuid, type="office365")

    # create the setting
    setting = Office365IntakeSetting(
        uuid=uuid.uuid4(),
        short_id=generate_short_id(prefix="IS"),
        intake_uuid=intake_uuid,
        community_uuid=intake.community_uuid,
        created_at=datetime.utcnow(),
        created_by=self.profile.identity,
        created_by_type=self.profile.type,
    )
    db.session.add(setting)
    db.session.commit()
