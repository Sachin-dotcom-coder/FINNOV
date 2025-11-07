import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { ArrowLeft, CheckCircle2, FileText } from 'lucide-react';

const Review = ({ invoices, onUpdateInvoice }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const invoice = useMemo(
    () => invoices.find(inv => inv.id === id),
    [invoices, id]
  );

  const [anomalies, setAnomalies] = useState(invoice?.anomalies || []);

  if (!invoice) {
    return (
      <div className="min-h-screen gradient-dark">
        <Header />
        <main className="container mx-auto px-6 py-12 text-center">
          <p className="text-gray-400">Invoice not found</p>
          <button onClick={() => navigate('/dashboard')} className="mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg">
            Back to Dashboard
          </button>
        </main>
      </div>
    );
  }

  const handleResolveAnomaly = (anomalyId) => {
    setAnomalies(prev => prev.filter(a => a.id !== anomalyId));
  };

  const handleMarkValid = () => {
    onUpdateInvoice(invoice.id, {
      status: 'valid',
      anomalies: [],
    });
    navigate('/summary');
  };

  const allResolved = anomalies.length === 0;

  return (
    <div className="min-h-screen gradient-dark">
      <Header />
      
      <main className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </button>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          <div className="space-y-6 animate-slide-in">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Invoice Preview</h2>
              <p className="text-gray-400">Review the invoice details</p>
            </div>

            <div className="glass-panel rounded-xl p-6">
              <div className="bg-white rounded-lg p-8 text-gray-800">
                <div className="space-y-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center mb-4">
                        <FileText className="h-6 w-6 text-blue-600" />
                      </div>
                      <h3 className="text-2xl font-bold">{invoice.vendor}</h3>
                    </div>
                    
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Invoice ID</p>
                      <p className="font-mono font-semibold">{invoice.id}</p>
                    </div>
                  </div>

                  <div className="border-t border-gray-200 pt-6 space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Date:</span>
                      <span className="font-medium">{invoice.date}</span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span className="text-gray-500">Amount:</span>
                      <span className="text-2xl font-bold text-blue-600">
                        ${invoice.amount.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6 animate-slide-in">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Detected Anomalies ({anomalies.length})
              </h2>
              <p className="text-gray-400">
                Review and resolve each anomaly to validate the invoice
              </p>
            </div>

            <div className="space-y-4">
              {anomalies.length === 0 ? (
                <div className="glass-panel rounded-xl p-8 text-center border border-green-500/20">
                  <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">All Anomalies Resolved!</h3>
                  <p className="text-gray-400 mb-6">
                    This invoice is ready for validation.
                  </p>
                  <button
                    onClick={handleMarkValid}
                    className="bg-green-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-600 transition-colors"
                  >
                    Mark Invoice as Valid
                  </button>
                </div>
              ) : (
                anomalies.map((anomaly) => (
                  <div key={anomaly.id} className="glass-panel rounded-xl p-4 border-l-4 border-red-400">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-white">{anomaly.description}</h4>
                      <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded">
                        {anomaly.priority} priority
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm mb-4">
                      {anomaly.details}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleResolveAnomaly(anomaly.id)}
                        className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-600 transition-colors flex-1"
                      >
                        Resolve
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Review;