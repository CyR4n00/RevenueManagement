import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('axios', () => ({
  get: jest.fn((url) => {
    if (url.includes('/market_data')) return Promise.resolve({ data: [] });
    if (url.includes('/alerts')) return Promise.resolve({ data: [] });
    if (url.includes('/recommendation')) return Promise.resolve({ data: {
      date: '2026-07-20',
      suggested_price: 15000,
      suggested_rank: 'B',
      reasoning: 'Test'
    } });
    return Promise.resolve({ data: [] });
  })
}));

test('renders app header', () => {
  render(<App />);
  const headerElement = screen.getByText(/レベニューアシスタント/i);
  expect(headerElement).toBeInTheDocument();
});
