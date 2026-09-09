import { useEffect, useState } from 'react';
import { fetchJson } from '../api/client.js';

export default function DemoBanner() {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchJson('/api/meta')
      .then((m) => alive && setDemo(Boolean(m && m.demo_mode)))
      .catch(() => alive && setDemo(false));
    return () => { alive = false; };
  }, []);

  if (!demo) return null;
  return (
    <div role="status" className="bg-amber-100 text-amber-900 text-sm text-center py-2 px-4">
      Public demo &mdash; runs on free-tier Gemini quota. Limited usage; generation may degrade or stop mid-flight.
    </div>
  );
}
