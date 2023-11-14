from zscaler.block_ioc import ZscalerBlockIOC

def test_block_ioc_action_success(requests_mock):
    mock_alert = requests_mock.post(url="https://thehive-project.org/api/alert", json={})

    action = ZscalerBlockIOC()
    action.module.configuration = {
        "base_url": "zscalerbeta.net",
        "apikey": "EqusKSwWRW7M",
        "username": "admin@16411777.zscalerbeta.net",
        "password": "xJO$c>(6I;)2"
    }

    result = action.run({"IoC": "185.216.70.222"})
    assert not action._error
    assert result is not None
    assert mock_alert.call_count == 1

    mock_alert = requests_mock.post(url="https://zscalerbeta.net/api/alert", status=200)
