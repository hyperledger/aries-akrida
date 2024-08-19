from locust import SequentialTaskSet, task, User, between
from locustClient import CustomClient
import time
import inspect
import json

import fcntl
import os
import signal

WITH_MEDIATION = os.getenv("WITH_MEDIATION")

class CustomLocust(User):
    abstract = True
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.client = CustomClient(self.host)

class UserBehaviour(SequentialTaskSet):
    def on_start(self):
        self.client.startup(withMediation=bool(WITH_MEDIATION))

    def on_stop(self):
        try:
            self.client.issuer_cleanup(self.invite["connection_id"])
        except Exception as e:
            raise Exception(f"Failed cleaning up connections on issuer side: {str(e)}")
        self.client.shutdown()

    @task
    def get_invite(self):
        invite = self.client.issuer_getinvite()
        self.invite = invite

    @task
    def accept_invite(self):
        self.client.ensure_is_running()

        connection = self.client.accept_invite(self.invite['invitation_url'])
        self.connection = connection

    @task
    def receive_credential(self):
        self.client.ensure_is_running()

        self.credential = self.client.receive_credential(self.invite['connection_id'])

    @task
    def revoke_credential(self):
        self.client.ensure_is_running()

        self.client.revoke_credential(self.credential)

    @task
    def issuer_cleanup(self):
        self.client.issuer_cleanup(self.invite["connection_id"])

class IssueRevoke(CustomLocust):
    tasks = [UserBehaviour]
    wait_time = between(float(os.getenv('LOCUST_MIN_WAIT',0.1)), float(os.getenv('LOCUST_MAX_WAIT',1)))
#    host = "example.com"
