import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

test('renders app header', async () => {
  // Mock API responses to prevent network errors in test
  mockedAxios.get.mockImplementation((url) => {
    if (url.includes('market_data')) {
      return Promise.resolve({ data: [] });
    }
    if (url.includes('alerts')) {
      return Promise.resolve({ data: [] });
    }
    if (url.includes('recommendation')) {
      return Promise.resolve({ data: { suggested_price: 10000, reasoning: 'test', date: '2026-07-20' } });
    }
    return Promise.resolve({ data: {} });
  });

  render(<App />);
  const headerElement = await screen.findByText(/レベニューアシスタント/i);
  expect(headerElement).toBeInTheDocument();
});
