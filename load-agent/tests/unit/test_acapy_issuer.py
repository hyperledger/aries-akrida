import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestAcapyIssuerUnit:
    @pytest.fixture(autouse=True)
    def setup_issuer(self):
        from agents.issuer.acapy import AcapyIssuer

        self.issuer = AcapyIssuer()
        self.issuer.agent_url = "http://localhost:8150"
        self.issuer.headers = {"X-API-Key": "test-api-key", "Content-Type": "application/json"}
        self.issuer.schema_id = "did:indy:test:123456789abcdef:2:TestSchema:1.0"
        self.issuer.cred_def_id = "did:indy:test:123456789abcdef:3:CL:1234:default"
        self.issuer.cred_attributes = [{"name": "attr1", "value": "test"}, {"name": "attr2", "value": "test2"}]

    def test_issuer_has_correct_base_url(self):
        assert self.issuer.agent_url == "http://localhost:8150"

    def test_issuer_has_correct_headers(self):
        assert self.issuer.headers["X-API-Key"] == "test-api-key"
        assert self.issuer.headers["Content-Type"] == "application/json"

    def test_issuer_has_schema_and_cred_def_ids(self):
        assert self.issuer.schema_id == "did:indy:test:123456789abcdef:2:TestSchema:1.0"
        assert self.issuer.cred_def_id == "did:indy:test:123456789abcdef:3:CL:1234:default"

    def test_issue_credential_returns_correct_structure(self):
        with patch("agents.issuer.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "connection_id": "test-connection-id",
                "credential_exchange_id": "test-cred-ex-id",
            }
            mock_post.return_value = mock_response

            result = self.issuer.issue_credential("test-connection-id")

            assert result["connection_id"] == "test-connection-id"
            assert result["cred_ex_id"] == "test-cred-ex-id"
            mock_post.assert_called_once()

            call_args = mock_post.call_args
            assert "/issue-credential/send" in call_args[0][0]
            assert call_args[1]["headers"] == self.issuer.headers

    def test_issue_credential_extracts_schema_parts(self):
        with patch("agents.issuer.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "connection_id": "test-connection-id",
                "credential_exchange_id": "test-cred-ex-id",
            }
            mock_post.return_value = mock_response

            self.issuer.issue_credential("test-connection-id")

            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert payload["schema_id"] == self.issuer.schema_id
            assert payload["cred_def_id"] == self.issuer.cred_def_id
            assert payload["connection_id"] == "test-connection-id"
            assert payload["comment"] == "Performance Issuance"

    def test_issue_credential_raises_on_non_200(self):
        with patch("agents.issuer.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Internal Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Internal Server Error"):
                self.issuer.issue_credential("test-connection-id")

    def test_revoke_credential_calls_correct_endpoint(self):
        with patch("agents.issuer.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            self.issuer.revoke_credential("test-connection-id", "test-cred-ex-id")

            call_args = mock_post.call_args
            assert "/revocation/revoke" in call_args[0][0]

            payload = call_args[1]["json"]
            assert payload["connection_id"] == "test-connection-id"
            assert payload["cred_ex_id"] == "test-cred-ex-id"
            assert payload["notify_version"] == "v1_0"

    def test_revoke_credential_raises_on_non_200(self):
        with patch("agents.issuer.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Revocation Failed"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Revocation Failed"):
                self.issuer.revoke_credential("test-connection-id", "test-cred-ex-id")


class TestAcapyIssuerBaseMethods:
    @pytest.fixture(autouse=True)
    def setup_issuer(self):
        from agents.issuer.acapy import AcapyIssuer

        self.issuer = AcapyIssuer()
        self.issuer.agent_url = "http://localhost:8150"
        self.issuer.headers = {"X-API-Key": "test-api-key", "Content-Type": "application/json"}

    def test_is_up_returns_true_when_healthy(self):
        with patch("agents.issuer.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert self.issuer.is_up() is True

    def test_is_up_returns_false_on_error(self):
        with patch("agents.issuer.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Error"
            mock_get.return_value = mock_response

            assert self.issuer.is_up() is False

    def test_is_up_returns_false_on_exception(self):
        with patch("agents.issuer.acapy.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            assert self.issuer.is_up() is False

    def test_get_invite_returns_connection_id(self):
        with (
            patch("agents.issuer.acapy.requests.post") as mock_post,
            patch("agents.issuer.acapy.requests.get") as mock_get,
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
