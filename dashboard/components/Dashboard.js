'use client';
import { useEffect, useState } from 'react';
import Alerts from './Alerts.js';
import Detail from './Detail.js';
import Why from './Why.js';
import MemoryCard from './MemoryCard.js';
import EvalPanel from './EvalPanel.js';
import { useApi } from './ui.js';

export default function Dashboard() {
  const alerts = useApi('/api/alerts');
  const backend = useApi('/api/backend');
  const memory = useApi('/api/memory');
  const evalApi = useApi('/api/eval');
  const [sel, setSel] = useState(null);
  const detail = useApi(sel ? `/api/detail?facility=${encodeURIComponent(sel.facility_id)}&medicine=${encodeURIComponent(sel.medicine_id)}` : null);
  const be = backend.data;

  // Deep link: /?facility=FAC-CHC-01&medicine=MED-001 pre-selects an alert.
  useEffect(() => {
    if (sel || !alerts.data?.items?.length) return;
    const sp = new URLSearchParams(window.location.search);
    const hit = alerts.data.items.find((i) => i.facility_id === sp.get('facility') && i.medicine_id === sp.get('medicine'));
    if (hit) setSel(hit);
  }, [alerts.data, sel]);

  const select = (item) => {
    setSel(item);
    window.history.replaceState(null, '', `?facility=${encodeURIComponent(item.facility_id)}&medicine=${encodeURIComponent(item.medicine_id)}`);
  };

  const onRan = () => {
    detail.reload();
    alerts.reload();
    backend.reload();
  };

  return (
    <div className="wrap">
      <div className="top">
        <div>
          <h1>MedTrace Dashboard</h1>
          <div className="sub">Read-only view over run outputs in this repo. Inventory data is simulated.</div>
        </div>
        <div className="chips">
          <span className={`badge ${be?.reachable ? 'b-ok' : 'b-mute'}`} title={be?.error || ''}>
            {backend.status === 'loading' && !be ? 'checking backend...' : be?.reachable ? `Backend online${be.sample_mode ? ' (sample mode)' : ''}` : 'Backend offline - stored runs only'}
          </span>
          <button onClick={backend.reload}>Re-check</button>
        </div>
      </div>

      <Alerts api={alerts} selected={sel ? `${sel.facility_id}/${sel.medicine_id}` : null} onSelect={select} />

      <div className="grid">
        <Detail item={sel} api={detail} backend={be} onRan={onRan} />
        <Why item={sel} api={detail} backend={be} />
      </div>

      <div className="grid2">
        <MemoryCard api={memory} />
        <EvalPanel api={evalApi} />
      </div>
    </div>
  );
}