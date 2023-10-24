from sekoia_automation.module import Module
from office365_connector.connector import Office365Connector

if __name__ == "__main__":
    module = Module()
    module.register(Office365Connector, "office365_connector")
    module.run()