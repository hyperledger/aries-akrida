import time
from json.decoder import JSONDecodeError

import requests
from models import (
    AnonCredsFilter,
    AnonCredsPresReq,
    Filter,
    IndyFilter,
    IndyPresReq,
    ProofRequest,
)
from models import RequestPresentationV2 as RequestPresentation
from settings import Settings

from ..base_acapy import BaseAcapyAgent
from .base import BaseVerifier


class AcapyVerifier(BaseVerifier, BaseAcapyAgent):
    def __init__(self):
        super().__init__()
        self.cred_attributes = Settings.CRED_ATTR
        if Settings.IS_ANONCREDS:
            self.filter = AnonCredsFilter(anoncreds=Filter(cred_def_id=self.cred_def_id))
        else:
            self.filter = IndyFilter(indy=Filter(cred_def_id=self.cred_def_id))

    def get_presentation_request(self):
        proof_request = ProofRequest(
            name="PerfScore",
            requested_attributes={
                item["name"]: {"name": item["name"], "restrictions": [{"cred_def_id": self.cred_def_id}]}
                for item in self.cred_attributes
            },
            requested_predicates={},
            version="1.0",
        ).model_dump()

        if Settings.IS_ANONCREDS:
            return AnonCredsPresReq(anoncreds=proof_request)
        else:
            return IndyPresReq(indy=proof_request)

    def create_connectionless_request(self):
        r = requests.post(
            f"{self.agent_url}/present-proof-2.0/create-request",
            headers=self.headers,
            json=RequestPresentation(
                presentation_request=self.get_presentation_request(),
            ).model_dump(),
        )
        if r.status_code != 200:
            raise Exception("Request was not successful: ", r.content)
        try:
            return r.json()
        except JSONDecodeError:
            raise Exception("Encountered JSONDecodeError while parsing the request: ", r.text) from None

    def request_verification(self, connection_id):

        r = requests.post(
            f"{self.agent_url}/present-proof-2.0/send-request",
            headers=self.headers,
            json=RequestPresentation(
                connection_id=connection_id,
                presentation_request=self.get_presentation_request(),
            ).model_dump(),
        )
        if r.status_code != 200:
            raise Exception("Request was not successful: ", r.content)

        try:
            return r.json()["pres_ex_id"]
        except JSONDecodeError:
            raise Exception("Encountered JSONDecodeError while parsing the request: ", r.text) from None

    def verify_verification(self, pres_ex_id):
        try:
            for _ in range(self.verifiedTimeoutSeconds):
                r = requests.get(
                    f"{self.agent_url}/present-proof-2.0/records/{pres_ex_id}",
                    headers=self.headers,
                )
                if r.status_code != 200:
                    raise Exception(f"Failed to get presentation record: status {r.status_code}, body: {r.text}")
                presentation_json = r.json()
                state = presentation_json["state"]
                if state == "done" or state == "abandoned":
                    break
                if state not in ("request-sent", "presentation-received"):
                    break
                time.sleep(1)
            else:
                raise TimeoutError(
                    f"Presentation verification timed out after {self.verifiedTimeoutSeconds}s, "
                    f"last state: '{presentation_json['state']}'"
                )

            state = presentation_json["state"]

            if state == "done":
                verified = presentation_json.get("verified")
                if isinstance(verified, str):
                    verified = verified.lower() == "true"
            elif state == "presentation-received":
                r_verify = requests.post(
                    f"{self.agent_url}/present-proof-2.0/records/{pres_ex_id}/verify-presentation",
                    headers=self.headers,
                )
                if r_verify.status_code != 200:
                    raise Exception(
                        f"Failed to verify presentation (state: '{state}'): {r_verify.text}. "
                        f"Holder likely has no credential matching cred_def_id={self.cred_def_id}, "
                        f"or format mismatch (IS_ANONCREDS={Settings.IS_ANONCREDS})"
                    )
                verified = r_verify.json()["verified"]
            elif state == "abandoned":
                raise Exception(f"Presentation exchange {pres_ex_id} is in abandoned state")
            else:
                raise Exception(f"Unexpected presentation state after polling: '{state}'")

            if verified is not True:
                raise AssertionError(f"Presentation was not successfully verified. Presentation in state {state}")

            return True

        except JSONDecodeError as e:
            resp_text = r.text if "r" in locals() else "N/A"
            raise Exception(
                f"Encountered JSONDecodeError while getting the presentation record: {e}. Response text: {resp_text}"
            ) from e
