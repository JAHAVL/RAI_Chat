#!/bin/bash

# End-to-End Memory Coherence Test Runner
# This script runs a comprehensive 50-turn conversation test against the running RAI Chat system
# to validate tiered memory coherence, pruning, and recall capabilities

echo "===== RAI Chat Tiered Memory Coherence Test ====="

# Check if Docker containers are running
if ! docker ps | grep -q "rai-backend"; then
  echo "Error: rai-backend container not running. Please start the Docker services first."
  echo "Run: docker-compose up -d"
  exit 1
fi

if ! docker ps | grep -q "rai-llm-engine"; then
  echo "Warning: rai-llm-engine container not detected. LLM responses may be affected."
  sleep 2
fi

# Check if backend API is accessible
echo "Checking backend API availability..."
if ! curl -s http://localhost:6102/api/health > /dev/null; then
  echo "Error: Backend API not accessible at http://localhost:6102"
  echo "Check Docker port mappings and service health."
  exit 1
fi

echo "Backend API available. Starting memory coherence test..."

# Run the test
python3 ./tests/test_e2e_memory_quiz.py

TEST_EXIT=$?

# Report results
if [ $TEST_EXIT -eq 0 ]; then
  echo "\n✅ Memory coherence test PASSED!"
  echo "Detailed results available in memory_test_results.log"
else
  echo "\n❌ Memory coherence test FAILED!"
  echo "Review memory_test_results.log for detailed error information."
fi

# Show test summary
echo "\n===== Test Summary ====="
tail -n 20 memory_test_results.log

exit $TEST_EXIT
