import React from 'react';
import { render, screen, act } from '@testing-library/react';
import App from './App';
import axios from 'axios';

jest.mock('axios');
jest.mock('./supabase', () => ({
  supabase: null,
  authIsConfigured: false,
  runtimeConfig: { apiUrl: '' },
}));

test('renders app header', async () => {
  jest.spyOn(axios, 'get').mockImplementation((url) => {
    if (url.includes('recommendations')) {
      return Promise.resolve({ data: [] });
    }
    if (url.includes('recommendation')) {
      return Promise.resolve({ data: { suggested_price: 10000, suggested_rank: 'C', reasoning: 'test' } });
    }
    return Promise.resolve({ data: [] });
  });
  await act(async () => {
    render(<App />);
  });
  const headerElement = screen.getByRole('heading', { name: '価格分析ダッシュボード' });
  expect(headerElement).toBeInTheDocument();
  const requestedUrls = (axios.get as jest.Mock).mock.calls.map(([url]) => url);
  expect(requestedUrls.some((url) => url.endsWith('/market_data/cached'))).toBe(true);
  expect(requestedUrls.some((url) => url.endsWith('/market_data'))).toBe(false);
});
