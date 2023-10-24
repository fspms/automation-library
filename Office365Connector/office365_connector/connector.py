from sekoia_automation.connector import Connector, DefaultConnectorConfiguration
from office365_connector.consumer import office365_pull_contents

from office365_connector.utils import Office365IntakeSetting
import threading


class Office365Config(DefaultConnectorConfiguration):
    kafka_url: str
    kafka_topic: str
    ws_url: str
    ws_key: str


class Office365Connector(Connector):
    configuration: Office365Config

    def run(self):  # pragma: no cover
        # get all office365 intake settings
        self.create_setting_office365(str(new_intake.uuid))
        settings = Office365IntakeSetting.query.filter(Office365IntakeSetting.validated == True).all()  # noqa: E712

        # for each settings
        for setting in settings:
            threading.Thread(target=self.office365_pull_contents, kwargs={"setting_uuid": setting.uuid})

    def _get_setting_office365(self, intake_uuid: str) -> Office365IntakeSetting:
        """Return the intake setting for Office365

        :param str intake_uuid: The identifier of the intake the setting belong to
        :raise: sic.exceptions.IntakeDoesNotExistsError
        :raise: sic.exceptions.IntakeSettingDoesNotExistsError
        """
        # check the existence of the intake
        intake = self._get_intake(intake_uuid)

        # get the office 365 setting
        query = Office365IntakeSetting.query.filter_by(intake_uuid=intake.uuid)

        try:
            return query.one()
        except NoResultFound as error:
            self._logger.warn("No Office365 setting found", intake_uuid=intake_uuid, error=error)
            raise IntakeSettingDoesNotExistError(intake_uuid=intake_uuid, type="office365")

    def get_setting_office365(self, intake_uuid: str) -> dict[str, Any]:
        """Return the intake setting for Office365 as a dict

        :param str intake_uuid: The identifier of the intake the setting belong to
        :raise: sic.exceptions.IntakeDoesNotExistsError
        :raise: sic.exceptions.IntakeSettingDoesNotExistsError
        """
        setting = self._get_setting_office365(intake_uuid)
        return self._serialize_setting(setting)

    def create_setting_office365(self, intake_uuid: str) -> dict[str, Any]:
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

        return self._serialize_setting(setting)

    def _get_office365_redirect_uri(self):
        """
        Return the redirect uri to use for Office 365
        """
        redirect_uri = app.config["OFFICE365_AUTH_REDIRECT_URL"]

        if redirect_uri is None:
            redirect_uri = urljoin(
                app.config["PLATFORM_URL"], f"{API_VERSION_PREFIX}/{URL_PREFIX}/intakes/settings/office365/oidc"
            )

        return redirect_uri

    def refresh_office365_authentication(self, intake_uuid):
        """
        Start the workflow to refresh the office365 authentication
        """
        enrich_current_action(
            name="intake-office365-refresh-authentication",
            parameters={
                "intake": {
                    "uuid": intake_uuid,
                }
            },
        )

        setting = self._get_setting_office365(intake_uuid)

        oidc = OpenIDConnect(client_id=app.config["OFFICE365_CLIENT_ID"])
        return oidc.get_authorization_request_url(
            scopes=["https://manage.office.com/.default"],
            state=str(setting.short_id),
            redirect_uri=self._get_office365_redirect_uri(),
            response_mode="query",
        )

    def validate_office365_authorization_code(self, intake_uuid: str, code: str, **kwargs):
        """
        Validate the authorization code

        :param str intake_uuid: The identifier of the intake
        :param str code: The authorization code
        :param str state: The state supplied when requesting the authorization code
        """
        enrich_current_action(
            name="intake-office365-authorization-validation",
            parameters={
                "intake": {"uuid": intake_uuid},
            },
        )

        # get the setting from the state
        setting = self._get_setting_office365(intake_uuid)

        try:
            # get information about the token
            oidc = OpenIDConnect(
                client_id=app.config["OFFICE365_CLIENT_ID"], client_secret=app.config["OFFICE365_CLIENT_SECRET"]
            )

            redirect_uri = app.config["OFFICE365_ADMIN_CONSENT_REDIRECT_URL"]

            # get the identifier of the tenant
            token = oidc.get_token_by_authorization_code(
                code,
                scopes=["https://manage.office.com/.default"],
                redirect_uri=redirect_uri,
            )
            tenant_id = token.get("id_token_claims", {}).get("tid")
            if tenant_id is None:
                self._logger.error(
                    "No tenant id found",
                    setting_uuid=str(setting.uuid),
                    code=code,
                    type="office365",
                )
                raise IntakeSettingOffice365GetTokenError(
                    setting_uuid=str(setting.uuid),
                    code=code,
                )

            # update the setting
            setting.tenant_uuid = tenant_id
            db.session.add(setting)
            db.session.commit()

            endpoint_url, params = oidc.get_admin_consent_url(
                tenant_id,
                redirect_uri,
                state=setting.short_id,
            )
            querystring = urlencode(params)
            sep = "?" if "?" not in endpoint_url else "&"
            return (tenant_id, f"{endpoint_url}{sep}{querystring}")
        except IntakeSettingOffice365GetTokenError as e:
            raise e
        except Exception as e:
            self._logger.error(
                "Failed to validate the authorization code",
                setting_uuid=str(setting.uuid),
                code=code,
                type="office365",
                error=e,
            )
            raise IntakeSettingOffice365GetTokenError(
                setting_uuid=str(setting.uuid),
                code=code,
                error=str(e),
            ) from e

    def validate_office365_admin_consent(self, intake_uuid: str, consent: str, **kwargs):
        """
        Validation the admin consent

        :param str intake_uuid: The identifier of the intake
        :param str consent: The admin consent
        """
        enrich_current_action(
            name="intake-office365-admin-consent",
            parameters={
                "intake": {
                    "uuid": intake_uuid,
                }
            },
        )

        # get the setting
        setting = self._get_setting_office365(intake_uuid)

        try:
            admin_consent = parse_boolean(consent)

            # set the admin consent for the setting
            setting.admin_consent = admin_consent
            db.session.add(setting)
            db.session.commit()

            office365_activate_subscriptions.apply_async(
                kwargs={"setting_uuid": str(setting.uuid)}, countdown=600  # delay the subcription to 10 min
            )
        except ValueError:
            self._logger.warn(
                "Failed to parse admin consent",
                intake_uuid=intake_uuid,
                type="office365",
                admin_consent=admin_consent,
            )
            raise validation.UnexpectedValueError("admin_consent", consent, {"True", "False"})
