import time

import requests
from models import AnonCredsRevocation, CredentialProposalV1, IssueCredentialV1

from ..base_acapy import BaseAcapyAgent
from .base import BaseIssuer


class AcapyIssuer(BaseIssuer, BaseAcapyAgent):
    def issue_credential(self, connection_id):
        schema_parts = self.schema_id.split(":")

        payload = IssueCredentialV1(
            connection_id=connection_id,
            comment="Performance Issuance",
            cred_def_id=self.cred_def_id,
            issuer_did=self.cred_def_id.split(":")[0],
            schema_id=self.schema_id,
            schema_issuer_did=schema_parts[0],
            schema_name=schema_parts[2],
            schema_version=schema_parts[3],
            credential_proposal=CredentialProposalV1(attributes=self.cred_attributes),
        ).model_dump()

        r = requests.post(
            f"{self.agent_url}/issue-credential/send",
            json=payload,
            headers=self.headers,
        )
        if r.status_code != 200:
            raise Exception(r.content)

        cred_offer = r.json()

        return {
            "connection_id": cred_offer["connection_id"],
            "cred_ex_id": cred_offer["credential_exchange_id"],
        }

    def revoke_credential(self, connection_id, credential_exchange_id):
        time.sleep(1)
        payload = AnonCredsRevocation(
            comment="Load Test",
            connection_id=connection_id,
            cred_ex_id=credential_exchange_id,
            notify_version="v1_0",
        ).model_dump()
        r = requests.post(
            f"{self.agent_url}/revocation/revoke",
            json=payload,
            headers=self.headers,
        )
        if r.status_code != 200:
            raise Exception(r.content)
