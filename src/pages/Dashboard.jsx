import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { SkeletonStats, SkeletonTableRow } from '../components/Skeletons';
import { FileText, AlertTriangle, CheckCircle2, Clock, Upload, TrendingUp } from 'lucide-react';
// Static summary data from extraction logic (no backend required)
// If present, this will drive the dashboard counts and summary cards.
import summary from '../../algo/data.json';
import { useRef } from 'react';

const Dashboard = ({ invoices }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [hoveredCard, setHoveredCard] = useState(null);

  // Try to fetch the JSON at runtime as an asset as well, to avoid bundling issues
  const hasFetched = useRef(false);
  const [summaryData, setSummaryData] = useState(null);
  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1500);

    if (!hasFetched.current) {
      hasFetched.current = true;
      try {
const url = new URL('../../algo/data.json', import.meta.url);
        fetch(url)
          .then((r) => (r.ok ? r.json() : null))
          .then((json) => {
            if (json && typeof json === 'object') setSummaryData(json);
          })
          .catch(() => {});
      } catch {}
    }

    return () => clearTimeout(timer);
  }, []);

  const stats = useMemo(() => {
    const src = summaryData || summary;
    if (src && typeof src.total_invoices === 'number') {
      const total = src.total_invoices || 0;
      const valid = src.validated || 0;
      const pending = Math.max(0, total - valid);
      const totalAnomalies = src.total_anomalies || 0;
      return { total, pending, valid, totalAnomalies };
    }

    // Fallback to computing from invoices prop
    const total = invoices.length;
    const pending = invoices.filter(inv => inv.status === 'pending').length;
    const valid = invoices.filter(inv => inv.status === 'verified').length;
    const totalAnomalies = invoices.reduce((sum, inv) =>
      sum + inv.anomalies.filter(a => !a.resolved).length, 0
    );

    return { total, pending, valid, totalAnomalies };
  }, [invoices, summaryData]);

  const StatCard = ({ title, value, icon, trend, className = '', index }) => (
    <div 
      className={`glass-card rounded-xl p-6 transition-all duration-300 hover-lift hover-glow ${
        hoveredCard === index ? 'scale-105' : ''
      } ${className}`}
      onMouseEnter={() => setHoveredCard(index)}
      onMouseLeave={() => setHoveredCard(null)}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        <div className={`p-2 rounded-xl bg-white/10 transition-transform duration-300 ${
          hoveredCard === index ? 'scale-110 rotate-12' : ''
        }`}>
          {icon}
        </div>
      </div>
      <div className="flex items-end justify-between">
        <div className="text-2xl font-bold text-white">{value}</div>
        {trend && (
          <div className="flex items-center gap-1 text-green-400 text-sm">
            <TrendingUp className="h-4 w-4" />
            <span>{trend}</span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen gradient-dark">
      <Header />
      
      <main className="container mx-auto px-6 py-8 space-y-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="text-3xl font-bold text-white hover-lift inline-block">
              Invoice Dashboard
            </h1>
            <p className="text-gray-400 mt-1">
              Monitor and review your invoice analysis results
            </p>
          </div>
          
          <button
            onClick={() => navigate('/upload')}
            className="gradient-accent text-white px-6 py-3 rounded-lg font-semibold hover:opacity-90 transition-all duration-300 hover-lift hover-glow flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            Upload More
          </button>
        </div>

        {/* Stats Cards with Enhanced Skeletons */}
        {loading ? (
          <SkeletonStats />
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Invoices"
              value={stats.total}
              icon={<FileText className="h-5 w-5 text-blue-400" />}
              trend="+12%"
              index={0}
            />
            <StatCard
              title="Total Anomalies"
              value={stats.totalAnomalies}
              icon={<AlertTriangle className="h-5 w-5 text-red-400" />}
              index={1}
            />
            <StatCard
              title="Validated"
              value={stats.valid}
              icon={<CheckCircle2 className="h-5 w-5 text-green-400" />}
              trend="+8%"
              index={2}
            />
            <StatCard
              title="Pending Review"
              value={stats.pending}
              icon={<Clock className="h-5 w-5 text-yellow-400" />}
              index={3}
            />
          </div>
        )}

        {/* Extraction summary cards from data.json (hsn/upi/other/duplicates) */}
        {(summaryData || summary) && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <div className="glass-card rounded-xl p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">HSN Validation</h3>
              <div className="space-y-1 text-white text-sm">
                <div className="flex justify-between"><span>Missing both</span><span>{(summaryData||summary).hsn_validation?.missing_both ?? 0}</span></div>
                <div className="flex justify-between"><span>HSN not found</span><span>{(summaryData||summary).hsn_validation?.hsn_not_found ?? 0}</span></div>
                <div className="flex justify-between"><span>Filled from HSN</span><span>{(summaryData||summary).hsn_validation?.filled_from_hsn ?? 0}</span></div>
                <div className="flex justify-between"><span>Nonstandard slab</span><span>{(summaryData||summary).hsn_validation?.nonstandard_slab ?? 0}</span></div>
              </div>
            </div>

            <div className="glass-card rounded-xl p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">UPI</h3>
              <div className="space-y-1 text-white text-sm">
                <div className="flex justify-between"><span>Docs found</span><span>{(summaryData||summary).upi?.docs_found ?? 0}</span></div>
                <div className="flex justify-between"><span>Missing Txn ID</span><span>{(summaryData||summary).upi?.missing_txn_id ?? 0}</span></div>
                <div className="flex justify-between"><span>Missing sender</span><span>{(summaryData||summary).upi?.missing_sender ?? 0}</span></div>
                <div className="flex justify-between"><span>Amount mismatch</span><span>{(summaryData||summary).upi?.amount_mismatch ?? 0}</span></div>
              </div>
            </div>

            <div className="glass-card rounded-xl p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">Other Flags</h3>
              <div className="space-y-1 text-white text-sm">
                <div className="flex justify-between"><span>Missing GSTIN</span><span>{(summaryData||summary).other_flags?.missing_gstin ?? 0}</span></div>
                <div className="flex justify-between"><span>Missing PAN</span><span>{(summaryData||summary).other_flags?.missing_pan ?? 0}</span></div>
                <div className="flex justify-between"><span>Future dates</span><span>{(summaryData||summary).other_flags?.future_dates ?? 0}</span></div>
                <div className="flex justify-between"><span>Low OCR</span><span>{(summaryData||summary).other_flags?.low_ocr ?? 0}</span></div>
              </div>
            </div>

            <div className="glass-card rounded-xl p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">Duplicates</h3>
              <div className="space-y-1 text-white text-sm">
                <div className="flex justify-between"><span>Groups</span><span>{(summaryData||summary).duplicates_groups ?? 0}</span></div>
                <div className="flex justify-between"><span>Total docs in groups</span><span>{(summaryData||summary).duplicates_total_docs_in_groups ?? 0}</span></div>
              </div>
            </div>
          </div>
        )}

        {/* Invoice Table with Enhanced Skeleton */}
        <div className="glass-card rounded-xl overflow-hidden animate-slide-in hover-lift">
          <div className="p-6 border-b border-gray-700">
            <h2 className="text-xl font-semibold text-white">Recent Invoices</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left p-4 text-sm font-medium text-gray-400">Invoice ID</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-400">Vendor</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-400">Amount</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-400">Status</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <>
                    <SkeletonTableRow delay={0} />
                    <SkeletonTableRow delay={100} />
                    <SkeletonTableRow delay={200} />
                  </>
                ) : (
                  invoices.map((invoice, index) => (
                    <tr 
                      key={invoice.id} 
                      className="border-b border-gray-800 hover:bg-white/5 transition-all duration-300 group animate-fade-in stagger-1"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      <td className="p-4 font-mono text-sm text-white group-hover:text-blue-300 transition-colors">
                        {invoice.id}
                      </td>
                      <td className="p-4 text-white group-hover:text-gray-200 transition-colors">
                        {invoice.vendor}
                      </td>
                      <td className="p-4 font-semibold text-white group-hover:scale-105 transition-transform">
                        ${invoice.amount.toLocaleString()}
                      </td>
                      <td className="p-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-300 group-hover:scale-110 ${
                          invoice.status === 'valid' 
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                            : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                        }`}>
                          {invoice.status === 'valid' ? 'Validated' : 'Pending'}
                        </span>
                      </td>
                      <td className="p-4">
                        <button
                          onClick={() => navigate(`/review/${invoice.id}`)}
                          className="gradient-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-all duration-300 hover-lift hover-glow"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;