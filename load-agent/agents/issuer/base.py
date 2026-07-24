from abc import abstractmethod

from settings import Settings

from ..base import BaseAgent


class BaseIssuer(BaseAgent):
    """
    Base class for a credential issuer agent.

    Issuer agents create and send credentials to holders. They define the
    schema and credential definition that determines what attributes are
    included in the credential.
    """

    def __init__(self):
        super().__init__()
        self.label = "Test Issuer"
        self.agent_url = Settings.ISSUER_URL
        self.headers = Settings.ISSUER_HEADERS | {"Content-Type": "application/json"}
        self.schema_id = Settings.SCHEMA_ID
        self.cred_def_id = Settings.CRED_DEF_ID
        self.cred_attributes = Settings.CRED_ATTR

    @abstractmethod
    def issue_credential(self, connection_id):
        """
        Issues a credential to a connected holder.

        Args:
            connection_id (str): The established connection ID with the holder.
        """

    @abstractmethod
    def revoke_credential(self, connection_id, credential_exchange_id):
        """
        Revokes a previously issued credential.

        Args:
            connection_id (str): The connection ID of the holder.
            credential_exchange_id (str): The credential exchange ID to revoke.
        """
