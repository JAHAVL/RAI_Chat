import React from 'react';
import styled from 'styled-components';
import { FaBars, FaSignOutAlt } from 'react-icons/fa';
import { useAuth } from '../../../contexts/AuthContext';

interface HeaderComponentProps {
  onToggleChatLibrary: () => void;
  logout?: () => void; // Make logout optional to maintain compatibility
}

const HeaderContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 50px; /* Make space for sidebar */
  height: 45px;
  background-color: rgba(18, 18, 18, 0.98);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 ${props => props.theme.spacing.md};
  z-index: 1000; /* Increased z-index for visibility */
  -webkit-app-region: drag;
  backdrop-filter: blur(15px);
`;

const Title = styled.h1`
  font-size: ${props => props.theme.typography.fontSize.md};
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  color: ${props => props.theme.colors.text};
  margin: 0;
  flex-grow: 1;
  text-align: center;
  -webkit-app-region: no-drag;
  padding-left: 40px; /* Add padding to roughly center with button on left */
`;

const HeaderButton = styled.button`
  background-color: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: ${props => props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.md};
  cursor: pointer;
  padding: ${props => props.theme.spacing.xs};
  margin: 0 5px;
  line-height: 1;
  transition: all ${props => props.theme.transitions.fast};
  -webkit-app-region: no-drag;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  box-shadow: ${props => props.theme.shadows.sm};

  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.3);
  }
  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.accent};
  }
`;
const HeaderComponent: React.FC<HeaderComponentProps> = ({ onToggleChatLibrary, logout: logoutProp }) => {
  const { logout: authLogout } = useAuth();
  const handleLogout = logoutProp || authLogout; // Use the prop if provided, otherwise use from auth
  const log = console.log; // Use console.log for web
  
  const handleToggleClick = (e: React.MouseEvent<HTMLButtonElement>) => { // Add event type
    e.stopPropagation(); // Stop the event from bubbling up
    log("HeaderComponent: Toggle button clicked");
    onToggleChatLibrary();
  };

  return (
    <HeaderContainer>
      {/* Chat Library Toggle Button */}
      <HeaderButton
        onClick={handleToggleClick}
        style={{ marginRight: '8px' }}
      >
        <FaBars />
      </HeaderButton>
      <Title>R.ai</Title>
      {/* Logout button in the top right */}
      <HeaderButton
        onClick={handleLogout}
        title="Logout"
      >
        <FaSignOutAlt />
      </HeaderButton>
    </HeaderContainer>
  );
};

export default HeaderComponent;