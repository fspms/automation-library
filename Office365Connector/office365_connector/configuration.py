"""
This module defines the model for intakes configurations.
"""

from sekoia_automation.connector import DefaultConnectorConfiguration


class Office365Configuration(DefaultConnectorConfiguration):
    """Represents an Office 365 intake configuration. It stores data
    required to retrieve data from Microsoft Office 365 Management
    Activity API.

    """

    uuid: str
    tenant_uuid: str
    intake_uuid: str
    community_uuid: str
    client_id: int
    client_secret: str
    publisher_id: int
    content_types: set[str]
