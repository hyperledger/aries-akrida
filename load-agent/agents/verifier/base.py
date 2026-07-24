import os
from abc import abstractmethod

from settings import Settings

from ..base import BaseAgent


class BaseVerifier(BaseAgent):
    """
    Base class for a credential verifier agent.

    Verifier agents request holders to present credentials and verify
    that the presentations meet the specified requirements.
    """

    def __init__(self):
        super().__init__()
        self.label = "Test Verifier"
        self.agent_url = Settings.VERIFIER_URL
        self.headers = Settings.VERIFIER_HEADERS | {"Content-Type": "application/json"}
        self.verifiedTimeoutSeconds = Settings.VERIFIED_TIMEOUT_SECONDS
        self.schema_id = Settings.SCHEMA_ID
        self.cred_def_id = Settings.CRED_DEF_ID
        self.cred_attributes = Settings.CRED_ATTR

        env_val = os.getenv("VERIFIED_TIMEOUT_SECONDS", "NOT SET")
        print(
            f"[{self.__class__.__name__}] VERIFIED_TIMEOUT_SECONDS = "
            f"{self.verifiedTimeoutSeconds} (from env: {env_val})"
        )

    @abstractmethod
    def request_verification(self, connection_id):
        """
        Sends a presentation request to a holder to verify their credentials.

        Args:
            connection_id (str): The established connection ID with the holder.

        Returns:
            str: The presentation exchange ID for tracking the verification.
        """

    @abstractmethod
    def verify_verification(self, presentation_exchange_id):
        """
        Checks the status and result of a presentation exchange.

        Args:
            presentation_exchange_id (str): The ID returned from request_verification.

        Returns:
            bool: True if the presentation was valid and verified.

        Raises:
            Exception: If verification fails or times out.
        """
