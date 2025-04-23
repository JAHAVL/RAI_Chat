import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext'; // Remove extension
import styled from 'styled-components'; // Import styled

// --- Styled Components for Auth Forms ---
// (These could be moved to a shared file later)

const FormWrapper = styled.div`
  /* No specific styles needed here if AuthPage's FormContainer handles it */
`;

const Title = styled.h2`
  color: ${props => props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.lg}; // Use theme font size
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  margin-bottom: ${props => props.theme.spacing.lg};
  text-align: center;
`;

const StyledForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${props => props.theme.spacing.md}; // Spacing between form elements
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${props => props.theme.spacing.xs};
`;

const Label = styled.label`
  font-size: ${props => props.theme.typography.fontSize.sm};
  color: ${props => props.theme.colors.text}CC; // Slightly transparent text
  font-weight: ${props => props.theme.typography.fontWeight.medium};
`;

const Input = styled.input`
  padding: ${props => props.theme.spacing.sm} ${props => props.theme.spacing.md};
  background-color: rgba(255, 255, 255, 0.05); // Match app input style
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.sm};
  color: ${props => props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.md};
  font-family: inherit;
  transition: border-color ${props => props.theme.transitions.fast}, background-color ${props => props.theme.transitions.fast};

  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.accent};
    background-color: rgba(255, 255, 255, 0.08);
  }

  &::placeholder {
    color: ${props => props.theme.colors.placeholder};
  }

  &:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    cursor: not-allowed;
    opacity: 0.6;
  }
`;

const Button = styled.button`
  padding: ${props => props.theme.spacing.sm} ${props => props.theme.spacing.md};
  background-color: ${props => props.theme.colors.accent};
  color: ${props => props.theme.colors.text};
  border: none;
  border-radius: ${props => props.theme.borderRadius.sm};
  font-size: ${props => props.theme.typography.fontSize.md};
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  cursor: pointer;
  transition: background-color ${props => props.theme.transitions.fast};
  margin-top: ${props => props.theme.spacing.sm}; // Add some space above button

  &:hover {
    background-color: ${props => props.theme.colors.accent}E6; // Slightly darken on hover
  }

  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px ${props => props.theme.colors.accent}80;
  }

  &:disabled {
    background-color: ${props => props.theme.colors.accent}80; // Dimmed accent color
    cursor: not-allowed;
    opacity: 0.7;
  }
`;

const ErrorMessage = styled.p`
  color: #f87171; // A slightly softer red for errors
  font-size: ${props => props.theme.typography.fontSize.sm};
  text-align: center;
  margin-top: ${props => props.theme.spacing.sm};
  min-height: calc(${props => props.theme.typography.fontSize.sm} * ${props => props.theme.typography.lineHeight?.normal || 1.5}); // Reserve space
`;

// --- Login Component ---

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error: authError } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(username, password);
      console.log('Login attempt submitted...');
    } catch (err: any) {
      console.error('Login component caught error:', err.message);
    }
  };

  return (
    <FormWrapper>
      <Title>Login</Title>
      <StyledForm onSubmit={handleLogin}>
        <FormGroup>
          <Label htmlFor="login-username">Username</Label>
          <Input
            type="text"
            id="login-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Enter your username"
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="login-password">Password</Label>
          <Input
            type="password"
            id="login-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Enter your password"
          />
        </FormGroup>
        {/* Display error from AuthContext */}
        <ErrorMessage>{authError ? authError : '\u00A0'}</ErrorMessage> {/* Use non-breaking space to reserve height */}
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Logging in...' : 'Login'}
        </Button>
      </StyledForm>
    </FormWrapper>
  );
};

export default Login;