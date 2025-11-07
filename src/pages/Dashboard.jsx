import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { SkeletonStats, SkeletonTableRow } from '../components/Skeletons';
import { FileText, AlertTriangle, CheckCircle2, Clock, Upload, TrendingUp } from 'lucide-react';

const Dashboard = ({ invoices }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [hoveredCard, setHoveredCard] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  const stats = useMemo(() => {
    const total = invoices.length;
    const pending = invoices.filter(inv => inv.status === 'pending').length;
    const valid = invoices.filter(inv => inv.status === 'valid').length;
    const totalAnomalies = invoices.reduce((sum, inv) => 
      sum + inv.anomalies.filter(a => !a.resolved).length, 0
    );

    return { total, pending, valid, totalAnomalies };
  }, [invoices]);

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