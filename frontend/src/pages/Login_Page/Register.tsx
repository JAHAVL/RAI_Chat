import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext'; // Remove extension
import styled from 'styled-components'; // Import styled

// --- Styled Components for Auth Forms ---
// (Copied from Login.tsx for now - ideally move to a shared file)

const FormWrapper = styled.div`
  /* No specific styles needed here if AuthPage's FormContainer handles it */
`;

const Title = styled.h2`
  color: ${props => props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.lg};
  font-weight: ${props => props.theme.typography.fontWeight.medium};
  margin-bottom: ${props => props.theme.spacing.lg};
  text-align: center;
`;

const StyledForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${props => props.theme.spacing.md};
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${props => props.theme.spacing.xs};
`;

const Label = styled.label`
  font-size: ${props => props.theme.typography.fontSize.sm};
  color: ${props => props.theme.colors.text}CC;
  font-weight: ${props => props.theme.typography.fontWeight.medium};
`;

const Input = styled.input`
  padding: ${props => props.theme.spacing.sm} ${props => props.theme.spacing.md};
  background-color: rgba(255, 255, 255, 0.05);
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
  margin-top: ${props => props.theme.spacing.sm};

  &:hover {
    background-color: ${props => props.theme.colors.accent}E6;
  }

  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px ${props => props.theme.colors.accent}80;
  }

  &:disabled {
    background-color: ${props => props.theme.colors.accent}80;
    cursor: not-allowed;
    opacity: 0.7;
  }
`;

// Specific message styles for Register
const Message = styled.p`
  font-size: ${props => props.theme.typography.fontSize.sm};
  text-align: center;
  margin-top: ${props => props.theme.spacing.sm};
  min-height: calc(${props => props.theme.typography.fontSize.sm} * ${props => props.theme.typography.lineHeight?.normal || 1.5}); // Reserve space
`;

const ErrorMessage = styled(Message)`
  color: #f87171; // Softer red
`;

const SuccessMessage = styled(Message)`
  color: #34d399; // Green for success
`;

// --- Register Component ---

const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { register, isLoading, error: authError } = useAuth();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    setSuccess(null);

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    try {
      await register(username, email, password);
      setSuccess('Registration successful! You can now switch to the login view.');
      setUsername('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      console.log('Registration attempt successful.');
    } catch (err: any) {
      console.error('Register component caught error:', err.message);
    }
  };

  // Determine which message to display
  const displayMessage = localError || authError || success || '\u00A0'; // Non-breaking space
  const MessageComponent = localError ? ErrorMessage : authError ? ErrorMessage : success ? SuccessMessage : Message;


  return (
    <FormWrapper>
      <Title>Register</Title>
      <StyledForm onSubmit={handleRegister}>
        <FormGroup>
          <Label htmlFor="register-username">Username</Label>
          <Input
            type="text"
            id="register-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Choose a username"
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="register-email">Email</Label>
          <Input
            type="email"
            id="register-email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Enter your email address"
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="register-password">Password</Label>
          <Input
            type="password"
            id="register-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Create a password"
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="confirm-password">Confirm Password</Label>
          <Input
            type="password"
            id="confirm-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={isLoading}
            placeholder="Confirm your password"
          />
        </FormGroup>

        {/* Display relevant message (error or success) */}
        <MessageComponent>{displayMessage}</MessageComponent>

        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Registering...' : 'Register'}
        </Button>
      </StyledForm>
    </FormWrapper>
  );
};

export default Register;