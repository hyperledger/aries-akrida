import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestAcapyVerifierV1:
    @pytest.fixture(autouse=True)
    def setup_verifier(self, monkeypatch):
        monkeypatch.setenv("VERIFIER_URL", "http://localhost:8150")
        monkeypatch.setenv("VERIFIER_TYPE", "acapy")
        monkeypatch.setenv("VERIFIER_HEADERS", '{"X-API-Key": "test-key"}')
        monkeypatch.setenv("VERIFIED_TIMEOUT_SECONDS", "2")
        monkeypatch.setenv("SCHEMA", "did:indy:test:123456789abcdef:2:TestSchema:1.0")
        monkeypatch.setenv("CRED_DEF", "did:indy:test:123456789abcdef:3:CL:1234:default")
        monkeypatch.setenv("CRED_ATTR", '[{"name": "score", "value": "100"}]')
        monkeypatch.setenv("IS_ANONCREDS", "false")
        monkeypatch.setenv("START_PORT", "10000")
        monkeypatch.setenv("END_PORT", "10500")

        from settings import Settings

        monkeypatch.setattr(Settings, "VERIFIED_TIMEOUT_SECONDS", 2)
        monkeypatch.setattr(Settings, "CRED_ATTR", [{"name": "score", "value": "100"}])

        from agents.verifier.acapy import AcapyVerifier

        self.verifier = AcapyVerifier()
        self.verifier.agent_url = "http://localhost:8150"
        self.verifier.headers = {"X-API-Key": "test-key", "Content-Type": "application/json"}

    def test_verifier_has_correct_base_url(self):
        assert self.verifier.agent_url == "http://localhost:8150"

    def test_create_connectionless_request_correct_endpoint(self):
        with patch("agents.verifier.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pres_ex_id": "test-id"}
            mock_post.return_value = mock_response

            self.verifier.create_connectionless_request()

            call_args = mock_post.call_args
            assert "/present-proof/create-request" in call_args[0][0]

    def test_create_connectionless_request_raises_on_non_200(self):
        with patch("agents.verifier.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Server Error"):
                self.verifier.create_connectionless_request()

    def test_request_verification_correct_endpoint(self):
        with patch("agents.verifier.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"presentation_exchange_id": "pres-ex-id"}
            mock_post.return_value = mock_response

            result = self.verifier.request_verification("test-connection-id")

            assert result == "pres-ex-id"
            call_args = mock_post.call_args
            assert "/present-proof/send-request" in call_args[0][0]

    def test_request_verification_includes_connection_id(self):
        with patch("agents.verifier.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"presentation_exchange_id": "pres-ex-id"}
            mock_post.return_value = mock_response

            self.verifier.request_verification("test-connection-id")

            payload = mock_post.call_args[1]["json"]
            assert payload["connection_id"] == "test-connection-id"

    def test_request_verification_raises_on_non_200(self):
        with patch("agents.verifier.acapy.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Verification Failed"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Verification Failed"):
                self.verifier.request_verification("test-connection-id")

    def test_verify_verification_polls_until_verified(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = [
                {"state": "request_sent"},
                {"state": "done", "verified": "true"},
            ]
            mock_get.return_value = mock_response

            result = self.verifier.verify_verification("pres-ex-id")

            assert result is True
            assert mock_get.call_count >= 2

    def test_verify_verification_handles_boolean_verified(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "done", "verified": True}
            mock_get.return_value = mock_response

            result = self.verifier.verify_verification("pres-ex-id")

            assert result is True

    def test_verify_verification_raises_on_abandoned(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "abandoned"}
            mock_get.return_value = mock_response

            with pytest.raises(Exception, match="abandoned"):
                self.verifier.verify_verification("pres-ex-id")

    def test_verify_verification_raises_on_declined(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "declined"}
            mock_get.return_value = mock_response

            with pytest.raises(Exception, match="declined"):
                self.verifier.verify_verification("pres-ex-id")

    def test_verify_verification_raises_when_not_verified(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "done", "verified": False}
            mock_get.return_value = mock_response

            with pytest.raises(AssertionError, match="not successfully verified"):
                self.verifier.verify_verification("pres-ex-id")

    def test_verify_verification_times_out(self):
        with patch("agents.verifier.acapy.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "request_sent"}
            mock_get.return_value = mock_response

            with pytest.raises(TimeoutError, match="timed out"):
                self.verifier.verify_verification("pres-ex-id")
