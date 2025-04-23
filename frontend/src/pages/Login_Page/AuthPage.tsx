import React, { useState } from 'react';
import Login from './Login';
import Register from './Register';
import styled from 'styled-components';
import { theme } from '../../../shared/theme'; // Corrected theme import path again

// Styled container for the entire auth page
const AuthPageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: ${props => props.theme.colors.background};
  color: ${props => props.theme.colors.text};
  font-family: ${props => props.theme.typography.fontFamily};
  padding: ${props => props.theme.spacing.lg};
`;

// Styled container for the form itself (Login or Register)
const FormContainer = styled.div`
  width: 100%;
  max-width: 400px; // Limit form width
  background-color: ${props => props.theme.colors.inputBackground}; // Slightly different background
  padding: ${props => props.theme.spacing.lg};
  border-radius: ${props => props.theme.borderRadius.md};
  border: 1px solid ${props => props.theme.colors.border};
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
`;

// Styled button for toggling between Login and Register views
const ToggleViewButton = styled.button`
  margin-top: ${props => props.theme.spacing.lg};
  padding: ${props => props.theme.spacing.sm} ${props => props.theme.spacing.md};
  background-color: transparent;
  color: ${props => props.theme.colors.accent};
  border: none; // Make it look like a link
  border-radius: ${props => props.theme.borderRadius.sm};
  cursor: pointer;
  font-size: ${props => props.theme.typography.fontSize.sm};
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  text-align: center;
  transition: color ${props => props.theme.transitions.fast};

  &:hover {
    color: ${props => props.theme.colors.text}; // Change color on hover
    text-decoration: underline;
  }

  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px ${props => props.theme.colors.accent}80; // Focus ring like other buttons
  }
`;

const AuthPage: React.FC = () => {
  const [isLoginView, setIsLoginView] = useState(true); // State to toggle between Login and Register

  const toggleView = () => {
    setIsLoginView(!isLoginView);
  };

  return (
    <AuthPageContainer>
      <FormContainer>
        {isLoginView ? <Login /> : <Register />}
        <ToggleViewButton onClick={toggleView}>
          {isLoginView ? "Don't have an account? Register" : "Already have an account? Login"}
        </ToggleViewButton>
      </FormContainer>
    </AuthPageContainer>
  );
};

export default AuthPage;