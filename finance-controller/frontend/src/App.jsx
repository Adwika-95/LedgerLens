import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import LedgerStrip from './components/LedgerStrip';
import ExceptionsTable from './components/ExceptionsTable';
import ExceptionBreakdownChart from './components/ExceptionBreakdownChart';
import AskLedger from './components/AskLedger';

const API_BASE = 'http://127.0.0.1:8000';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [running, setRunning] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [summaryRes, exceptionsRes] = await Promise.all([
        fetch(`${API_BASE}/api/reconciliation/summary`),
        fetch(`${API_BASE}/api/reconciliation/exceptions`),
      ]);
      if (!summaryRes.ok || !exceptionsRes.ok) throw new Error('Backend not reachable');
      setSummary(await summaryRes.json());
      const excData = await exceptionsRes.json();
      setExceptions(excData.exceptions || []);
      setLoadError(null);
    } catch (e) {
      setLoadError('Could not reach the backend at ' + API_BASE + '. Is uvicorn running?');
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runBatch = async () => {
    setRunning(true);
    try {
      await fetch(`${API_BASE}/api/reconciliation/run`, { method: 'POST' });
      await loadData();
    } catch (e) {
      setLoadError('Reconciliation run failed.');
    }
    setRunning(false);
  };

  const askAgent = async (question) => {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail?.error || 'The agent could not answer that.');
    }
    return res.json();
  };

  return (
    <div className="min-h-screen bg-paper text-ink font-sans">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <header className="flex items-baseline justify-between mb-6 pb-4 border-b border-line">
          <div>
            <h1 className="font-serif text-2xl text-ink">AI Finance Controller</h1>
            <p className="text-sm text-steel mt-0.5">Merchant settlement reconciliation ledger</p>
          </div>
          <button
            onClick={runBatch}
            disabled={running}
            className="flex items-center gap-2 border border-ink text-ink px-3 py-1.5 rounded-sm text-sm hover:bg-ink hover:text-white disabled:opacity-50"
          >
            <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
            {running ? 'Running…' : 'Run reconciliation'}
          </button>
        </header>

        {loadError && (
          <div className="mb-6 border border-amber bg-amber-soft text-amber text-sm px-4 py-3 rounded-sm">
            {loadError}
          </div>
        )}

        <div className="mb-6">
          <LedgerStrip summary={summary} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-[600px]">
            <ExceptionsTable exceptions={exceptions} />
          </div>

          <div className="flex flex-col gap-6">
            <div className="border border-line rounded-sm bg-white p-5">
              <h2 className="font-serif text-lg text-ink mb-3">Exceptions by type</h2>
              <ExceptionBreakdownChart breakdown={summary?.breakdown} />
            </div>

            <AskLedger onAsk={askAgent} />
          </div>
        </div>
      </div>
    </div>
  );
}
