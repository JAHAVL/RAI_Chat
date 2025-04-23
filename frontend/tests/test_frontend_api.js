/**
 * Test script for the Frontend API Client
 * This script tests the frontend's ability to communicate with the backend API.
 */

// Mock fetch for testing
const originalFetch = global.fetch;
let mockFetchImplementation = null;

// Mock implementation
const mockFetch = (...args) => {
  if (mockFetchImplementation) {
    return mockFetchImplementation(...args);
  }
  return originalFetch(...args);
};

// Setup mock
global.fetch = mockFetch;

// Import the RAI API client
const { RAIAPIClient } = require('../src/api/rai_api');

console.log("Testing Frontend API Client...");

// Test configuration
const TEST_CONFIG = {
  baseUrl: 'http://localhost:5001',
  sessionId: 'test-session-' + Date.now(),
  message: 'Hello, can you tell me about the RAI Chat application?'
};

// Test functions
async function testCreateSession() {
  console.log("Testing create session...");
  
  try {
    // Setup mock response
    mockFetchImplementation = () => Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ 
        session_id: TEST_CONFIG.sessionId,
        status: 'success'
      })
    });
    
    const client = new RAIAPIClient(TEST_CONFIG.baseUrl);
    const result = await client.createSession(TEST_CONFIG.sessionId);
    
    if (result && result.session_id === TEST_CONFIG.sessionId) {
      console.log("✅ Create session test passed");
      return true;
    } else {
      console.log("❌ Create session test failed: Unexpected response");
      console.log("Response:", result);
      return false;
    }
  } catch (error) {
    console.log("❌ Create session test failed with exception:", error.message);
    return false;
  }
}

async function testSendMessage() {
  console.log("Testing send message...");
  
  try {
    // Setup mock response
    mockFetchImplementation = () => Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ 
        session_id: TEST_CONFIG.sessionId,
        response: "I'm the RAI Chat application, a conversational AI system.",
        status: 'success'
      })
    });
    
    const client = new RAIAPIClient(TEST_CONFIG.baseUrl);
    const result = await client.sendMessage({
      message: TEST_CONFIG.message,
      sessionId: TEST_CONFIG.sessionId
    });
    
    if (result && result.response && result.session_id === TEST_CONFIG.sessionId) {
      console.log("✅ Send message test passed");
      console.log("Response:", result.response.substring(0, 100) + "...");
      return true;
    } else {
      console.log("❌ Send message test failed: Unexpected response");
      console.log("Response:", result);
      return false;
    }
  } catch (error) {
    console.log("❌ Send message test failed with exception:", error.message);
    return false;
  }
}

async function testStreamMessage() {
  console.log("Testing stream message...");
  
  try {
    // Setup mock response
    mockFetchImplementation = () => Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ 
        session_id: TEST_CONFIG.sessionId,
        response: "I'm the RAI Chat application, a conversational AI system.",
        status: 'success',
        type: 'final'
      })
    });
    
    let updateReceived = false;
    
    const client = new RAIAPIClient(TEST_CONFIG.baseUrl);
    const result = await client.streamMessage({
      message: TEST_CONFIG.message,
      sessionId: TEST_CONFIG.sessionId,
      onUpdate: (chunk) => {
        console.log("Received update chunk:", chunk.type);
        updateReceived = true;
      }
    });
    
    if (result && result.response && updateReceived) {
      console.log("✅ Stream message test passed");
      console.log("Response:", result.response.substring(0, 100) + "...");
      return true;
    } else {
      console.log("❌ Stream message test failed: Unexpected response");
      console.log("Response:", result);
      return false;
    }
  } catch (error) {
    console.log("❌ Stream message test failed with exception:", error.message);
    return false;
  }
}

async function testErrorHandling() {
  console.log("Testing error handling...");
  
  try {
    // Setup mock response for network error
    mockFetchImplementation = () => Promise.reject(new TypeError('Failed to fetch'));
    
    const client = new RAIAPIClient(TEST_CONFIG.baseUrl);
    
    try {
      await client.sendMessage({
        message: TEST_CONFIG.message,
        sessionId: TEST_CONFIG.sessionId
      });
      console.log("❌ Error handling test failed: Expected an error but none was thrown");
      return false;
    } catch (error) {
      if (error.message.includes('Network connection error')) {
        console.log("✅ Error handling test passed");
        return true;
      } else {
        console.log("❌ Error handling test failed: Unexpected error message");
        console.log("Error:", error.message);
        return false;
      }
    }
  } catch (error) {
    console.log("❌ Error handling test failed with exception:", error.message);
    return false;
  }
}

// Run all tests
async function runTests() {
  const createSessionResult = await testCreateSession();
  const sendMessageResult = await testSendMessage();
  const streamMessageResult = await testStreamMessage();
  const errorHandlingResult = await testErrorHandling();
  
  // Restore original fetch
  global.fetch = originalFetch;
  
  // Print summary
  console.log("\n=== Frontend API Client Test Summary ===");
  console.log(`Create Session: ${createSessionResult ? '✅ Passed' : '❌ Failed'}`);
  console.log(`Send Message: ${sendMessageResult ? '✅ Passed' : '❌ Failed'}`);
  console.log(`Stream Message: ${streamMessageResult ? '✅ Passed' : '❌ Failed'}`);
  console.log(`Error Handling: ${errorHandlingResult ? '✅ Passed' : '❌ Failed'}`);
  
  // Overall result
  if (createSessionResult && sendMessageResult && streamMessageResult && errorHandlingResult) {
    console.log("\n✅ All Frontend API Client tests passed!");
    process.exit(0);
  } else {
    console.log("\n❌ Some Frontend API Client tests failed!");
    process.exit(1);
  }
}

// Run the tests
runTests().catch(error => {
  console.error("Test runner error:", error);
  process.exit(1);
});
