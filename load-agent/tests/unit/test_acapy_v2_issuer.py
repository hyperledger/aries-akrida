import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestAcapyV2IssuerAPICalls:
    @pytest.fixture(autouse=True)
    def setup_issuer(self):
        from agents.issuer.acapy_v2 import AcapyIssuer
        from models import Filter, IndyFilter

        self.issuer = AcapyIssuer()
        self.issuer.agent_url = "http://localhost:8150"
        self.issuer.headers = {"X-API-Key": "test-api-key", "Content-Type": "application/json"}
        self.issuer.schema_id = "did:indy:test:123456789abcdef:2:TestSchema:1.0"
        self.issuer.cred_def_id = "did:indy:test:123456789abcdef:3:CL:1234:default"
        self.issuer.cred_attributes = [{"name": "attr1", "value": "test"}, {"name": "attr2", "value": "test2"}]
        self.issuer.filter = IndyFilter(indy=Filter(cred_def_id=self.issuer.cred_def_id))
        self.issuer.revoke_endpoint = "/revocation/revoke"

    def test_issue_credential_v2_calls_correct_endpoint(self):
        with patch("agents.issuer.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "connection_id": "test-connection-id",
                "cred_ex_id": "test-cred-ex-id",
            }
            mock_post.return_value = mock_response

            result = self.issuer.issue_credential("test-connection-id")

            assert result["connection_id"] == "test-connection-id"
            assert result["cred_ex_id"] == "test-cred-ex-id"

            call_args = mock_post.call_args
            assert "/issue-credential-2.0/send" in call_args[0][0]

    def test_issue_credential_v2_uses_auto_issue(self):
        with patch("agents.issuer.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "connection_id": "test-connection-id",
                "cred_ex_id": "test-cred-ex-id",
            }
            mock_post.return_value = mock_response

            self.issuer.issue_credential("test-connection-id")

            payload = mock_post.call_args[1]["json"]
            assert payload["auto_issue"] is True
            assert payload["connection_id"] == "test-connection-id"
            assert payload["filter"]["indy"]["cred_def_id"] == "did:indy:test:123456789abcdef:3:CL:1234:default"

    def test_issue_credential_v2_raises_on_non_200(self):
        with patch("agents.issuer.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Internal Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Internal Server Error"):
                self.issuer.issue_credential("test-connection-id")

    def test_revoke_credential_v2_calls_correct_endpoint(self):
        with patch("agents.issuer.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            self.issuer.revoke_credential("test-connection-id", "test-cred-ex-id")

            call_args = mock_post.call_args
            assert "/revocation/revoke" in call_args[0][0]

            payload = call_args[1]["json"]
            assert payload["connection_id"] == "test-connection-id"
            assert payload["cred_ex_id"] == "test-cred-ex-id"


class TestAcapyV2IssuerAnonCreds:
    @pytest.fixture(autouse=True)
    def setup_issuer(self):
        from agents.issuer.acapy_v2 import AcapyIssuer
        from models import AnonCredsFilter, Filter

        self.issuer = AcapyIssuer()
        self.issuer.agent_url = "http://localhost:8150"
        self.issuer.headers = {"X-API-Key": "test-api-key", "Content-Type": "application/json"}
        self.issuer.schema_id = "did:indy:test:123456789abcdef:2:TestSchema:1.0"
        self.issuer.cred_def_id = "did:indy:test:123456789abcdef:3:CL:1234:default"
        self.issuer.cred_attributes = [{"name": "attr1", "value": "test"}]
        self.issuer.filter = AnonCredsFilter(anoncreds=Filter(cred_def_id=self.issuer.cred_def_id))
        self.issuer.revoke_endpoint = "/anoncreds/revocation/revoke"

    def test_issuer_uses_anoncreds_filter(self):
        assert hasattr(self.issuer, "filter")
        assert hasattr(self.issuer.filter, "anoncreds")
        assert self.issuer.filter.anoncreds.cred_def_id == "did:indy:test:123456789abcdef:3:CL:1234:default"

    def test_issuer_uses_correct_revoke_endpoint_for_anoncreds(self):
        assert self.issuer.revoke_endpoint == "/anoncreds/revocation/revoke"

    def test_issue_credential_uses_anoncreds_filter(self):
        with patch("agents.issuer.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "connection_id": "test-connection-id",
                "cred_ex_id": "test-cred-ex-id",
            }
            mock_post.return_value = mock_response

            self.issuer.issue_credential("test-connection-id")

            payload = mock_post.call_args[1]["json"]
            assert "anoncreds" in payload["filter"]
            assert payload["filter"]["anoncreds"]["cred_def_id"] == "did:indy:test:123456789abcdef:3:CL:1234:default"


class TestAcapyV2IssuerBaseMethods:
    @pytest.fixture(autouse=True)
    def setup_issuer(self):
        from agents.issuer.acapy_v2 import AcapyIssuer

        self.issuer = AcapyIssuer()
        self.issuer.agent_url = "http://localhost:8150"
        self.issuer.headers = {"X-API-Key": "test-api-key", "Content-Type": "application/json"}

    def test_is_up_returns_true_when_healthy(self):
        with patch("agents.issuer.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert self.issuer.is_up() is True

    def test_is_up_returns_false_on_error(self):
        with patch("agents.issuer.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Error"
            mock_get.return_value = mock_response

            assert self.issuer.is_up() is False

    def test_is_up_returns_false_on_exception(self):
        with patch("agents.issuer.acapy_v2.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            assert self.issuer.is_up() is False

    def test_get_invite_returns_connection_id(self):
        with (
            patch("agents.issuer.acapy_v2.requests.post") as mock_post,
            patch("agents.issuer.acapy_v2.requests.get") as mock_get,
        ):
            mock_invitation_response = MagicMock()
            mock_invitation_response.json.return_value = {
                "invi_msg_id": "test-msg-id",
                "invitation_url": "http://example.com/invite",
            }
            mock_post.return_value = mock_invitation_response

            mock_conn_response = MagicMock()
            mock_conn_response.json.return_value = {"results": [{"connection_id": "test-conn-id"}]}
            mock_get.return_value = mock_conn_response

            result = self.issuer.get_invite()

            assert result["connection_id"] == "test-conn-id"
            assert result["invitation_url"] == "http://example.com/invite"
