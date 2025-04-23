# RAI_Chat/backend/tests/unit/test_models.py

import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...core.database.models import Base, User, Session


class TestDatabaseModels(unittest.TestCase):
    """Test cases for SQLAlchemy database models."""

    def setUp(self):
        """Set up test database."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        """Clean up after tests."""
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_user_model(self):
        """Test User model creation and relationships."""
        # Create a test user
        user = User(
            username='testuser',
            hashed_password='hashed_password',
            email='test@example.com',
            auth_provider='local'
        )
        self.session.add(user)
        self.session.commit()

        # Retrieve the user
        retrieved_user = self.session.query(User).filter_by(username='testuser').first()
        
        # Assert user properties
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.username, 'testuser')
        self.assertEqual(retrieved_user.email, 'test@example.com')
        self.assertEqual(retrieved_user.auth_provider, 'local')
        self.assertTrue(retrieved_user.is_active)
        self.assertIsNotNone(retrieved_user.created_at)

    def test_session_model(self):
        """Test Session model creation and relationships."""
        # Create a test user
        user = User(
            username='testuser',
            hashed_password='hashed_password',
            email='test@example.com'
        )
        self.session.add(user)
        self.session.commit()

        # Create a test session for the user
        chat_session = Session(
            user_id=user.user_id,
            title='Test Session'
        )
        self.session.add(chat_session)
        self.session.commit()

        # Retrieve the session
        retrieved_session = self.session.query(Session).filter_by(title='Test Session').first()
        
        # Assert session properties
        self.assertIsNotNone(retrieved_session)
        self.assertEqual(retrieved_session.title, 'Test Session')
        self.assertEqual(retrieved_session.user_id, user.user_id)
        self.assertIsNotNone(retrieved_session.created_at)
        self.assertIsNotNone(retrieved_session.last_activity_at)

        # Test relationship
        self.assertEqual(retrieved_session.user.username, 'testuser')
        self.assertIn(retrieved_session, user.sessions)


if __name__ == '__main__':
    unittest.main()
