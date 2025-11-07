import { useNavigate } from 'react-router-dom';
import { Eye, AlertTriangle, CheckCircle2, Clock, FileText } from 'lucide-react';

const InvoiceTable = ({ invoices }) => {
  const navigate = useNavigate();

  const getStatusIcon = (status, anomalies) => {
    const hasUnresolvedAnomalies = anomalies.some(a => !a.resolved);
    
    if (status === 'valid') {
      return <CheckCircle2 className="h-5 w-5 text-green-400" />;
    }
    
    if (hasUnresolvedAnomalies) {
      return <AlertTriangle className="h-5 w-5 text-red-400 animate-pulse" />;
    }
    
    return <Clock className="h-5 w-5 text-yellow-400" />;
  };

  const getStatusBadge = (status, anomalies) => {
    const hasUnresolvedAnomalies = anomalies.some(a => !a.resolved);
    
    if (status === 'valid') {
      return (
        <span className="px-3 py-1 rounded-full bg-green-400/20 text-green-400 text-xs font-medium border border-green-400/30">
          Validated
        </span>
      );
    }
    
    if (hasUnresolvedAnomalies) {
      return (
        <span className="px-3 py-1 rounded-full bg-red-400/20 text-red-400 text-xs font-medium border border-red-400/30 animate-pulse">
          Anomalies
        </span>
      );
    }
    
    return (
      <span className="px-3 py-1 rounded-full bg-yellow-400/20 text-yellow-400 text-xs font-medium border border-yellow-400/30">
        Pending
      </span>
    );
  };

  if (invoices.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center animate-scale-in">
        <div className="w-20 h-20 rounded-2xl bg-white/5 mx-auto mb-6 flex items-center justify-center">
          <FileText className="h-10 w-10 text-white/40" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-3">No invoices yet</h3>
        <p className="text-white/60 mb-8 max-w-md mx-auto">
          Upload your first invoice to get started with AI-powered analysis and anomaly detection
        </p>
        <button 
          onClick={() => navigate('/upload')}
          className="gradient-accent text-white px-8 py-4 rounded-2xl font-semibold hover:scale-105 transition-transform duration-300 glow-accent"
        >
          Upload Invoices
        </button>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden animate-fade-in-up">
      <div className="p-6 border-b border-white/10">
        <h2 className="text-2xl font-bold text-white">Recent Invoices</h2>
        <p className="text-white/60 mt-1">AI-analyzed invoices ready for review</p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-6 text-sm font-semibold text-white/70">Invoice ID</th>
              <th className="text-left p-6 text-sm font-semibold text-white/70">Vendor</th>
              <th className="text-left p-6 text-sm font-semibold text-white/70">Amount</th>
              <th className="text-left p-6 text-sm font-semibold text-white/70">Date</th>
              <th className="text-left p-6 text-sm font-semibold text-white/70">Status</th>
              <th className="text-left p-6 text-sm font-semibold text-white/70">Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice, index) => (
              <tr 
                key={invoice.id} 
                className="border-b border-white/5 hover:bg-white/5 transition-all duration-300 group"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <td className="p-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-cyan-400" />
                    </div>
                    <span className="font-mono text-sm text-white font-medium">{invoice.id}</span>
                  </div>
                </td>
                <td className="p-6 text-white font-medium">{invoice.vendor}</td>
                <td className="p-6">
                  <span className="text-lg font-bold text-white">
                    ${invoice.amount.toLocaleString()}
                  </span>
                </td>
                <td className="p-6 text-white/70">{invoice.date}</td>
                <td className="p-6">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(invoice.status, invoice.anomalies)}
                    {getStatusBadge(invoice.status, invoice.anomalies)}
                  </div>
                </td>
                <td className="p-6">
                  <button
                    onClick={() => navigate(`/review/${invoice.id}`)}
                    className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white font-medium transition-all duration-300 hover:scale-105 hover:glow-primary"
                  >
                    <Eye className="h-4 w-4" />
                    Review
                    <div className="w-0 group-hover:w-2 h-0.5 bg-white rounded transition-all duration-300" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InvoiceTable;