#!/bin/bash
# Run tests with coverage reporting (single-run)

set -euo pipefail

echo "=== HA Event Processor - Test Suite ==="
echo ""

# Optional: install test dependencies if the environment requires it
if [ "$1" != "--no-install" ]; then
  echo "Installing test dependencies..."
  pip install -q -r requirements-test.txt
  echo ""
fi

PYTEST_CMD=(pytest tests/ -v --cov=src/ha_event_processor --cov-report=term-missing --cov-report=html --cov-report=xml --junit-xml=test-results.xml)

echo "Running tests: ${PYTEST_CMD[*]}"

"${PYTEST_CMD[@]}"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo ""
  echo "=== Tests failed with exit code $EXIT_CODE ==="
  exit $EXIT_CODE
fi

echo ""
echo "=== Test run successful ==="

echo "Coverage HTML: htmlcov/index.html"
echo "Coverage XML: coverage.xml"
echo "JUnit XML: test-results.xml"

exit 0
