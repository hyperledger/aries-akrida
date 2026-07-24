import time

from constants import deviation_wait, standard_wait
from locust import task
from locustConnection import ConnectionUserBehaviour
from locustCustom import CustomLocust


class UserBehaviour(ConnectionUserBehaviour):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = []

    @task
    def receive_credential(self):
        self.client.ensure_is_running()

        for invite in self.invites:
            self.credentials.append(self.client.receive_credential(invite["connection_id"]))
            time.sleep(deviation_wait())

    @task
    def revoke_credential(self):
        self.client.ensure_is_running()

        for credential in self.credentials:
            self.client.revoke_credential(credential)


class IssueRevoke(CustomLocust):
    tasks = [UserBehaviour]
    wait_time = standard_wait
