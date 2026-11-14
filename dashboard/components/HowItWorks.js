'use client';
import { useEffect, useRef } from 'react';
import { Brain, Calculator, ClipboardCheck, Cpu, Database, Gavel, ScanSearch, Search, X } from 'lucide-react';

const STEPS = [
  { Icon: ScanSearch, title: 'Triage Planner', desc: 'Deterministic scan of every facility-medicine pair into severity tiers.' },
  { Icon: Calculator, title: 'Reconciler', desc: 'Trust-adjusted stock and discrepancies, computed without an LLM.' },
  { Icon: Search, title: 'Investigator', desc: 'Formulates 3+ competing hypotheses grounded in evidence queries.' },
  { Icon: Gavel, title: 'Skeptic + Number Auditor', desc: 'Challenges causes and re-verifies every single number against deterministic truth (up to 3 rounds).' },
  { Icon: ClipboardCheck, title: 'Action Planner', desc: 'Formulates approval-ready action recommendations for the human officer.' },
];

export default function HowItWorks({ isOpen, onClose }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e) => {
      e.preventDefault();
      onClose();
    };

    dialog.addEventListener('cancel', handleCancel);
    return () => dialog.removeEventListener('cancel', handleCancel);
  }, [onClose]);

  if (!isOpen) return null;

  return (
    <dialog
      ref={dialogRef}
      className="modal-dialog"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className="dialog-header">
        <div>
          <h2>How MedTrace decides</h2>
          <p className="dialog-subtitle">Numbers by deterministic arithmetic, reasoning by agents, decisions by human officers.</p>
        </div>
        <button className="btn-ghost" onClick={onClose} aria-label="Close dialog">
          <X size={18} />
        </button>
      </div>

      <div className="dialog-body">
        <ol className="flow-steps">
          {STEPS.map(({ Icon, title, desc }, index) => (
            <li key={title} className="flow-step-item">
              <span className="flow-step-icon" aria-hidden="true">
                <Icon size={16} />
              </span>
              <div className="flow-step-content">
                <strong>{index + 1}. {title}</strong>
                <p>{desc}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="dialog-tech-section">
          <h4>Core integrated technologies</h4>
          <div className="tech-chips">
            <span className="badge badge-info">
              <Database size={13} aria-hidden="true" />
              <span><strong>Zetaris</strong> Lightning SQL (MEDTRACE_LH)</span>
            </span>
            <span className="badge badge-skeptic">
              <Brain size={13} aria-hidden="true" />
              <span><strong>Meterless H-MEM & World Model</strong> officer decision memory</span>
            </span>
            <span className="badge badge-mute">
              <Cpu size={13} aria-hidden="true" />
              <span><strong>NVIDIA Nemotron</strong> reasoning (qualitative only; no arithmetic)</span>
            </span>
          </div>
        </div>
      </div>

      <div className="dialog-footer">
        <button className="btn btn-primary" onClick={onClose}>
          Got it
        </button>
      </div>
    </dialog>
  );
}
