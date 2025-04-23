// RAI_Chat/frontend/src/types/chat.d.ts

// Define the Message interface
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date; // Use Date consistently in the app state
  isLoading?: boolean;
  messageType?: string;
  isSearchMessage?: boolean; // Added for search-related system messages
  // Add other potential message properties if needed
}

// Export other shared chat types here if necessary