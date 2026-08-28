"use client";

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

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

  // Compute BI Data
  const biData = useMemo(() => {
    if (!stats || !stats.forensic_logs) return null;
    const logs = stats.forensic_logs;

    // 1. Time Series Data (Events per Hour/Day)
    const timeMap = {};
    logs.forEach(log => {
      // Group by Hour
      const d = new Date(log.timestamp);
      const key = `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:00`;
      if (!timeMap[key]) timeMap[key] = { time: key, connections: 0, logins: 0 };
      if (log.event_type.includes('LOGIN')) timeMap[key].logins += 1;
      else timeMap[key].connections += 1;
    });
    const timeSeries = Object.values(timeMap).reverse();

    // 2. Events Breakdown
    const loginsCount = logs.filter(l => l.event_type.includes('LOGIN')).length;
    const connCount = logs.filter(l => !l.event_type.includes('LOGIN')).length;
    const eventPie = [
      { name: 'Connections', value: connCount },
      { name: 'Logins', value: loginsCount }
    ];

    // 3. Top Endpoints
    const endpointMap = {};
    logs.forEach(log => {
      if (log.endpoint) {
        endpointMap[log.endpoint] = (endpointMap[log.endpoint] || 0) + 1;
      }
    });
    const topEndpoints = Object.entries(endpointMap)
      .map(([name, count]) => ({ name: name.split('?')[0].substring(0, 25), count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return { timeSeries, eventPie, topEndpoints };
  }, [stats]);

  const COLORS = ['#34d399', '#60a5fa', '#f87171', '#fbbf24', '#c084fc'];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8 text-white">
        <div className="animate-spin text-4xl text-blue-500">⏳</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8 border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 tracking-tight flex items-center gap-3">
              Power BI Analytics Dashboard
            </h1>
            <p className="text-slate-400 mt-1 text-sm">Real-time forensic insights and system statistics.</p>
          </div>
          <Link href="/" className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-semibold transition-all border border-slate-700 shadow-md">
            ← Back to App
          </Link>
        </div>

        {error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center shadow-lg">
            <h2 className="text-xl text-red-400 font-semibold mb-2">Access Denied</h2>
            <p className="text-slate-400">{error}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Total Connections</div>
                <div className="text-4xl font-black text-white">{stats.total_connections.toLocaleString()}</div>
                <div className="text-xs text-emerald-400 mt-2 font-medium">↑ Active tracking</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Total Logins</div>
                <div className="text-4xl font-black text-white">{stats.total_logins.toLocaleString()}</div>
                <div className="text-xs text-blue-400 mt-2 font-medium">Authentication events</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Logs Captured</div>
                <div className="text-4xl font-black text-white">{stats.forensic_logs?.length || 0}</div>
                <div className="text-xs text-purple-400 mt-2 font-medium">In recent memory buffer</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">System Status</div>
                <div className="text-4xl font-black text-emerald-400">HEALTHY</div>
                <div className="text-xs text-slate-500 mt-2 font-medium">All services operational</div>
              </div>
            </div>

            {/* Charts Section */}
            {biData && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Time Series Line Chart */}
                <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                  <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-6">Traffic Over Time</h3>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={biData.timeSeries}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="time" stroke="#64748b" tick={{fontSize: 12}} />
                        <YAxis stroke="#64748b" tick={{fontSize: 12}} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                          itemStyle={{ color: '#f1f5f9' }}
                        />
                        <Legend wrapperStyle={{ paddingTop: '20px' }} />
                        <Line type="monotone" dataKey="connections" stroke="#34d399" strokeWidth={3} dot={{r: 4}} activeDot={{r: 6}} name="API Connections" />
                        <Line type="monotone" dataKey="logins" stroke="#60a5fa" strokeWidth={3} dot={{r: 4}} activeDot={{r: 6}} name="Login Events" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Event Distribution Pie Chart */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col">
                  <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-2">Traffic Composition</h3>
                  <div className="flex-1 min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={biData.eventPie}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {biData.eventPie.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                          itemStyle={{ color: '#f1f5f9' }}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Top Endpoints Bar Chart */}
                <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
                  <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-6">Most Accessed Endpoints</h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={biData.topEndpoints} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={true} vertical={false} />
                        <XAxis type="number" stroke="#64748b" />
                        <YAxis dataKey="name" type="category" stroke="#64748b" width={150} tick={{fontSize: 12}} />
                        <Tooltip 
                          cursor={{fill: '#1e293b'}}
                          contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                        />
                        <Bar dataKey="count" fill="#818cf8" radius={[0, 4, 4, 0]} barSize={30} name="Total Requests">
                          {biData.topEndpoints.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[(index+2) % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>
            )}

            {/* Raw Data Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl mt-8">
              <div className="p-5 border-b border-slate-800 flex justify-between items-center">
                <h2 className="font-bold text-white tracking-wide">Raw Forensic Log Data</h2>
                <span className="text-xs bg-slate-800 text-slate-400 px-3 py-1 rounded-full border border-slate-700">Displaying max 500 records</span>
              </div>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-slate-400 uppercase bg-slate-950 sticky top-0 z-10">
                    <tr>
                      <th className="px-5 py-4 font-semibold">ID</th>
                      <th className="px-5 py-4 font-semibold">Timestamp</th>
                      <th className="px-5 py-4 font-semibold">IP Address</th>
                      <th className="px-5 py-4 font-semibold">Event</th>
                      <th className="px-5 py-4 font-semibold">User Email</th>
                      <th className="px-5 py-4 font-semibold">Endpoint</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {stats.forensic_logs && stats.forensic_logs.length > 0 ? (
                      stats.forensic_logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="px-5 py-3 text-slate-500 font-mono text-xs">#{log.id}</td>
                          <td className="px-5 py-3 whitespace-nowrap text-slate-300 text-xs">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="px-5 py-3 font-mono text-xs text-slate-400">{log.ip_address}</td>
                          <td className="px-5 py-3">
                            <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider ${
                              log.event_type.includes('LOGIN') ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}>
                              {log.event_type}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-slate-300 text-xs">{log.user_email || <span className="text-slate-600 italic">Anonymous</span>}</td>
                          <td className="px-5 py-3 text-slate-400 font-mono text-[11px] truncate max-w-[250px]" title={log.endpoint}>
                            {log.endpoint}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="6" className="px-5 py-12 text-center text-slate-500">
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
