import time
from json.decoder import JSONDecodeError

import requests
from models import ProofRequest, RequestPresentationV1
from settings import Settings

from ..base_acapy import BaseAcapyAgent
from .base import BaseVerifier


class AcapyVerifier(BaseVerifier, BaseAcapyAgent):
    def __init__(self):
        super().__init__()
        self.proof_request = ProofRequest(
            name="PerfScore",
            requested_attributes={item["name"]: {"name": item["name"]} for item in Settings.CRED_ATTR},
            requested_predicates={},
            version="1.0",
        )

    def create_connectionless_request(self):
        # Calling verification agent

        # API call to /present-proof/create-request
        r = requests.post(
            f"{self.agent_url}/present-proof/create-request",
            json=RequestPresentationV1(
                comment="Performance Verification", proof_request=self.proof_request
            ).model_dump(),
            headers=self.headers,
        )

        try:
            if r.status_code != 200:
                raise Exception("Request was not successful: ", r.content)
            presentation_request = r.json()
        except JSONDecodeError:
            raise Exception("Encountered JSONDecodeError while parsing the request: ", r.text) from None

        return presentation_request

    def request_verification(self, connection_id):
        # From verification side
        # Might need to change nonce
        # TO DO: Generalize schema parts
        r = requests.post(
            f"{self.agent_url}/present-proof/send-request",
            json=RequestPresentationV1(
                comment="Performance Verification",
                connection_id=connection_id,
                proof_request=self.proof_request,
            ).model_dump(),
            headers=self.headers,
        )

        try:
            if r.status_code != 200:
                raise Exception("Request was not successful: ", r.content)
            presentation_request = r.json()
        except JSONDecodeError:
            raise Exception("Encountered JSONDecodeError while parsing the request: ", r.text) from None

        return presentation_request["presentation_exchange_id"]

    def verify_verification(self, presentation_exchange_id):
        try:
            for _ in range(self.verifiedTimeoutSeconds):
                r = requests.get(
                    f"{self.agent_url}/present-proof/records/{presentation_exchange_id}",
                    headers=self.headers,
                )
                if r.status_code != 200:
                    raise Exception(f"Failed to get presentation record: status {r.status_code}, body: {r.text}")
                presentation_record = r.json()
                presentation_state = presentation_record["state"]

                if presentation_state in ("verified", "done", "abandoned", "declined"):
                    break
                if presentation_state not in (
                    "request_sent",
                    "request_received",
                    "presentation_sent",
                    "presentation_received",
                ):
                    break
                time.sleep(1)
            else:
                raise TimeoutError(
                    f"Presentation verification timed out after {self.verifiedTimeoutSeconds}s, "
                    f"last state: '{presentation_state}'"
                )

            presentation_state = presentation_record["state"]

            if presentation_state == "abandoned":
                raise Exception(f"Presentation exchange {presentation_exchange_id} is in abandoned state")
            if presentation_state == "declined":
                raise Exception(f"Presentation exchange {presentation_exchange_id} is in declined state")

            verified = presentation_record.get("verified")
            if isinstance(verified, str):
                verified = verified.lower() == "true"
            if verified is not True:
                raise AssertionError(
                    f"Presentation was not successfully verified. Presentation in state {presentation_state}"
                )

        except JSONDecodeError as e:
            resp_text = r.text if "r" in locals() else "N/A"
            raise Exception(
                f"Encountered JSONDecodeError while getting the presentation record: {e}. Response text: {resp_text}"
            ) from e

        return True
