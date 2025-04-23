#!/bin/bash
# Master test script to run all component tests in sequence

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== RAI Chat Application Test Suite =====${NC}"
echo "Starting tests at $(date)"
echo

# Store the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Function to run a test and report results
run_test() {
  local test_name="$1"
  local test_command="$2"
  local test_dir="$3"
  
  echo -e "${YELLOW}Running $test_name tests...${NC}"
  
  # Change to the test directory if specified
  if [ -n "$test_dir" ]; then
    cd "$test_dir" || { echo -e "${RED}Failed to change to directory: $test_dir${NC}"; return 1; }
  fi
  
  # Run the test command
  eval "$test_command"
  local result=$?
  
  # Return to the project root
  cd "$PROJECT_ROOT"
  
  # Report the result
  if [ $result -eq 0 ]; then
    echo -e "${GREEN}✅ $test_name tests PASSED${NC}"
  else
    echo -e "${RED}❌ $test_name tests FAILED${NC}"
  fi
  
  echo
  return $result
}

# Initialize test results
llm_engine_result=0
backend_result=0
frontend_result=0

# Test 1: LLM Engine
run_test "LLM Engine" "python3 tests/test_llm_engine.py"
llm_engine_result=$?

# Test 2: Backend Conversation Manager
run_test "Backend Conversation Manager" "python3 backend/tests/test_conversation_manager.py"
backend_result=$?

# Test 3: Frontend API Client
# For frontend tests, we need Node.js
if command -v node &> /dev/null; then
  run_test "Frontend API Client" "node frontend/tests/test_frontend_api.js"
  frontend_result=$?
else
  echo -e "${RED}❌ Node.js not found. Skipping Frontend API Client tests.${NC}"
  frontend_result=1
fi

# Print summary
echo -e "${YELLOW}===== Test Summary =====${NC}"
echo -e "LLM Engine: $([ $llm_engine_result -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
echo -e "Backend Conversation Manager: $([ $backend_result -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
echo -e "Frontend API Client: $([ $frontend_result -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"

# Overall result
if [ $llm_engine_result -eq 0 ] && [ $backend_result -eq 0 ] && [ $frontend_result -eq 0 ]; then
  echo -e "\n${GREEN}✅ All tests PASSED!${NC}"
  exit 0
else
  echo -e "\n${RED}❌ Some tests FAILED!${NC}"
  exit 1
fi
