import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

test('guided demo: start button loads the sample and current step is marked', async () => {
  fetchJson.mockResolvedValue({ demo_mode: true, llm: 'gemini' });
  const onStart = vi.fn().mockResolvedValue();
  render(<DemoBanner activeTab="council" approved={false} onStart={onStart} onGoto={vi.fn()} />);
  const start = await screen.findByRole('button', { name: /start guided demo/i });
  fireEvent.click(start);
  await waitFor(() => expect(onStart).toHaveBeenCalledTimes(1));
  expect(screen.getByRole('button', { name: /2\. Council review/ })).toHaveAttribute('aria-current', 'step');
});

test('guided demo: approved council state advances to the approve step', async () => {
  fetchJson.mockResolvedValue({ demo_mode: true, llm: 'gemini' });
  render(<DemoBanner activeTab="council" approved onStart={vi.fn()} onGoto={vi.fn()} />);
  const step = await screen.findByRole('button', { name: /3\. You approve/ });
  expect(step).toHaveAttribute('aria-current', 'step');
});
