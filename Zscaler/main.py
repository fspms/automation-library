from Zscaler import ZscalerModule
from Zscaler.custom_iocs import (
    ZscalerActionBlockIOC,
    ZscalerActionPushIOCsBlock,
)

if __name__ == "__main__":
    module = ZscalerModule()
    module.register(ZscalerActionPushIOCsBlock, "push_iocs_block")
    module.register(ZscalerActionBlockIOC, "block_ioc")

    module.run()
