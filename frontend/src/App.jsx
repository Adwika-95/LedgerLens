import React, { useState, useEffect } from 'react';
import { Search, AlertCircle, CheckCircle, Database } from 'lucide-react';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLog, setChatLog] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch initial dashboard data
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/reconciliation/summary')
      .then(res => res.json())
      .then(data => setSummary(data));
      
    fetch('http://127.0.0.1:8000/api/reconciliation/exceptions')
      .then(res => res.json())
      .then(data => setExceptions(data.exceptions));
  }, []);

  const handleChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput;
    setChatInput('');
    setChatLog(prev => [...prev, { type: 'user', text: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage })
      });
      const data = await response.json();
      
      setChatLog(prev => [...prev, { 
        type: 'agent', 
        explanation: data.explanation,
        sql: data.sql,
        rows: data.rows 
      }]);
    } catch (error) {
      setChatLog(prev => [...prev, { type: 'error', text: 'Failed to reach AI agent.' }]);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 font-sans">
      <header className="mb-8 flex items-center gap-3 border-b pb-4">
        <Database className="text-blue-600 w-8 h-8" />
        <h1 className="text-3xl font-bold tracking-tight">AI Finance Controller</h1>
      </header>

      {/* KPI Metrics */}
      {summary && (
        <div className="grid grid-cols-4 gap-6 mb-8">
          {[
            { label: 'Total Transactions', val: summary.total_transactions, color: 'border-slate-200' },
            { label: 'Matched Records', val: summary.matched, color: 'border-green-200 text-green-700' },
            { label: 'Exceptions Found', val: summary.exceptions, color: 'border-red-200 text-red-700' },
            { label: 'Match Rate', val: `${summary.match_rate}%`, color: 'border-blue-200 text-blue-700' }
          ].map((kpi, i) => (
            <div key={i} className={`bg-white p-6 rounded-xl border-l-4 shadow-sm ${kpi.color}`}>
              <p className="text-sm text-slate-500 font-medium uppercase tracking-wider">{kpi.label}</p>
              <p className="text-3xl font-bold mt-2">{kpi.val}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        {/* Left: AI Chat Terminal */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-[600px]">
          <div className="p-4 border-b bg-slate-100 rounded-t-xl font-semibold">
            Reconciliation Copilot
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatLog.map((msg, idx) => (
              <div key={idx} className={`flex flex-col ${msg.type === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.type === 'user' ? (
                  <div className="bg-blue-600 text-white px-4 py-2 rounded-2xl max-w-[80%]">
                    {msg.text}
                  </div>
                ) : (
                  <div className="bg-slate-100 p-4 rounded-xl max-w-[95%] border border-slate-200">
                    <p className="text-slate-800 font-medium mb-3">{msg.explanation}</p>
                    {msg.sql && (
                      <div className="bg-slate-800 text-green-400 font-mono text-xs p-3 rounded-md overflow-x-auto">
                        {msg.sql}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="text-slate-400 text-sm animate-pulse">Agent is analyzing ledger...</div>}
          </div>

          <form onSubmit={handleChat} className="p-4 border-t flex gap-2">
            <input 
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="e.g., Why did order ORD_0053 fail?"
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2">
              <Search className="w-4 h-4" /> Ask
            </button>
          </form>
        </div>

        {/* Right: Exception Grid */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 h-[600px] flex flex-col">
          <div className="p-4 border-b bg-slate-100 rounded-t-xl font-semibold flex justify-between items-center">
            <span>Exception Audit Log</span>
            <span className="bg-red-100 text-red-700 text-xs px-2 py-1 rounded-full font-bold">
              {exceptions.length} Anomalies
            </span>
          </div>
          <div className="overflow-auto p-0">
            <table className="w-full text-left border-collapse text-sm">
              <thead className="bg-slate-50 sticky top-0 border-b">
                <tr>
                  <th className="p-3 font-medium text-slate-500">Order ID</th>
                  <th className="p-3 font-medium text-slate-500">Status</th>
                  <th className="p-3 font-medium text-slate-500 text-right">Expected (₹)</th>
                  <th className="p-3 font-medium text-slate-500 text-right">Delta (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {exceptions.map((exc, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="p-3 font-mono">{exc.order_id}</td>
                    <td className="p-3">
                      <span className="flex items-center gap-1 text-xs font-bold text-red-600 bg-red-50 px-2 py-1 rounded-md w-fit">
                        <AlertCircle className="w-3 h-3" /> {exc.reconciliation_status}
                      </span>
                    </td>
                    <td className="p-3 text-right">{exc.expected_settlement}</td>
                    <td className="p-3 text-right text-red-600 font-medium">
                      {exc.discrepancy ? Math.abs(exc.discrepancy).toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}