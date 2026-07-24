import inspect
import time

from locust import events
from settings import Settings


def stopwatch(func):
    def wrapper(*args, **kwargs):
        # get task's function name
        previous_frame = inspect.currentframe().f_back
        file_name, _, task_name, _, _ = inspect.getframeinfo(previous_frame)

        start = time.time()
        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            total = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="TYPE",
                name=f"{file_name}_{task_name}",
                response_time=total,
                response_length=0,
                exception=e,
            )
        else:
            total = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="TYPE",
                name=f"{file_name}_{task_name}",
                response_time=total,
                response_length=0,  # size in bytes
                exception=None,
            )
        return result

    return wrapper


class CustomClient:
    def __init__(self, host):
        self.host = host

        self.issuerType = Settings.ISSUER_TYPE
        self.verifierType = Settings.VERIFIER_TYPE
        self.holderType = Settings.HOLDER_TYPE
        self.messageToSend = Settings.MESSAGE_TO_SEND

        # Load modules here depending on config
        self._load_issuer()
        self._load_verifier()
        self._load_holder()

    def _load_issuer(self):
        """Load issuer agent based on configuration"""
        issuer_classes = {
            "acapy": lambda: self._import_and_create("agents.issuer.acapy", "AcapyIssuer"),
            "acapy_v2": lambda: self._import_and_create("agents.issuer.acapy_v2", "AcapyIssuer"),
        }

        loader = issuer_classes.get(self.issuerType.lower())
        if loader:
            self.issuer = loader()
        else:
            raise ValueError(f"Unsupported issuer type: {self.issuerType}")

    def _load_verifier(self):
        """Load verifier agent based on configuration"""
        verifier_classes = {
            "acapy": lambda: self._import_and_create("agents.verifier.acapy", "AcapyVerifier"),
            "acapy_v2": lambda: self._import_and_create("agents.verifier.acapy_v2", "AcapyVerifier"),
        }

        loader = verifier_classes.get(self.verifierType.lower())
        if loader:
            self.verifier = loader()
        else:
            raise ValueError(f"Unsupported verifier type: {self.verifierType}")

    def _load_holder(self):
        """Load holder agent based on configuration"""
        holder_classes = {
            "credo": lambda: self._import_and_create("agents.holder.credo", "CredoHolder"),
        }

        loader = holder_classes.get(self.holderType.lower())
        if loader:
            self.holder = loader()
        else:
            raise ValueError(f"Unsupported holder type: {self.holderType}")

    def _import_and_create(self, module_path, class_name):
        """Dynamically import module and create instance"""
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        return cls()

    _locust_environment = None

    @stopwatch
    def startup(self, with_mediation=True, reinstantiate=False):
        self.holder.start(with_mediation=with_mediation, reinstantiate=reinstantiate)

    def shutdown(self):
        self.holder.shutdown()

    def ensure_is_running(self):
        self.holder.ensure_is_running()

    def is_running(self):
        return self.holder.is_running()

    @stopwatch
    def ping_mediator(self):
        self.holder.ping_mediator()

    @stopwatch
    def issuer_getinvite(self):
        return self.issuer.get_invite()

    @stopwatch
    def issuer_getliveness(self):
        return self.issuer.is_up()

    @stopwatch
    def delete_oob(self, id):
        self.holder.delete_oob(id)

    @stopwatch
    def accept_invite(self, invite, use_connection_did=False):
        return self.holder.accept_invite(invite, use_connection_did)

    @stopwatch
    def receive_credential(self, connection_id):
        self.holder.receive_credential_prepare()
        r = self.issuer.issue_credential(connection_id)
        self.holder.receive_credential()
        return r

    @stopwatch
    def verifier_getinvite(self):
        return self.verifier.get_invite()

    @stopwatch
    def presentation_exchange(self, connection_id):
        self.holder.presentation_exchange_prepare()

        pres_ex_id = self.verifier.request_verification(connection_id)
        self.holder.presentation_exchange()

        self.verifier.verify_verification(pres_ex_id)

    @stopwatch
    def verifier_connectionless_request(self):
        return self.verifier.create_connectionless_request()

    @stopwatch
    def revoke_credential(self, credential_exchange):
        self.issuer.revoke_credential(credential_exchange["connection_id"], credential_exchange["cred_ex_id"])

    @stopwatch
    def msg_client(self, connection_id):
        self.holder.receive_message_prepare()

        self.issuer.send_message(connection_id, self.messageToSend)

        self.holder.receive_message()
