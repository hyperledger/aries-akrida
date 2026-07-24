from abc import ABC, abstractmethod

from settings import Settings


class BaseHolder(ABC):
    """
    Base class for a credential holder/wallet agent.

    Holder agents receive and store credentials issued by issuers, and can
    present those credentials to verifiers for verification.
    """

    def __init__(self):
        super().__init__()
        self.label = "Test Holder"
        self.agent_url = Settings.HOLDER_URL
        self.headers = Settings.HOLDER_HEADERS | {"Content-Type": "application/json"}

    @abstractmethod
    def accept_invite(self, invitation_url, use_connection_did=False):
        """
        Accepts an out-of-band invitation to establish a connection.

        Args:
            invitation_url (str): The invitation URL from an issuer or verifier.
            use_connection_did (bool): Whether to use the connection DID for routing.

        Returns:
            str: The established connection ID.
        """

    @abstractmethod
    def receive_credential_prepare(self):
        """
        Prepares the holder to receive a credential offer.

        This may involve starting any necessary message listeners or
        preparing internal state. Implementations should ensure the agent
        is ready to receive an incoming credential offer.
        """

    @abstractmethod
    def receive_credential(self):
        """
        Accepts and stores a credential sent by an issuer.

        Called after the credential offer is received and should complete
        the credential exchange, storing the credential in the wallet.
        """

    @abstractmethod
    def presentation_exchange_prepare(self):
        """
        Prepares the holder for a presentation exchange.

        This may involve starting listeners for presentation requests
        from verifiers. Implementations should ensure the agent is ready
        to receive and process presentation requests.
        """

    @abstractmethod
    def presentation_exchange(self):
        """
        Retrieves and presents credentials in response to a verification request.

        Called after receiving a presentation request from a verifier.
        Should fetch the requested credentials from the wallet and send
        the presentation back to the verifier.
        """

    @abstractmethod
    def ping_mediator(self):
        """
        Sends a ping to the configured connection  or mediator to ensure connectivity.
        """

    @abstractmethod
    def delete_oob(self, id):
        """
        Deletes an out-of-band record by ID.

        Args:
            id (str): The ID of the OOB record to delete.
        """

    @abstractmethod
    def receive_message_prepare(self):
        """
        Prepares the holder to receive basic messages.

        Starts any necessary listeners for incoming messages sent via
        the connections protocol.
        """

    @abstractmethod
    def receive_message(self):
        """
        Processes an incoming basic message.

        Called when a message is received from a connected agent.
        Should handle the message appropriately (e.g., log, respond, etc.).
        """
