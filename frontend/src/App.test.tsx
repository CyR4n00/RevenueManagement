import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

test('renders app header and handles data fetch correctly', async () => {
  // Setup mock responses to prevent network errors during test
  mockedAxios.get.mockImplementation((url) => {
    if (url.includes('/market_data')) {
      return Promise.resolve({ data: [] });
    }
    if (url.includes('/alerts')) {
      return Promise.resolve({ data: [] });
    }
    if (url.includes('/recommendation')) {
      return Promise.resolve({ data: { suggested_price: 10000, suggested_rank: "A", reasoning: "Test" } });
    }
    return Promise.reject(new Error('not found'));
  });

  render(<App />);
  const headerElement = screen.getByText(/レベニューアシスタント/i);
  expect(headerElement).toBeInTheDocument();

  await waitFor(() => {
    expect(mockedAxios.get).toHaveBeenCalledTimes(3);
  });
});
