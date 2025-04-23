import React from 'react';
import styled, { css } from 'styled-components';
import { Message } from '../chat.d';

// --- Styled Components ---

const SystemMessageContainer = styled.div`
  display: flex; 
  justify-content: center; 
  margin: ${props => props.theme.spacing.md} 0; 
  padding: 0 ${props => props.theme.spacing.md};
`;

// This interface is no longer needed as we're using SystemMessageStyledProps

// Use a different name to avoid name conflicts with the DOM attributes
interface SystemMessageStyledProps {
  $messageType?: string; // Using $ prefix to indicate it's a styled-component prop
}

const SystemMessage = styled.div<SystemMessageStyledProps>`
  max-width: 90%; 
  padding: ${props => props.theme.spacing.sm} ${props => props.theme.spacing.md}; 
  border-radius: 16px;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
  color: ${props => props.theme.colors.text}; 
  font-size: ${props => props.theme.typography.fontSize.md}; 
  text-align: center;
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  animation: fadeIn 0.3s ease-in-out;
  box-shadow: inset 3px 0 0 ${props => props.theme.colors.accent};
  
  ${props => props.$messageType === 'error' && css`
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 #ef4444;
  `}
  
  ${props => props.$messageType === 'warning' && css`
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 #f59e0b;
  `}
  
  ${props => props.$messageType === 'success' && css`
    background: linear-gradient(90deg, rgba(34, 197, 94, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 #22c55e;
  `}
  
  ${props => props.$messageType === 'info' && css`
    background: linear-gradient(90deg, rgba(59, 130, 246, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 ${props => props.theme.colors.accent};
  `}
  
  ${props => props.$messageType === 'welcome' && css`
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 #10b981;
    font-size: ${props => props.theme.typography.fontSize.lg};
  `}
  
  ${props => props.$messageType === 'search' && css`
    background: linear-gradient(90deg, rgba(124, 58, 237, 0.3) 0%, rgba(30, 30, 30, 0.5) 100%);
    box-shadow: inset 3px 0 0 #7c3aed;
  `}
`;

interface SystemMessageComponentProps {
  message: Message;
}

const SystemMessageComponent: React.FC<SystemMessageComponentProps> = ({ message }) => {
  // Use messageType if available, or default to 'default'
  const typeToUse = message.messageType || 'default';
  
  return (
    <SystemMessageContainer>
      <SystemMessage $messageType={typeToUse}>
        {message.content}
      </SystemMessage>
    </SystemMessageContainer>
  );
};

export default SystemMessageComponent;