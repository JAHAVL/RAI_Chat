import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login page initially', () => {
  render(<App />);
  // Check for the "Login" heading which should be present initially
  const headingElement = screen.getByRole('heading', { name: /login/i });
  expect(headingElement).toBeInTheDocument();
});
