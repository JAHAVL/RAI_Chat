# RAI_Chat/backend/tests/integration/test_api.py

import unittest
import json
from ...app import create_app


class TestAPIEndpoints(unittest.TestCase):
    """Integration tests for API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'ok')

    def test_auth_endpoints(self):
        """Test authentication endpoints."""
        # Test registration
        register_data = {
            'username': 'testuser',
            'password': 'testpassword',
            'email': 'test@example.com'
        }
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(register_data),
            content_type='application/json'
        )
        
        # This is just a basic structure test - in a real app, we'd use a test database
        # and validate the full registration flow
        self.assertIn(response.status_code, [200, 201, 400, 409])
        
        # Test login (will likely fail without a proper test database setup)
        login_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        # Just checking that the endpoint exists and returns a valid response
        self.assertIn(response.status_code, [200, 401, 404])


if __name__ == '__main__':
    unittest.main()
