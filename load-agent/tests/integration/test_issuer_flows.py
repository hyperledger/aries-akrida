import pytest


@pytest.mark.integration
class TestAcapyIssuerIntegration:
    def test_issuer_is_up(self, issuer_agent):
        assert issuer_agent.is_up() is True

    def test_issuer_has_public_did(self, ledger_config):
        assert ledger_config["issuer_did"]
        assert len(ledger_config["issuer_did"]) >= 16
        assert len(ledger_config["verkey"]) == 44

    def test_issuer_has_schema_and_cred_def(self, ledger_config):
        assert ledger_config["schema_id"]
        assert ledger_config["cred_def_id"]
        assert ":2:" in ledger_config["schema_id"]
        assert ":3:CL:" in ledger_config["cred_def_id"]

    def test_issuer_can_create_invitation(self, issuer_agent):
        invite = issuer_agent.get_invite()

        assert invite["connection_id"]
        assert invite["invitation_url"]
        assert "oob=" in invite["invitation_url"]

    def test_holder_can_receive_invitation(self, issuer_agent, holder_agent):
        issuer_invite = issuer_agent.get_invite()
        holder_conn_id = holder_agent.receive_invitation(issuer_invite["invitation"])

        assert holder_conn_id
        assert holder_conn_id != issuer_invite["connection_id"]


@pytest.mark.integration
class TestCredentialIssuanceV1:
    @pytest.mark.skip(reason="V1 issuance endpoint not available in this ACA-Py version")
    def test_credential_issuance_v1(
        self, issuer_agent, holder_agent, ledger_config, established_connection, test_attributes
    ):
        result = issuer_agent.issue_credential_v1(
            connection_id=established_connection["issuer_connection_id"],
            cred_def_id=ledger_config["cred_def_id"],
            attributes=test_attributes,
        )

        assert result["connection_id"] == established_connection["issuer_connection_id"]
        assert result["credential_exchange_id"]

        cred_ex_state = result.get("state", "")
        assert cred_ex_state in ["credential_acked", "offer_sent", "request_received"]


@pytest.mark.integration
class TestCredentialIssuanceV2:
    def test_credential_issuance_v2_indy(
        self, issuer_agent, holder_agent, ledger_config, established_connection, test_attributes
    ):
        result = issuer_agent.issue_credential_v2(
            connection_id=established_connection["issuer_connection_id"],
            cred_def_id=ledger_config["cred_def_id"],
            attributes=test_attributes,
            anoncreds=False,
        )

        assert result["connection_id"] == established_connection["issuer_connection_id"]
        assert result["cred_ex_id"]

    @pytest.mark.skip(reason="Anoncreds requires ACA-Py configured with anoncreds plugin and did:indy format cred defs")
    def test_credential_issuance_v2_anoncreds(
        self, issuer_agent, holder_agent, ledger_config, established_connection, test_attributes
    ):
        result = issuer_agent.issue_credential_v2(
            connection_id=established_connection["issuer_connection_id"],
            cred_def_id=ledger_config["cred_def_id"],
            attributes=test_attributes,
            anoncreds=True,
        )

        assert result["connection_id"] == established_connection["issuer_connection_id"]
        assert result["cred_ex_id"]


@pytest.mark.integration
class TestCredentialRevocation:
    @pytest.mark.skip(reason="V1 issuance endpoint not available in this ACA-Py version")
    def test_credential_revocation_v1(self, issuer_agent, ledger_config, established_connection, test_attributes):
        result = issuer_agent.issue_credential_v1(
            connection_id=established_connection["issuer_connection_id"],
            cred_def_id=ledger_config["cred_def_id"],
            attributes=test_attributes,
        )

        cred_ex_id = result.get("credential_exchange_id")
        assert cred_ex_id

        issuer_agent.revoke_credential(
            connection_id=established_connection["issuer_connection_id"],
            cred_ex_id=cred_ex_id,
            anoncreds=False,
        )

    @pytest.mark.skip(reason="Revocation requires cred_def with support_revocation=True and tails server")
    def test_credential_revocation_v2_indy(self, issuer_agent, ledger_config, established_connection, test_attributes):
        result = issuer_agent.issue_credential_v2(
            connection_id=established_connection["issuer_connection_id"],
            cred_def_id=ledger_config["cred_def_id"],
            attributes=test_attributes,
            anoncreds=False,
        )

        cred_ex_id = result.get("cred_ex_id")
        assert cred_ex_id

        issuer_agent.revoke_credential(
            connection_id=established_connection["issuer_connection_id"],
            cred_ex_id=cred_ex_id,
            anoncreds=False,
        )


@pytest.mark.integration
class TestConnectionManagement:
    def test_multiple_connections(self, issuer_agent, holder_agent, unique_prefix):
        connections = []
        for _ in range(3):
            invite = issuer_agent.get_invite()
            holder_conn_id = holder_agent.receive_invitation(invite["invitation"])
            connections.append(invite["connection_id"])
            assert holder_conn_id

        for conn_id in connections:
            assert issuer_agent.wait_for_connection_active(conn_id, timeout=30)


@pytest.mark.integration
class TestLedgerOperations:
    def test_issuer_did_on_ledger(self, ledger_config, issuer_agent):
        public_did = issuer_agent.get_public_did()
        assert public_did is not None
        assert public_did["did"] == ledger_config["issuer_did"]
        assert public_did["verkey"] == ledger_config["verkey"]

    def test_schema_registered(self, ledger_config):
        assert ":2:" in ledger_config["schema_id"]
        parts = ledger_config["schema_id"].split(":")
        assert len(parts) >= 4

    def test_cred_def_registered(self, ledger_config):
        parts = ledger_config["cred_def_id"].split(":")
        assert len(parts) >= 5
        assert parts[0] == ledger_config["issuer_did"]
