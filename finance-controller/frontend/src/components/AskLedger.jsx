import { useState } from 'react';
import { ArrowRight } from 'lucide-react';

const EXAMPLES = [
  'Which orders are stuck unsettled the longest?',
  'Total amount lost to amount mismatches',
  'Show every duplicate UTR',
];

export default function AskLedger({ onAsk }) {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (q) => {
    const text = (q || question).trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const data = await onAsk(text);
      setResult({ question: text, ...data });
    } catch (e) {
      setError(e.message || 'The agent could not answer that.');
    }
    setLoading(false);
    setQuestion('');
  };

  return (
    <div className="border border-line rounded-sm bg-white p-5">
      <h2 className="font-serif text-lg text-ink mb-3">Ask the ledger</h2>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex gap-2 mb-3"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Why did ORD_0053 fail to settle?"
          className="flex-1 border border-line rounded-sm px-3 py-2 text-sm focus:outline-none focus:border-ink"
        />
        <button
          type="submit"
          disabled={loading}
          className="border border-ink bg-ink text-white px-3 py-2 rounded-sm text-sm flex items-center gap-1 disabled:opacity-50"
        >
          Ask <ArrowRight size={14} />
        </button>
      </form>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => submit(ex)}
            className="text-xs text-steel border border-line rounded-sm px-2 py-1 hover:border-ink hover:text-ink"
          >
            {ex}
          </button>
        ))}
      </div>

      {loading && <p className="text-xs text-steel">Querying the ledger…</p>}
      {error && <p className="text-xs text-amber">{error}</p>}

      {result && !loading && (
        <div className="border-t border-line pt-3">
          <p className="text-xs text-steel mb-1">{result.question}</p>
          <p className="text-sm text-ink mb-2">{result.explanation}</p>
          {typeof result.execution_time_ms === 'number' && (
            <p className="text-[11px] text-steel mb-2">
              {result.rows?.length ?? 0} row(s) · {result.execution_time_ms} ms
            </p>
          )}
          {result.sql && (
            <details>
              <summary className="text-xs text-steel cursor-pointer">View generated SQL</summary>
              <pre className="font-mono text-[11px] bg-paper border border-line rounded-sm p-2 mt-1 overflow-x-auto">
                {result.sql}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
