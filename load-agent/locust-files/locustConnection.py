import os

from constants import standard_wait
from locust import SequentialTaskSet, task
from locustCustom import CustomLocust

WITH_MEDIATION = os.getenv("WITH_MEDIATION", "false").lower() in ("true", "1", "yes")
NUMBER_OF_CONNECTIONS = int(os.getenv("CONNECTIONS_PER_AGENT", 1))


class ConnectionUserBehaviour(SequentialTaskSet):
    def on_start(self):
        # Start up the client with or without mediation once per user
        self.client.startup(with_mediation=WITH_MEDIATION)
        self.invites = []

    def on_stop(self):
        self.client.shutdown()

    @task
    def establish_connections(self):
        if len(self.invites) < NUMBER_OF_CONNECTIONS:
            self.client.ensure_is_running()
            invite = self.client.issuer_getinvite()
            self.client.accept_invite(invite["invitation_url"])
            self.invites.append(invite)


class Issue(CustomLocust):
    tasks = [ConnectionUserBehaviour]
    wait_time = standard_wait
