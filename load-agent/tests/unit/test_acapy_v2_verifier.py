import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestAcapyV2Verifier:
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
        monkeypatch.setattr(Settings, "IS_ANONCREDS", False)

        from agents.verifier.acapy_v2 import AcapyVerifier

        self.verifier = AcapyVerifier()
        self.verifier.agent_url = "http://localhost:8150"
        self.verifier.headers = {"X-API-Key": "test-key", "Content-Type": "application/json"}
        self.verifier.cred_attributes = [{"name": "score", "value": "100"}]

    def test_verifier_has_correct_base_url(self):
        assert self.verifier.agent_url == "http://localhost:8150"

    def test_uses_indy_filter_when_not_anoncreds(self):
        assert "IndyFilter" in type(self.verifier.filter).__name__

    def test_get_presentation_request_includes_attributes(self):
        proof_request = self.verifier.get_presentation_request()
        assert "score" in str(proof_request)

    def test_create_connectionless_request_correct_endpoint(self):
        with patch("agents.verifier.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pres_ex_id": "test-id"}
            mock_post.return_value = mock_response

            self.verifier.create_connectionless_request()

            call_args = mock_post.call_args
            assert "/present-proof-2.0/create-request" in call_args[0][0]

    def test_create_connectionless_request_raises_on_non_200(self):
        with patch("agents.verifier.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Server Error"):
                self.verifier.create_connectionless_request()

    def test_request_verification_correct_endpoint(self):
        with patch("agents.verifier.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pres_ex_id": "pres-ex-v2"}
            mock_post.return_value = mock_response

            result = self.verifier.request_verification("test-connection-id")

            assert result == "pres-ex-v2"
            call_args = mock_post.call_args
            assert "/present-proof-2.0/send-request" in call_args[0][0]

    def test_request_verification_includes_connection_id(self):
        with patch("agents.verifier.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pres_ex_id": "pres-ex-v2"}
            mock_post.return_value = mock_response

            self.verifier.request_verification("test-connection-id")

            payload = mock_post.call_args[1]["json"]
            assert payload["connection_id"] == "test-connection-id"

    def test_request_verification_raises_on_non_200(self):
        with patch("agents.verifier.acapy_v2.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.content = b"V2 Verification Failed"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="V2 Verification Failed"):
                self.verifier.request_verification("test-connection-id")

    def test_verify_verification_polls_done_state(self):
        with patch("agents.verifier.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = [
                {"state": "request-sent"},
                {"state": "done", "verified": "true"},
            ]
            mock_get.return_value = mock_response

            result = self.verifier.verify_verification("pres-ex-v2")

            assert result is True

    def test_verify_verification_polls_abandoned_state(self):
        with patch("agents.verifier.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "abandoned"}
            mock_get.return_value = mock_response

            with pytest.raises(Exception, match="abandoned"):
                self.verifier.verify_verification("pres-ex-v2")

    def test_verify_verification_handles_auto_verified_state(self):
        with patch("agents.verifier.acapy_v2.requests.get") as mock_get:
            get_response = MagicMock()
            get_response.status_code = 200
            get_response.json.side_effect = [
                {"state": "request-sent"},
                {"state": "done", "verified": "true"},
            ]
            mock_get.return_value = get_response

            result = self.verifier.verify_verification("pres-ex-v2")

            assert result is True

    def test_verify_verification_times_out(self):
        with patch("agents.verifier.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "request-sent"}
            mock_get.return_value = mock_response

            with pytest.raises(TimeoutError, match="timed out"):
                self.verifier.verify_verification("pres-ex-v2")

    def test_verify_verification_raises_on_not_verified(self):
        with patch("agents.verifier.acapy_v2.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "done", "verified": "false"}
            mock_get.return_value = mock_response

            with pytest.raises(AssertionError, match="not successfully verified"):
                self.verifier.verify_verification("pres-ex-v2")
