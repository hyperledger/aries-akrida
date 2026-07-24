import os
import time

from constants import deviation_wait, standard_wait
from locust import task
from locustConnection import ConnectionUserBehaviour
from locustCustom import CustomLocust

WITH_MEDIATION = os.getenv("WITH_MEDIATION", "false").lower() in ("true", "1", "yes")


class UserBehaviour(ConnectionUserBehaviour):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @task(3)
    def receive_credential(self):
        self.client.ensure_is_running()

        for invite in self.invites:
            self.client.receive_credential(invite["connection_id"])
            time.sleep(deviation_wait())

    @task(1)
    def presentation_exchange(self):
        self.client.ensure_is_running()

        # Need connection id
        for invite in self.invites:
            self.client.presentation_exchange(invite["connection_id"])
            time.sleep(deviation_wait())


class Issue(CustomLocust):
    tasks = [UserBehaviour]
    wait_time = standard_wait
