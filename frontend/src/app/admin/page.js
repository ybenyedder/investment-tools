"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('it_token');
        if (!token) {
          setError("No authentication token found. Please login on the home page.");
          setLoading(false);
          return;
        }

        const res = await fetch('/api/admin/stats', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!res.ok) {
          if (res.status === 403 || res.status === 401) {
            setError("You do not have admin privileges.");
          } else {
            setError("Failed to fetch admin stats.");
          }
          setLoading(false);
          return;
        }

        const data = await res.json();
        setStats(data);
      } catch (err) {
        setError("Network error.");
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8 text-white">
        <div className="animate-spin text-4xl">⏳</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            🛡️ Admin Forensic Dashboard
          </h1>
          <Link href="/" className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors border border-slate-700">
            ← Back to App
          </Link>
        </div>

        {error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
            <h2 className="text-xl text-red-400 font-semibold mb-2">Access Denied</h2>
            <p className="text-slate-400">{error}</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                <div className="text-sm text-slate-400 uppercase font-semibold tracking-wider">Total API Connections</div>
                <div className="text-4xl font-bold text-emerald-400 mt-2">{stats.total_connections}</div>
              </div>
              <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                <div className="text-sm text-slate-400 uppercase font-semibold tracking-wider">Total Logins & Attempts</div>
                <div className="text-4xl font-bold text-blue-400 mt-2">{stats.total_logins}</div>
              </div>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center">
                <h2 className="font-semibold text-white">Audit Log (Recent 500)</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                    <tr>
                      <th className="px-4 py-3">ID</th>
                      <th className="px-4 py-3">Timestamp</th>
                      <th className="px-4 py-3">IP Address</th>
                      <th className="px-4 py-3">Event</th>
                      <th className="px-4 py-3">User Email</th>
                      <th className="px-4 py-3">Endpoint</th>
                      <th className="px-4 py-3">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.forensic_logs && stats.forensic_logs.length > 0 ? (
                      stats.forensic_logs.map((log) => (
                        <tr key={log.id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                          <td className="px-4 py-3 text-slate-500">#{log.id}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-slate-300">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">{log.ip_address}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              log.event_type.includes('LOGIN') ? 'bg-blue-500/20 text-blue-300' : 'bg-emerald-500/20 text-emerald-300'
                            }`}>
                              {log.event_type}
                            </span>
                          </td>
                          <td className="px-4 py-3">{log.user_email || <span className="text-slate-600">-</span>}</td>
                          <td className="px-4 py-3 text-slate-400 font-mono text-xs truncate max-w-[200px]" title={log.endpoint}>
                            {log.endpoint}
                          </td>
                          <td className="px-4 py-3 text-slate-400 truncate max-w-[200px]" title={log.details}>
                            {log.details || <span className="text-slate-600">-</span>}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="7" className="px-4 py-8 text-center text-slate-500">
                          No audit logs found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
