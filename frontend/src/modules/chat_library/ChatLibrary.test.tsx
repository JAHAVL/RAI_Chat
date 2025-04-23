import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatLibrary from './ChatLibrary';
import { useAuth } from '../../contexts/AuthContext'; // Adjust path if needed
import raiAPIClient from '../../api/rai_api'; // Adjust path if needed
import { Session } from '../../api/rai_api'; // Changed from 'import type'

// --- Mocks ---

// Mock the useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

// Mock the raiAPIClient
jest.mock('../../api/rai_api', () => ({
  deleteChatSession: jest.fn(),
}));

// Removed mock for window.api as it's no longer used in web version


// Helper to provide mock context values
const mockUseAuth = useAuth as jest.Mock;
const mockDeleteChatSession = raiAPIClient.deleteChatSession as jest.Mock;
const mockFetchUserSessions = jest.fn(); // Mock function provided by context

const mockSessions: Session[] = [
  { id: 'session-1', title: 'Test Chat 1', timestamp: new Date().toISOString(), last_modified: new Date().toISOString() },
  { id: 'session-2', title: 'Another Chat', timestamp: new Date().toISOString(), last_modified: new Date().toISOString() },
];

// Default props for ChatLibrary
const defaultProps = {
  isOpen: true,
  onSelectChat: jest.fn(),
  currentSessionId: 'some-other-id',
  onNewChat: jest.fn(),
  onChatDeleted: jest.fn(),
};

// --- Tests ---

describe('ChatLibrary Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    // Default mock implementation for useAuth
    mockUseAuth.mockReturnValue({
      sessions: null,
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
  });

  test('renders loading state', () => {
    mockUseAuth.mockReturnValue({
      sessions: null,
      isFetchingSessions: true, // Simulate loading
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    expect(screen.getByText('Loading chats...')).toBeInTheDocument();
  });

  test('renders error state', () => {
    const errorMessage = 'Failed to load';
    mockUseAuth.mockReturnValue({
      sessions: null,
      isFetchingSessions: false,
      error: errorMessage, // Simulate error
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toHaveStyle('color: red');
  });

  test('renders empty state', () => {
    mockUseAuth.mockReturnValue({
      sessions: [], // Simulate empty array
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    expect(screen.getByText('No chats yet.')).toBeInTheDocument();
  });

  test('renders list of sessions', () => {
    mockUseAuth.mockReturnValue({
      sessions: mockSessions, // Simulate successful fetch
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    expect(screen.getByText('Test Chat 1')).toBeInTheDocument();
    expect(screen.getByText('Another Chat')).toBeInTheDocument();
    expect(screen.queryByText('Loading chats...')).not.toBeInTheDocument();
    expect(screen.queryByText('No chats yet.')).not.toBeInTheDocument();
  });

  test('calls onSelectChat when a chat item is clicked', () => {
    mockUseAuth.mockReturnValue({
      sessions: mockSessions,
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    fireEvent.click(screen.getByText('Test Chat 1'));
    expect(defaultProps.onSelectChat).toHaveBeenCalledWith('session-1');
  });

  test('calls onNewChat when the new chat button is clicked', () => {
    mockUseAuth.mockReturnValue({
      sessions: mockSessions,
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions,
    });
    render(<ChatLibrary {...defaultProps} />);
    fireEvent.click(screen.getByTitle('Start New Chat'));
    expect(defaultProps.onNewChat).toHaveBeenCalled();
  });

  test('calls deleteChatSession and fetchUserSessions when delete button is clicked', async () => {
    // No need to mock window.confirm as it's been bypassed
    mockDeleteChatSession.mockResolvedValue({ status: 'success' }); // Mock successful API delete

    mockUseAuth.mockReturnValue({
      sessions: mockSessions,
      isFetchingSessions: false,
      error: null,
      fetchUserSessions: mockFetchUserSessions, // Provide the mock fetch function
    });

    render(<ChatLibrary {...defaultProps} />);

    // Find the delete button associated with the first chat
    const chatItem = screen.getByText('Test Chat 1').closest('li');
    expect(chatItem).toBeInTheDocument();
    const deleteButton = chatItem?.querySelector('button[title*="Delete chat"]');
    expect(deleteButton).toBeInTheDocument();

    // Click the delete button
    fireEvent.click(deleteButton!);

    // Check if API client delete method was called
    await waitFor(() => {
        expect(mockDeleteChatSession).toHaveBeenCalledWith('session-1');
    });

    // Check if fetchUserSessions from context was called after successful delete
    expect(mockFetchUserSessions).toHaveBeenCalled();

    // Check if parent callback was called
    expect(defaultProps.onChatDeleted).toHaveBeenCalledWith('session-1');
  });

  // Test for delete cancellation removed since confirmation dialog has been bypassed

});