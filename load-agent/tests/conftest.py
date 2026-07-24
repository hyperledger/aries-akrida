import asyncio
import json
import os
import time
from dataclasses import dataclass

import pytest
import requests

try:
    from aiohttp import ClientSession
except ImportError:
    ClientSession = None

INDICIO_TESTNET_GENESIS = (
    "https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/"
    "genesis_files/pool_transactions_testnet_genesis"
)

ACAPY_IMAGE = "ghcr.io/hyperledger/aries-cloudagent-python:py3.9-0.12-lts"
ADMIN_PORT = 8150
HTTP_PORT = 8151


@dataclass
class LedgerConfig:
    issuer_did: str
    verkey: str
    schema_id: str
    cred_def_id: str


class AcapyTestAgent:
    def __init__(
        self,
        container_id: str,
        admin_port: int,
        http_port: int,
        admin_api_key: str = "",
    ):
        self.container_id = container_id
        self.admin_port = admin_port
        self.http_port = http_port
        self.admin_api_key = admin_api_key
        self.base_url = f"http://localhost:{admin_port}"
        self.headers = {
            "Content-Type": "application/json",
        }
        if admin_api_key:
            self.headers["X-API-Key"] = admin_api_key

    def is_ready(self, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.base_url}/status", headers=self.headers, timeout=5)
                if r.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False

    def get_wallet_did(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/wallet/did", headers=self.headers)
            if r.status_code == 200:
                results = r.json().get("results", [])
                return results[0] if results else None
        except requests.RequestException:
            pass
        return None

    def create_did(self) -> dict:
        r = requests.post(
            f"{self.base_url}/wallet/did/create",
            headers=self.headers,
            json={"method": "sov", "options": {"key_type": "ed25519"}},
        )
        r.raise_for_status()
        return r.json().get("result", {})

    def set_public_did(self, did: str) -> None:
        requests.post(
            f"{self.base_url}/wallet/did/public",
            headers=self.headers,
            params={"did": did},
        )

    def get_taa_status(self) -> dict:
        r = requests.get(f"{self.base_url}/ledger/taa", headers=self.headers)
        r.raise_for_status()
        return r.json().get("result", {})

    def accept_taa(self, text: str, version: str) -> None:
        requests.post(
            f"{self.base_url}/ledger/taa/accept",
            headers=self.headers,
            json={
                "mechanism": "on_file",
                "text": text,
                "version": version,
            },
        )

    def create_schema(self, schema_name: str, schema_version: str, attributes: list) -> str:
        r = requests.post(
            f"{self.base_url}/schemas",
            headers=self.headers,
            json={
                "schema_name": schema_name,
                "schema_version": schema_version,
                "attributes": attributes,
            },
        )
        r.raise_for_status()
        return r.json().get("schema_id", "")

    def create_cred_def(self, schema_id: str, tag: str = "default") -> str:
        r = requests.post(
            f"{self.base_url}/credential-definitions",
            headers=self.headers,
            json={
                "schema_id": schema_id,
                "tag": tag,
                "support_revocation": False,
            },
        )
        r.raise_for_status()
        return r.json().get("credential_definition_id", "")

    def get_invite(self) -> dict:
        r = requests.post(
            f"{self.base_url}/out-of-band/create-invitation",
            headers=self.headers,
            json={"handshake_protocols": ["https://didcomm.org/didexchange/1.1"]},
            params={"auto_accept": "true"},
        )
        r.raise_for_status()
        invitation = r.json()
        invi_msg_id = invitation.get("invi_msg_id", "")

        r = requests.get(
            f"{self.base_url}/connections",
            headers=self.headers,
            params={"invitation_msg_id": invi_msg_id},
        )
        r.raise_for_status()
        connection = r.json().get("results", [{}])[0]

        return {
            "invitation_url": invitation.get("invitation_url", ""),
            "connection_id": connection.get("connection_id", ""),
            "invitation": invitation.get("invitation", {}),
        }

    def is_up(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/status", headers=self.headers, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def cleanup(self) -> None:
        pass


class SelfServeClient:
    def __init__(self):
        self.session: ClientSession | None = None

    async def onboard(self, did: str, verkey: str, network: str = "testnet") -> dict:
        if not self.session:
            self.session = ClientSession()

        url = "https://selfserve.indiciotech.io/nym"
        async with self.session.post(
            url,
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={
                "network": network,
                "did": did,
                "verkey": verkey,
                "alias": None,
                "role": "ENDORSER",
            },
        ) as resp:
            if not resp.ok:
                body = await resp.text()
                raise Exception(f"Failed to write DID: {resp.status}; {body}")
            body = await resp.text()
            try:
                import json

                return json.loads(body) if body else {}
            except json.JSONDecodeError:
                return {}

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


def pytest_addoption(parser):
    parser.addoption(
        "--use-docker",
        action="store_true",
        default=False,
        help="Run integration tests with real Docker ACA-Py agents",
    )
    parser.addoption(
        "--use-real-ledger",
        action="store_true",
        default=False,
        help="Use real Indicio TestNet instead of mocked ledger",
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
def test_wallet_name():
    import uuid

    return f"test-issuer-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_schema_name():
    import uuid

    return f"TestSchema-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def admin_api_key():
    return os.getenv("TEST_ACAPY_ADMIN_API_KEY", "test-api-key")


@pytest.fixture(scope="session")
def use_docker(request):
    return request.config.getoption("--use-docker")


@pytest.fixture(scope="session")
def use_real_ledger(request):
    return request.config.getoption("--use-real-ledger")


@pytest.fixture(scope="session")
def acapy_issuer_config(genesis_url, test_wallet_name, admin_api_key):
    return {
        "image": ACAPY_IMAGE,
        "wallet_name": test_wallet_name,
        "wallet_key": "test-wallet-key-32-chars-long!!",
        "genesis_url": genesis_url,
        "admin_port": ADMIN_PORT,
        "http_port": HTTP_PORT,
        "admin_api_key": admin_api_key,
    }


@pytest.fixture(scope="session")
def acapy_holder_config(genesis_url, admin_api_key):
    return {
        "image": ACAPY_IMAGE,
        "wallet_name": "test-holder",
        "wallet_key": "test-wallet-key-32-chars-long!!",
        "genesis_url": genesis_url,
        "admin_port": ADMIN_PORT + 100,
        "http_port": HTTP_PORT + 100,
        "admin_api_key": admin_api_key,
    }


@pytest.fixture(scope="session")
def mock_ledger_config():
    return LedgerConfig(
        issuer_did="did:indy:testnet:123456789abcdef",
        verkey="VerkeyDaJSD1RG5RGHCL3NKDNRE2HS4GRV5GG42U3XYZ",
        schema_id="did:indy:testnet:123456789abcdef:2:TestSchema:1.0",
        cred_def_id="did:indy:testnet:123456789abcdef:3:CL:1234:default",
    )


class MockAcapyIssuer:
    def __init__(
        self,
        agent_url: str = "http://localhost:8150",
        headers: dict = None,
        schema_id: str = "did:indy:testnet:123:2:schema:1.0",
        cred_def_id: str = "did:indy:testnet:123:3:CL:123:default",
        cred_attributes: list = None,
    ):
        self.agent_url = agent_url
        self.headers = headers or {}
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.cred_attributes = cred_attributes or []

    def get_invite(self):
        return {
            "invitation_url": f"{self.agent_url}/invitation",
            "connection_id": "mock-connection-id",
        }

    def is_up(self):
        return True

    def issue_credential(self, connection_id):
        return {
            "connection_id": connection_id,
            "cred_ex_id": "mock-cred-ex-id",
        }

    def revoke_credential(self, connection_id, credential_exchange_id):
        pass


@pytest.fixture
def mock_issuer():
    return MockAcapyIssuer()


@pytest.fixture
def mock_settings(monkeypatch):
    import os
    import sys

    test_settings = {
        "ISSUER_URL": "http://localhost:8150",
        "ISSUER_HEADERS": {"X-API-Key": "test-api-key"},
        "SCHEMA_ID": "did:indy:testnet:123:2:TestSchema:1.0",
        "CRED_DEF_ID": "did:indy:testnet:123:3:CL:123:default",
        "CRED_ATTR": [{"name": "attr1", "value": "test"}],
        "IS_ANONCREDS": False,
        "ISSUER_TYPE": "acapy",
    }

    for key, value in test_settings.items():
        monkeypatch.setenv(
            key,
            str(value)
            if not isinstance(value, (list, dict))
            else (json.dumps(value) if isinstance(value, list) else value),
        )

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
