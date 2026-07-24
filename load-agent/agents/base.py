from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Base class for all agents. Subclasses must set `agent_url` and `headers`
    in their `__init__` to point to the correct agent's admin interface.
    """

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_invite(self):
        """
        Creates an invitation and returns the invitation URL and connection ID.

        Returns:
            dict: Contains 'invitation_url' and 'connection_id' for establishing a connection.
        """

    @abstractmethod
    def is_up(self):
        """
        Checks if the agent's admin interface is reachable and responding.

        Returns:
            bool: True if agent is up, False otherwise.
        """

    @abstractmethod
    def send_message(self, connection_id, msg):
        """
        Sends a basic message to a connected agent via the connections protocol.

        Args:
            connection_id (str): The established connection ID to send the message to.
            msg (str): The message content to send.
        """
