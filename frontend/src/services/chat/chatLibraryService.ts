/**
 * Chat Library Service
 * Handles operations related to the chat library component
 * This service separates business logic from UI components.
 */

import { RefObject } from 'react';

// Types
export interface ChatLibraryRefMethods {
  addPlaceholder: (tempId: string, initialTitle: string) => void;
  confirmPlaceholder: (tempId: string, realSessionData: { id: string; title: string }) => void;
  removePlaceholder: (tempId: string) => void;
  fetchSessions: () => void;
}

/**
 * Chat Library Service class to handle all chat library operations
 */
class ChatLibraryService {
  /**
   * Add a placeholder chat to the library
   * @param chatLibraryRef Reference to the chat library component
   * @param tempId Temporary ID for the placeholder
   * @param initialTitle Initial title for the placeholder
   */
  addPlaceholder(
    chatLibraryRef: RefObject<ChatLibraryRefMethods | null>,
    tempId: string,
    initialTitle: string
  ): void {
    if (chatLibraryRef.current) {
      chatLibraryRef.current.addPlaceholder(tempId, initialTitle);
    }
  }

  /**
   * Confirm a placeholder chat in the library
   * @param chatLibraryRef Reference to the chat library component
   * @param tempId Temporary ID of the placeholder
   * @param realSessionData Real session data to replace the placeholder
   */
  confirmPlaceholder(
    chatLibraryRef: RefObject<ChatLibraryRefMethods | null>,
    tempId: string,
    realSessionData: { id: string; title: string }
  ): void {
    if (chatLibraryRef.current) {
      chatLibraryRef.current.confirmPlaceholder(tempId, realSessionData);
    }
  }

  /**
   * Remove a placeholder chat from the library
   * @param chatLibraryRef Reference to the chat library component
   * @param tempId Temporary ID of the placeholder to remove
   */
  removePlaceholder(
    chatLibraryRef: RefObject<ChatLibraryRefMethods | null>,
    tempId: string
  ): void {
    if (chatLibraryRef.current) {
      chatLibraryRef.current.removePlaceholder(tempId);
    }
  }

  /**
   * Refresh the sessions in the chat library
   * @param chatLibraryRef Reference to the chat library component
   */
  refreshSessions(chatLibraryRef: RefObject<ChatLibraryRefMethods | null>): void {
    if (chatLibraryRef.current) {
      chatLibraryRef.current.fetchSessions();
    }
  }
}

// Export singleton instance
const chatLibraryService = new ChatLibraryService();
export default chatLibraryService;
