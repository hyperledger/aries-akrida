#!/bin/bash
set -e

echo "=== Running Unit Tests ==="
pdm run pytest tests/unit -v

echo ""
echo "=== Running Locust Tests ==="
pdm run pytest locust-files/test -v

echo ""
echo "=== Unit tests completed ==="