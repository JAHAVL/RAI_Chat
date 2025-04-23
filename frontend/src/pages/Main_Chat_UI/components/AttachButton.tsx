import React from 'react';
import styled from 'styled-components';
import { FaPaperclip } from 'react-icons/fa';

interface AttachButtonProps {
  onClick: () => void;
  title?: string;
}

// Using styles similar to IconButton in ChatPage for consistency
const StyledAttachButton = styled.button`
  width: 36px; 
  height: 36px; 
  border-radius: 50%; 
  border: 1px solid rgba(255, 255, 255, 0.2);
  background-color: transparent;
  color: ${props => props.theme.colors?.text || '#ffffff'};
  font-size: ${props => props.theme.typography?.fontSize?.md || '16px'};
  cursor: pointer;
  display: flex; 
  align-items: center; 
  justify-content: center;
  transition: all ${props => props.theme.transitions?.fast || '0.15s ease'};
  margin-left: ${props => props.theme.spacing?.sm || '8px'};
  margin-right: ${props => props.theme.spacing?.sm || '8px'};
  
  &:focus { 
    outline: none;
    border-color: ${props => props.theme.colors?.accent || '#3b82f6'};
  }
  &:hover { 
    background-color: rgba(255, 255, 255, 0.05); 
  }
`;

const AttachButton: React.FC<AttachButtonProps> = ({ onClick, title = "Attach file" }) => {
  return (
    <StyledAttachButton onClick={onClick} title={title}>
      <FaPaperclip />
    </StyledAttachButton>
  );
};

export default AttachButton;