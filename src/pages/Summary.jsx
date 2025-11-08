import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { CheckCircle2 } from 'lucide-react';

const Summary = () => {
  const navigate = useNavigate();
  const [invoiceCount, setInvoiceCount] = useState(0);
  const [anomalyCount, setAnomalyCount] = useState(0);

  useEffect(() => {
    const invoiceTarget = 15;
    const anomalyTarget = 8;
    
    const duration = 2000;
    const steps = 50;
    const invoiceIncrement = invoiceTarget / steps;
    const anomalyIncrement = anomalyTarget / steps;

    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep++;
      setInvoiceCount(Math.min(Math.floor(invoiceIncrement * currentStep), invoiceTarget));
      setAnomalyCount(Math.min(Math.floor(anomalyIncrement * currentStep), anomalyTarget));

      if (currentStep >= steps) {
        clearInterval(interval);
      }
    }, duration / steps);
  }, []);

  return (
    <div className="min-h-screen gradient-dark">
      <Header />
      <main className="flex items-center justify-center min-h-[calc(100vh-80px)]"> {/* Proper centering */}
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mx-auto text-center space-y-8">
            <div className="animate-fade-in">
              <CheckCircle2 className="h-20 w-20 text-green-400 mx-auto mb-6" />
              <h1 className="text-4xl font-bold text-white mb-4">Validation Complete</h1>
              <p className="text-gray-400 text-lg">
                All invoices have been successfully reviewed and validated.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6 animate-slide-in">
              <div className="glass-panel rounded-xl p-6">
                <div className="text-3xl font-bold text-blue-400 mb-2">{invoiceCount}</div>
                <div className="text-gray-400">Invoices Processed</div>
              </div>

              <div className="glass-panel rounded-xl p-6">
                <div className="text-3xl font-bold text-green-400 mb-2">{anomalyCount}</div>
                <div className="text-gray-400">Anomalies Resolved</div>
              </div>
            </div>

            <div className="flex gap-4 justify-center animate-fade-in">
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-blue-500 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-600 transition-colors"
              >
                Return to Dashboard
              </button>
              
              <button
                onClick={() => navigate('/upload')}
                className="glass-panel border border-gray-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-white/5 transition-colors"
              >
                Upload More Invoices
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Summary;