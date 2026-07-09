import React from 'react';
import { render, screen, act } from '@testing-library/react';
import App from './App';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

test('renders app header', async () => {
  mockedAxios.get.mockImplementation((url) => {
    if (url.includes('recommendation')) {
      return Promise.resolve({ data: { suggested_price: 10000, suggested_rank: 'C', reasoning: 'test' } });
    }
    return Promise.resolve({ data: [] });
  });
  await act(async () => {
    render(<App />);
  });
  const headerElement = screen.getByText(/マーケティングアシスタント/i);
  expect(headerElement).toBeInTheDocument();
});
