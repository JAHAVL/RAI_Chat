import React from 'react';
import styled from 'styled-components';

// Type for styled-component props
interface ModuleButtonProps {
  $active?: boolean; // Transient prop
  onClick: () => void;
  title?: string;
  children: React.ReactNode;
}

// Styled component for the module button
const StyledModuleButton = styled.button<{ $active?: boolean }>`
  width: 40px;
  height: 40px;
  min-width: 40px;
  min-height: 40px;
  flex-shrink: 0;
  border-radius: 50%;
  margin-bottom: 16px;
  background-color: ${props => props.$active ? 'rgba(59, 130, 246, 0.2)' : 'transparent'};
  border: none;
  color: ${props => props.$active ? props.theme.colors.accent : props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.lg};
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all ${props => props.theme.transitions.fast};
  
  &:hover {
    background-color: ${props => props.$active ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255, 255, 255, 0.1)'};
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px ${props => props.theme.colors.accent}80;
  }
`;

const ModuleButton: React.FC<ModuleButtonProps> = ({ $active, onClick, title, children }) => {
  return (
    <StyledModuleButton $active={$active} onClick={onClick} title={title}>
      {children}
    </StyledModuleButton>
  );
};

export default ModuleButton;