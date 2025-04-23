import React from 'react';
import styled from 'styled-components';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../chat'; // Updated path (one level up)
// Remove direct theme import - we'll use ThemeProvider

// --- Styled Components (Copied from ChatPage.tsx for now) ---
// TODO: Consider moving these to a shared styles file if used elsewhere

interface MessageStyleProps {
  role: 'user' | 'assistant' | 'system';
}

const MessageContainer = styled.div<MessageStyleProps>`
  display: flex; justify-content: ${props => props.role === 'user' ? 'flex-end' : 'flex-start'};
  margin: ${props => props.theme.spacing.sm} 0; padding: 0 ${props => props.theme.spacing.sm}; animation: fadeIn 0.3s ease-in-out;
  @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
`;

// SystemMessageContainer moved to SystemMessageComponent.tsx

const MessageBubble = styled.div<MessageStyleProps>`
  max-width: 85%; min-width: 60px; padding: ${props => props.theme.spacing.md};
  border-radius: ${props => props.role === 'user' ? '22px 22px 4px 22px' : props.role === 'assistant' ? '22px 4px 22px 22px' : props.theme.borderRadius.md};
  background-color: ${props => props.role === 'user' ? 'rgba(59, 130, 246, 0.2)' : props.role === 'assistant' ? 'rgba(55, 55, 55, 0.4)' : 'transparent'};
  color: ${props => props.theme.colors.text}; font-size: ${props => props.theme.typography.fontSize.md}; line-height: ${props => props.theme.typography.lineHeight.normal};
  word-wrap: break-word; overflow-wrap: break-word;
  white-space: normal; /* Prevent text from being truncated */
  overflow: visible; /* Make sure content isn't cut off */
  display: block; /* Ensure proper rendering of the full content */
  width: auto; /* Let the content dictate width within max-width constraints */

  p { margin-bottom: ${props => props.theme.spacing.md}; &:last-child { margin-bottom: 0; } }
  ul, ol { margin-top: ${props => props.theme.spacing.sm}; margin-bottom: ${props => props.theme.spacing.md}; padding-left: ${props => props.theme.spacing.lg}; &:last-child { margin-bottom: 0; } }
  li { margin-bottom: ${props => props.theme.spacing.xs}; }
  strong { font-weight: ${props => props.theme.typography.fontWeight.bold}; }
  code { background-color: rgba(255, 255, 255, 0.1); padding: 0.1em 0.3em; border-radius: ${props => props.theme.borderRadius.sm}; font-size: 0.9em; }
`;

// SystemMessage moved to SystemMessageComponent.tsx


// --- Chat Message Component ---
interface ChatMessageComponentProps {
  message: Message | undefined; // Allow undefined for safety
}

const ChatMessageComponent: React.FC<ChatMessageComponentProps> = ({ message }) => {
  if (!message) return null; // Safety check

  // System message rendering moved to SystemMessageComponent.tsx

  if (message.isLoading) {
     return (
        <MessageContainer role="assistant">
            <MessageBubble role="assistant" style={{ opacity: 0.7 }}>{message.content}</MessageBubble>
        </MessageContainer>
     );
  }

  return (
    <MessageContainer role={message.role}>
      <MessageBubble role={message.role}>
        {/* Ensure full content is displayed without truncation */}
        <ReactMarkdown 
          components={{
            // Override default paragraph to prevent any text truncation
            p: ({node, ...props}) => <p style={{whiteSpace: 'normal', overflow: 'visible'}} {...props} />,
            // Make links open in new tab
            a: ({node, ...props}) => <a target="_blank" rel="noopener noreferrer" {...props} />
          }}
        >
          {message.content}
        </ReactMarkdown>
      </MessageBubble>
    </MessageContainer>
  );
};

export default ChatMessageComponent;