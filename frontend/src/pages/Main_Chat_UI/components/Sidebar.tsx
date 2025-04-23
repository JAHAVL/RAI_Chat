import React from 'react';
import styled from 'styled-components';
import ModuleButton from './ModuleButton';

interface SidebarProps {
  activeModule: string | null;
  onModuleChange: (module: string) => void;
  moduleButtons: Array<{
    id: string;
    icon: React.ReactNode;
    title?: string;
  }>;
}

const SidebarContainer = styled.div`
  width: 50px;
  min-width: 50px;
  position: relative;
  background-color: rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: ${props => props.theme.spacing.md} 0;
  padding-top: calc(46px + ${props => props.theme.spacing.md});
  padding-bottom: ${props => props.theme.spacing.lg};
  z-index: 100;
  backdrop-filter: blur(15px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
  
  &::-webkit-scrollbar {
    display: none;
    width: 0;
  }
`;

const Sidebar: React.FC<SidebarProps> = ({ activeModule, onModuleChange, moduleButtons }) => {
  return (
    <SidebarContainer>
      {moduleButtons.map(button => (
        <ModuleButton
          key={button.id}
          $active={activeModule === button.id ? true : false}
          onClick={() => onModuleChange(button.id)}
          title={button.title}
        >
          {button.icon}
        </ModuleButton>
      ))}
    </SidebarContainer>
  );
};

export default Sidebar;