from gevent import lock as gevent_lock
from settings import Settings


class PortManager:
    def __init__(self):
        self.lock = gevent_lock.BoundedSemaphore()
        self.ports = list(range(Settings.START_PORT, Settings.END_PORT))

    def get_port(self):
        self.lock.acquire()
        try:
            if not self.ports:
                raise RuntimeError(
                    f"Port pool exhausted ({Settings.START_PORT}-{Settings.END_PORT}). "
                    f"All {len(range(Settings.START_PORT, Settings.END_PORT))} ports in use. "
                    "Increase END_PORT in settings."
                )
            port = self.ports.pop(0)
            return port
        finally:
            self.lock.release()

    def return_port(self, port):
        self.lock.acquire()
        try:
            self.ports.append(port)
        finally:
            self.lock.release()


portmanager = PortManager()
