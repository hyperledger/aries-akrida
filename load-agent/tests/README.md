# ACA-Py Issuer Functional Tests

This directory contains functional tests for the ACA-Py issuer implementations (`acapy.py` and `acapy_v2.py`).

## Test Structure

```
tests/
├── conftest.py                    # Main pytest fixtures
├── unit/
│   ├── test_acapy_issuer.py      # Unit tests for v1 issuer
│   └── test_acapy_v2_issuer.py   # Unit tests for v2 issuer
├── integration/
│   ├── conftest.py               # Integration test fixtures
│   └── test_issuer_flows.py     # Integration tests with real agents
└── fixtures/
    └── docker-compose.test.yml   # Docker compose for tests
```

## Running Tests

### Unit Tests

```bash
# From load-agent directory
pdm run pytest tests/unit -v

# Or use the helper script
./tests/run_unit_tests.sh
```

### Integration Tests (requires Docker + Indicio TestNet)

```bash
# Make sure Docker is running
docker --version

# Log in to GitHub Container Registry (required for ghcr.io images)
docker login ghcr.io

# Run with real ACA-Py agents on Indicio TestNet
pdm run pytest tests/integration -v --use-docker --use-real-ledger -m integration
```

> **Troubleshooting**: If `ghcr.io` images fail to pull, try the Docker Hub alternative:
> ```bash
> docker pull bcgovimages/aries-cloudagent:latest
> ```
> Then update `ACAPY_IMAGE` in conftest.py to use the Docker Hub image.

### Integration Test Notes

**Status**: Under development

Integration tests require proper ACA-Py container startup which varies by version:
- Current image (`aries-cloudagent-run:latest`) uses Poetry entrypoint
- Requires specific flags for inbound-transport, genesis-url, etc.

For now, integration tests require manual container setup OR skip:
```bash
pdm run pytest tests/unit locust-files/test -v
```

### Locust Tests

```bash
pdm run pytest locust-files/test -v
```

### All Tests

```bash
pdm run pytest tests/unit locust-files/test -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_ACAPY_ADMIN_API_KEY` | API key for ACA-Py admin interface | (empty) |

## Ledger Configuration

The tests use the **Indicio TestNet** by default:
- Genesis URL: `https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/genesis_files/pool_transactions_testnet_genesis`
- DID Registration: Automated via SelfServe API

## Test Categories

### Unit Tests
- Mocked HTTP calls to ACA-Py endpoints
- Fast execution, no external dependencies
- Tests return values, error handling, and method calls

### Integration Tests (`@pytest.mark.integration`)
- Real Docker containers running ACA-Py agents
- Real Indicio TestNet ledger
- Tests full credential issuance and revocation flows

## Manual Ledger Setup (if not using automated)

If you need to set up the ledger manually:

1. Register DID at https://selfserve.indiciotech.io/
2. Create schema and credential definition via ACA-Py admin API
3. Set environment variables for tests

## Dependencies

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-mock>=3.12.0", "pytest-asyncio>=0.23.0"]
integration = ["aiohttp>=3.9.0"]
```
