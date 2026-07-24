from unittest.mock import MagicMock

import pytest
from locustMediatorPresentProof import Issue, UserBehaviour


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
        self.behaviour.verifier_invite = {
            "connection_id": "verifier-conn-1",
            "invitation_url": "http://example.com/invite",
        }

    def test_receive_credential_calls_client(self):
        self.behaviour.receive_credential()
        self.mock_client.ensure_is_running.assert_called_once()
        assert self.mock_client.receive_credential.call_count == 2

    def test_get_verifier_invite_calls_issuer_getinvite(self):
        self.behaviour.get_verifier_invite()
        self.mock_client.issuer_getinvite.assert_called_once()
        assert self.behaviour.verifier_invite is not None

    def test_accept_verifier_invite_calls_accept_invite(self):
        self.behaviour.accept_verifier_invite()
        self.mock_client.ensure_is_running.assert_called_once()
        self.mock_client.accept_invite.assert_called_once_with("http://example.com/invite")

    def test_presentation_exchange_calls_client(self):
        self.behaviour.presentation_exchange()
        self.mock_client.ensure_is_running.assert_called_once()
        self.mock_client.presentation_exchange.assert_called_once_with("verifier-conn-1")


class TestIssue:
    def test_locust_class_exists(self):
        assert Issue is not None
        assert hasattr(Issue, "tasks")
        assert UserBehaviour in Issue.tasks
