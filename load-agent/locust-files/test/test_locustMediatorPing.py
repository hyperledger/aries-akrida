from unittest.mock import MagicMock

import pytest
from locustMediatorPing import UserBehaviour


class TestUserBehaviour:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_client = MagicMock()
        self.mock_parent = MagicMock()
        self.mock_parent.client = self.mock_client
        self.behaviour = UserBehaviour(parent=self.mock_parent)

    def test_on_start_calls_startup(self):
        self.behaviour.on_start()
        self.mock_client.startup.assert_called_once()

    def test_on_stop_calls_shutdown(self):
        self.behaviour.on_stop()
        self.mock_client.shutdown.assert_called_once()

    def test_ping_mediator_calls_ensure_is_running_and_ping(self):
        self.behaviour.ping_mediator()
        self.mock_client.ensure_is_running.assert_called_once()
        self.mock_client.ping_mediator.assert_called_once()

    def test_ping_mediator_raises_when_ensure_is_running_fails(self):
        self.mock_client.ensure_is_running.side_effect = RuntimeError("Agent not running")
        with pytest.raises(RuntimeError, match="Agent not running"):
            self.behaviour.ping_mediator()

    def test_ping_mediator_raises_when_ping_fails(self):
        self.mock_client.ensure_is_running.return_value = None
        self.mock_client.ping_mediator.side_effect = RuntimeError("Ping failed")
        with pytest.raises(RuntimeError, match="Ping failed"):
            self.behaviour.ping_mediator()


class TestBoolConversion:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", False),
            ("0", True),
            ("false", True),
            ("False", True),
            ("FALSE", True),
            ("true", True),
            ("1", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
        ],
    )
    def test_bool_conversion(self, value, expected):
        assert bool(value) == expected
