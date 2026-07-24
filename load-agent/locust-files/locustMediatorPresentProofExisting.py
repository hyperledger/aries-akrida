import time

from constants import deviation_wait, standard_wait
from locust import task
from locustConnection import ConnectionUserBehaviour
from locustCustom import CustomLocust


class UserBehaviour(ConnectionUserBehaviour):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @task
    def receive_credential(self):
        self.client.ensure_is_running()
        for invite in self.invites:
            self.client.receive_credential(invite["connection_id"])
            time.sleep(deviation_wait())

    @task
    def get_verifier_invite(self):
        verifier_invite = self.client.verifier_getinvite()
        self.verifier_invite = verifier_invite

    @task
    def accept_verifier_invite(self):
        self.client.ensure_is_running()

        verifier_connection = self.client.accept_invite(self.verifier_invite["invitation_url"])
        if verifier_connection is not None:
            self.verifier_connection = verifier_connection

    @task
    def presentation_exchange(self):
        presentation_not_complete = True
        restart = False
        while presentation_not_complete:
            if not self.client.is_running() or restart:
                self.client.shutdown()
                self.on_start()

            restart = False

            try:
                presentation = self.client.presentation_exchange(self.verifier_invite["connection_id"])
                presentation_not_complete = False
            except AssertionError as e:
                if "JSONDecodeError" in presentation["result"]:
                    restart = True
                    pass
                else:
                    raise AssertionError("Error is : ", e) from e


class Issue(CustomLocust):
    tasks = [UserBehaviour]
    wait_time = standard_wait
