import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import axios from 'axios';

jest.mock('axios');

test('renders app header', async () => {
  // Mock successful response to avoid unhandled promise rejections
  (axios.get as jest.Mock).mockResolvedValue({ data: [] });

  render(<App />);
  const headerElement = await screen.findByText(/レベニューアシスタント/i);
  expect(headerElement).toBeInTheDocument();
});
