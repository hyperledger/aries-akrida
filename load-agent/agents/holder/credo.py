import json
import os
import select
import signal
import subprocess
import sys

from portmanager import portmanager
from settings import Settings

from .base import BaseHolder


class CredoHolder(BaseHolder):
    def __init__(self):
        super().__init__()
        self.agent = None
        self.port = None
        self.agent_config = None
        self.errors = 0
        self.with_mediation = None

    def start(self, with_mediation=True, reinstantiate=False):
        if self.port is not None:
            portmanager.return_port(self.port)
            self.port = None

        try:
            self.port = portmanager.get_port()
            self.errors = 0
            self.agent = subprocess.Popen(
                ["node", "--max-old-space-size=128", "dist/agent.js"],
                bufsize=0,
                universal_newlines=True,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=sys.stderr,
                shell=False,
            )

            self.run_command(
                {
                    "cmd": "start",
                    "withMediation": with_mediation,
                    "port": self.port,
                    "agentConfig": self.agent_config if reinstantiate else None,
                }
            )

            self.agent_config = self.read_json_line()["result"]

            if self.agent is None or self.agent.poll() is not None:
                raise Exception("unable to start")
        except Exception as e:
            self.shutdown()
            raise e

    def _cleanup_agent(self):
        if self.agent is None:
            return
        try:
            self.agent.stdin.write(json.dumps({"cmd": "shutdown"}))
            self.agent.stdin.write("\n")
            self.agent.stdin.flush()
            self.agent.communicate(timeout=Settings.SHUTDOWN_TIMEOUT_SECONDS)
        except Exception:
            pass
        finally:
            try:
                os.kill(self.agent.pid, signal.SIGTERM)
            except Exception:
                pass
            self.agent = None

    def shutdown(self):
        if self.port:
            portmanager.return_port(self.port)
            self.port = None
        self._cleanup_agent()

    def run_command(self, command):
        try:
            self.agent.stdin.write(json.dumps(command))
            self.agent.stdin.write("\n")
            self.agent.stdin.flush()
        except Exception as e:
            self.shutdown()
            raise e

    def read_json_line(self):
        try:
            while True:
                line = None
                raw_line_stdout = None

                if self.agent.stdout.closed:
                    raise Exception("Stdout is closed.")

                q = select.poll()
                q.register(self.agent.stdout, select.POLLIN)

                if q.poll(Settings.READ_TIMEOUT_SECONDS * 1000):
                    raw_line_stdout = self.agent.stdout.readline()

                    if not raw_line_stdout:
                        raise Exception("EOF reached or empty line received.")

                    try:
                        line = json.loads(raw_line_stdout)
                    except json.JSONDecodeError:
                        print(f"{raw_line_stdout.strip()}", file=sys.stderr)
                        continue

                    if q.poll(0):
                        continue
                else:
                    raise Exception("Read Timeout")

                if not line or not isinstance(line, dict):
                    print(line, file=sys.stderr)
                    continue

                if line.get("error") != 0:
                    raise Exception("Error encountered within load testing agent: ", line)

                return line

        except Exception as e:
            self.errors += 1
            if self.errors > Settings.ERRORS_BEFORE_RESTART:
                self.shutdown()
            raise e

    def ensure_is_running(self):
        if not self.agent:
            self.start()
        elif self.agent.poll() is None:
            if self.agent.stdout.closed or self.agent.stdin.closed:
                self.start()
            else:
                return True
        else:
            self.start()

    def is_running(self):
        if not self.agent:
            return False
        elif self.agent.poll() is None:
            if self.agent.stdout.closed or self.agent.stdin.closed:
                return False
            else:
                return True
        else:
            return False

    def accept_invite(self, invitation_url, use_connection_did=False):
        try:
            if use_connection_did:
                self.run_command({"cmd": "receiveInvitationConnectionDid", "invitationUrl": invitation_url})
            else:
                self.run_command({"cmd": "receiveInvitation", "invitationUrl": invitation_url})
        except Exception:
            self.run_command({"cmd": "receiveInvitation", "invitationUrl": invitation_url})

        line = self.read_json_line()

        if line.get("connection") is None:
            return None

        return line["connection"]

    def receive_credential_prepare(self):
        self.run_command({"cmd": "receiveCredential"})

    def receive_credential(self):
        self.read_json_line()

    def presentation_exchange_prepare(self):
        self.run_command({"cmd": "presentationExchange"})

    def presentation_exchange(self):
        return self.read_json_line()

    def ping_mediator(self):
        self.run_command({"cmd": "ping_mediator"})
        self.read_json_line()

    def delete_oob(self, id):
        self.run_command({"cmd": "deleteOobRecordById", "id": id})
        self.read_json_line()

    def receive_message_prepare(self):
        self.run_command({"cmd": "receiveMessage"})

    def receive_message(self):
        self.read_json_line()
