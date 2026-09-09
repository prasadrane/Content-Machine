import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import DemoBanner from './DemoBanner.jsx';

vi.mock('../api/client.js', () => ({
  fetchJson: vi.fn(),
}));

import { fetchJson } from '../api/client.js';

test('shows free-tier notice in demo mode', async () => {
  fetchJson.mockResolvedValue({ demo_mode: true, llm: 'gemini' });
  render(<DemoBanner />);
  await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
  expect(screen.getByText(/free-tier Gemini quota/i)).toBeInTheDocument();
});

test('renders nothing outside demo mode', async () => {
  fetchJson.mockResolvedValue({ demo_mode: false, llm: 'relay' });
  const { container } = render(<DemoBanner />);
  await waitFor(() => expect(fetchJson).toHaveBeenCalled());
  expect(container.querySelector('[role="status"]')).toBeNull();
});

test('fetch failure renders nothing', async () => {
  fetchJson.mockRejectedValue(new Error('offline'));
  const { container } = render(<DemoBanner />);
  await new Promise((r) => setTimeout(r, 0));
  expect(container.querySelector('[role="status"]')).toBeNull();
});
