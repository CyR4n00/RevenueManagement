import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders app header', () => {
  render(<App />);
  const headerElement = screen.getByText(/レベニューコントロール/i);
  expect(headerElement).toBeInTheDocument();
});
