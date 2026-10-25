'use client';
import { useEffect, useState } from 'react';
import { ChevronDown, Brain, Calculator, ClipboardCheck, Database, Gavel, ScanSearch, Search, Cpu } from 'lucide-react';

// Facts from README.md / SPONSOR_TECH.md. Wording stays literal: no accuracy or "zero hallucination" claims.
const STEPS = [
  { Icon: ScanSearch, t: 'Triage Planner', d: 'Deterministic scan of every facility-medicine pair into tiers', c: 'var(--accent)' },
  { Icon: Calculator, t: 'Reconciler', d: 'Trust-adjusted stock and discrepancies, computed without an LLM', c: 'var(--accent)' },
  { Icon: Search, t: 'Investigator', d: '3+ competing hypotheses', c: 'var(--accent)', pair: true },
  { Icon: Gavel, t: 'Skeptic + Number Auditor', d: 'Challenges them and re-checks quoted figures; up to 3 rounds', c: 'var(--skep)', pair: true },
  { Icon: ClipboardCheck, t: 'Action Planner', d: 'Approval-ready pack; a human officer decides', c: 'var(--ok)' },
];

export default function HowItWorks() {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    try {
      const v = window.localStorage.getItem('medtrace-how');
      if (v) setOpen(v === '1');
      else if (window.innerWidth < 960) setOpen(false);
    } catch {
      /* ignore */
    }
  }, []);
  const toggle = () => {
    setOpen((o) => {
      try { window.localStorage.setItem('medtrace-how', o ? '0' : '1'); } catch { /* ignore */ }
      return !o;
    });
  };
  return (
    <section className="how panel" aria-label="How MedTrace decides">
      <button className="how-h" onClick={toggle} aria-expanded={open}>
        <b>How MedTrace decides</b>
        <span className="sub">numbers by deterministic code, reasoning by agents, decisions by people</span>
        <ChevronDown className={`ic chev ${open ? '' : 'shut'}`} />
      </button>
      {open ? (
        <div className="how-b">
          <ol className="flow">
            {STEPS.map(({ Icon, t, d, c, pair }, i) => (
              <li key={t} className={`fstep ${pair ? 'pair' : ''}`} style={{ '--nc': c }}>
                <span className="fic"><Icon className="ic" /></span>
                <span><b>{t}</b><span className="fd">{d}</span></span>
                {i < STEPS.length - 1 ? <span className="farrow" aria-hidden="true">{pair && STEPS[i + 1].pair ? '⇄' : '→'}</span> : null}
              </li>
            ))}
          </ol>
          <div className="chips2">
            <span className="chip2"><Database className="ic" /><b>Zetaris</b> Lightning SQL (MEDTRACE_LH)</span>
            <span className="chip2"><Brain className="ic" /><b>Meterless H-MEM</b> officer-decision memory</span>
            <span className="chip2"><Cpu className="ic" /><b>NVIDIA Nemotron</b> LLM reasoning (sample mode runs without it)</span>
          </div>
        </div>
      ) : null}
    </section>
  );
}