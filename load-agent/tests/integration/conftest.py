import asyncio
import os
import subprocess
import time
from dataclasses import dataclass

import pytest
import requests

ACAPY_IMAGE = "aries-cloudagent-run:latest"
INDICIO_TESTNET_GENESIS = (
    "https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/"
    "genesis_files/pool_transactions_testnet_genesis"
)


@dataclass
class DockerAgent:
    container_id: str
    name: str
    admin_port: int
    http_port: int
    admin_api_key: str

    @property
    def admin_url(self) -> str:
        return f"http://localhost:{self.admin_port}"

    @property
    def headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.admin_api_key:
            headers["X-API-Key"] = self.admin_api_key
        return headers

    def is_ready(self, timeout: int = 120) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.admin_url}/status", headers=self.headers, timeout=5)
                if r.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(3)
        return False

    def get_status(self) -> dict:
        r = requests.get(f"{self.admin_url}/status", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def logs(self, tail: int = 50) -> str:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), self.container_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr

    def is_up(self) -> bool:
        try:
            r = requests.get(f"{self.admin_url}/status", headers=self.headers, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def get_taa_status(self) -> dict:
        r = requests.get(f"{self.admin_url}/ledger/taa", headers=self.headers)
        r.raise_for_status()
        return r.json().get("result", {})

    def accept_taa(self, text: str, version: str) -> None:
        r = requests.post(
            f"{self.admin_url}/ledger/taa/accept",
            headers=self.headers,
            json={"mechanism": "on_file", "text": text, "version": version},
        )
        if r.status_code not in (200, 201):
            raise Exception(f"Failed to accept TAA: {r.text}")

    def create_did(self) -> dict:
        r = requests.post(
            f"{self.admin_url}/wallet/did/create",
            headers=self.headers,
            json={"method": "sov", "options": {"key_type": "ed25519"}},
        )
        r.raise_for_status()
        return r.json().get("result", {})

    def set_public_did(self, did: str) -> None:
        r = requests.post(
            f"{self.admin_url}/wallet/did/public",
            headers=self.headers,
            params={"did": did},
        )
        if r.status_code not in (200, 201):
            raise Exception(f"Failed to set public DID: {r.text}")

    def get_public_did(self) -> dict | None:
        try:
            r = requests.get(f"{self.admin_url}/wallet/did/public", headers=self.headers)
            if r.status_code == 200:
                result = r.json().get("result")
                return result if result else None
        except requests.RequestException:
            pass
        return None

    def create_schema(self, schema_name: str, schema_version: str, attributes: list) -> str:
        r = requests.post(
            f"{self.admin_url}/schemas",
            headers=self.headers,
            json={
                "schema_name": schema_name,
                "schema_version": schema_version,
                "attributes": attributes,
            },
        )
        r.raise_for_status()
        return r.json().get("schema_id", "")

    def create_cred_def(self, schema_id: str, tag: str = "default", support_revocation: bool = False) -> str:
        r = requests.post(
            f"{self.admin_url}/credential-definitions",
            headers=self.headers,
            json={
                "schema_id": schema_id,
                "tag": tag,
                "support_revocation": support_revocation,
            },
        )
        r.raise_for_status()
        return r.json().get("credential_definition_id", "")

    def get_invite(self) -> dict:
        r = requests.post(
            f"{self.admin_url}/out-of-band/create-invitation",
            headers=self.headers,
            json={"handshake_protocols": ["https://didcomm.org/didexchange/1.1"]},
            params={"auto_accept": "true"},
        )
        r.raise_for_status()
        invitation = r.json()
        invi_msg_id = invitation.get("invi_msg_id", "")

        r = requests.get(
            f"{self.admin_url}/connections",
            headers=self.headers,
            params={"invitation_msg_id": invi_msg_id},
        )
        r.raise_for_status()
        connections = r.json().get("results", [])
        connection = connections[0] if connections else {}

        return {
            "invitation_url": invitation.get("invitation_url", ""),
            "connection_id": connection.get("connection_id", ""),
            "invitation": invitation.get("invitation", {}),
        }

    def receive_invitation(self, invitation: dict) -> str:
        r = requests.post(
            f"{self.admin_url}/out-of-band/receive-invitation",
            headers=self.headers,
            json=invitation,
            params={"auto_accept": "true"},
        )
        r.raise_for_status()
        return r.json().get("connection_id", "")

    def get_connection_state(self, connection_id: str) -> str:
        r = requests.get(
            f"{self.admin_url}/connections/{connection_id}",
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json().get("state", "")

    def wait_for_connection_active(self, connection_id: str, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            state = self.get_connection_state(connection_id)
            if state == "active":
                return True
            time.sleep(2)
        return False

    def issue_credential_v1(self, connection_id: str, cred_def_id: str, attributes: list) -> dict:
        r = requests.post(
            f"{self.admin_url}/issue-credential/send",
            headers=self.headers,
            json={
                "connection_id": connection_id,
                "cred_def_id": cred_def_id,
                "credential_preview": {
                    "type": "issue-credential/1.0/credential-preview",
                    "attributes": attributes,
                },
                "comment": "Integration test credential",
            },
        )
        r.raise_for_status()
        return r.json()

    def issue_credential_v2(
        self, connection_id: str, cred_def_id: str, attributes: list, anoncreds: bool = False
    ) -> dict:
        filter_type = "anoncreds" if anoncreds else "indy"
        r = requests.post(
            f"{self.admin_url}/issue-credential-2.0/send",
            headers=self.headers,
            json={
                "auto_issue": True,
                "connection_id": connection_id,
                "filter": {filter_type: {"cred_def_id": cred_def_id}},
                "credential_preview": {
                    "type": "issue-credential-2.0/2.0/credential-preview",
                    "attributes": attributes,
                },
            },
        )
        r.raise_for_status()
        return r.json()

    def revoke_credential(self, connection_id: str, cred_ex_id: str, anoncreds: bool = False) -> None:
        endpoint = "/anoncreds/revocation/revoke" if anoncreds else "/revocation/revoke"
        r = requests.post(
            f"{self.admin_url}{endpoint}",
            headers=self.headers,
            json={
                "connection_id": connection_id,
                "cred_ex_id": cred_ex_id,
                "notify_version": "v1_0",
            },
        )
        if r.status_code != 200:
            raise Exception(f"Failed to revoke: {r.text}")

    def cleanup(self):
        try:
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                capture_output=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, Exception):
            pass


async def onboard_to_ledger(agent: DockerAgent) -> dict:
    taa_status = agent.get_taa_status()
    if taa_status.get("taa_required") and not taa_status.get("taa_accepted"):
        agent.accept_taa(
            taa_status["taa_record"]["text"],
            taa_status["taa_record"]["version"],
        )

    did_info = agent.create_did()
    did = did_info["did"]
    verkey = did_info["verkey"]

    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://selfserve.indiciotech.io/nym",
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={
                "network": "testnet",
                "did": did,
                "verkey": verkey,
                "alias": None,
                "role": "ENDORSER",
            },
        ) as resp:
            if not resp.ok:
                body = await resp.text()
                raise Exception(f"Failed to write DID to ledger: {resp.status}; {body}")

    agent.set_public_did(did)

    return {"did": did, "verkey": verkey}


def start_acapy_container(
    name: str,
    wallet_name: str,
    admin_port: int,
    http_port: int,
    genesis_url: str,
    admin_api_key: str = "",
) -> DockerAgent:
    container_name = f"test-acapy-{name}-{int(time.time())}"

    env_vars = [
        "ACAPY_WALLET_NAME=" + wallet_name,
        "ACAPY_WALLET_KEY=test-wallet-key-32-characters-long",
        "ACAPY_WALLET_TYPE=askar",
        f"ACAPY_GENESIS_URL={genesis_url}",
        "ACAPY_ADMIN_INSECURE_MODE=true" if not admin_api_key else f"ACAPY_ADMIN_API_KEY={admin_api_key}",
        "ACAPY_LABEL=" + name,
        "ACAPY_AUTO_ACCEPT_INVITES=true",
        "ACAPY_AUTO_ACCEPT_REQUESTS=true",
        "ACAPY_AUTO_PING_CONNECTION=true",
        "ACAPY_DEBUG_CONNECTION=true",
        "ACAPY_AUTO_PROVISION=true",
    ]

    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--network=host",
    ]
    for env in env_vars:
        cmd.extend(["-e", env])

    cmd.append(ACAPY_IMAGE)
    cmd.append("start")
    cmd.append("--inbound-transport")
    cmd.append("http")
    cmd.append("0.0.0.0")
    cmd.append(str(http_port))
    cmd.append("--outbound-transport")
    cmd.append("http")
    cmd.append("--endpoint")
    cmd.append(f"http://0.0.0.0:{http_port}")
    cmd.append("--admin")
    cmd.append("0.0.0.0")
    cmd.append(str(admin_port))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise Exception(f"Failed to start container: {result.stderr}")

    container_id = result.stdout.strip()

    return DockerAgent(
        container_id=container_id,
        name=name,
        admin_port=admin_port,
        http_port=http_port,
        admin_api_key=admin_api_key,
    )


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def genesis_url():
    return INDICIO_TESTNET_GENESIS


@pytest.fixture(scope="session")
def admin_api_key():
    return os.getenv("TEST_ACAPY_ADMIN_API_KEY", "")


@pytest.fixture(scope="session")
def unique_prefix():
    import uuid

    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session")
def issuer_agent(genesis_url, admin_api_key, unique_prefix):
    agent = start_acapy_container(
        name=f"test-issuer-{unique_prefix}",
        wallet_name=f"test-issuer-wallet-{unique_prefix}",
        admin_port=8150,
        http_port=8151,
        genesis_url=genesis_url,
        admin_api_key=admin_api_key,
    )

    if not agent.is_ready(timeout=120):
        print(f"\n=== Container logs ===\n{agent.logs()}")
        agent.cleanup()
        pytest.fail("Issuer agent failed to start - check logs above")

    yield agent

    agent.cleanup()


@pytest.fixture(scope="session")
def holder_agent(genesis_url, admin_api_key, unique_prefix):
    agent = start_acapy_container(
        name=f"test-holder-{unique_prefix}",
        wallet_name=f"test-holder-wallet-{unique_prefix}",
        admin_port=9160,
        http_port=9161,
        genesis_url=genesis_url,
        admin_api_key=admin_api_key,
    )

    assert agent.is_ready(timeout=120), "Holder agent failed to start"

    yield agent

    agent.cleanup()


@pytest.fixture(scope="session")
def ledger_config(issuer_agent):
    did_info = asyncio.run(onboard_to_ledger(issuer_agent))

    schema_id = issuer_agent.create_schema(
        schema_name=f"TestSchema-{int(time.time())}",
        schema_version="1.0",
        attributes=["name", "email"],
    )

    cred_def_id = issuer_agent.create_cred_def(schema_id)

    return {
        "issuer_did": did_info["did"],
        "verkey": did_info["verkey"],
        "schema_id": schema_id,
        "cred_def_id": cred_def_id,
    }


@pytest.fixture
def established_connection(issuer_agent, holder_agent):
    issuer_invite = issuer_agent.get_invite()

    holder_conn_id = holder_agent.receive_invitation(issuer_invite["invitation"])

    assert issuer_agent.wait_for_connection_active(issuer_invite["connection_id"], timeout=60), (
        "Connection did not become active"
    )
    assert holder_agent.wait_for_connection_active(holder_conn_id, timeout=60), (
        "Connection did not become active on holder"
    )

    return {
        "issuer_connection_id": issuer_invite["connection_id"],
        "holder_connection_id": holder_conn_id,
    }


@pytest.fixture
def test_attributes():
    return [
        {"name": "name", "value": "Test User"},
        {"name": "email", "value": "test@example.com"},
    ]
