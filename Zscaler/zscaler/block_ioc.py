from typing import Any

from sekoia_automation.action import Action
from zscaler_api_talkers import ZiaTalker
from requests import HTTPError


class ZscalerBlockIOC(Action):
    def run(self, arguments: dict[str, Any]):
        try:
            api = ZiaTalker(self.module.configuration["base_url"])
            api.authenticate(
                api_key=self.module.configuration["apikey"],
                username=self.module.configuration["username"],
                password=self.module.configuration["password"],
            )
        except Exception as e:
            self.error(f"ZIA authentication failed: {str(e)}")

        try:
            IOC_list = [arguments["IoC"]]
            self.log(f"IOC_list to block {IOC_list}")
        except Exception as e:
            self.log(f"Build of IOC list failed: {str(e)}")

        try:
            response = api.add_security_blacklist_urls(urls=IOC_list)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            self.error(str(e))
            if e.response is not None:
                self.log(f"ZIA blacklist url update failed with status code: {e.response.status_code}")
                self.log(f"Response: {e.response.text}")
        except Exception as e:
            self.error(str(e))

        return None
