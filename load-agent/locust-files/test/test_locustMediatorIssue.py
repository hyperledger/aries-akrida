from unittest.mock import MagicMock

import pytest
from locustMediatorIssue import Issue, UserBehaviour


class TestUserBehaviour:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_client = MagicMock()
        self.mock_parent = MagicMock()
        self.mock_parent.client = self.mock_client
        self.behaviour = UserBehaviour(parent=self.mock_parent)
        self.behaviour.invites = [
            {"connection_id": "conn-1"},
            {"connection_id": "conn-2"},
        ]

    def test_receive_credential_calls_client_methods(self):
        self.behaviour.receive_credential()
        self.mock_client.ensure_is_running.assert_called_once()
        assert self.mock_client.receive_credential.call_count == 2


class TestIssue:
    def test_locust_class_exists(self):
        assert Issue is not None
        assert hasattr(Issue, "tasks")
        assert UserBehaviour in Issue.tasks
