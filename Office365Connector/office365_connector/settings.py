"""
This module defines the model for intakes configurations.
"""

from pydantic import BaseSettings


class Office365IntakeSettings(BaseSettings):
    """Represents an Office 365 intake configuration. It stores data
    required to retrieve data from Microsoft Office 365 Management
    Activity API.

    """

    intake_uuid: str
    community_uuid: str
    uuid: str
    tenant_uuid: str | None = None
