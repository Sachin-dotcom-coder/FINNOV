import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Hero from './pages/Hero';
import Upload from './pages/Upload';
import Dashboard from './pages/Dashboard';
import Review from './pages/Review';
import Summary from './pages/Summary';

function App() {
  const [invoices, setInvoices] = useState([
    {
      id: 'INV-2023-0452',
      fileName: 'invoice_0452.pdf',
      vendor: 'Global Supplies Inc.',
      amount: 12450.00,
      date: '2023-10-15',
      status: 'pending',
      anomalies: [
        {
          id: 'anom-1',
          type: 'amount_mismatch',
          priority: 'high',
          description: 'Amount Mismatch',
          details: 'Invoice total doesn\'t match purchase order amount. Difference: $1,250.00',
          resolved: false
        }
      ],
      uploadedAt: new Date()
    }
  ]);

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Check if user was previously logged in
  useEffect(() => {
    const savedLogin = localStorage.getItem('isLoggedIn');
    if (savedLogin === 'true') {
      setIsLoggedIn(true);
    }
  }, []);

  const handleLogin = () => {
    setIsLoggedIn(true);
    localStorage.setItem('isLoggedIn', 'true');
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    localStorage.removeItem('isLoggedIn');
  };

  const handleUploadComplete = (files) => {
    const newInvoices = files.map((file, index) => ({
      id: `INV-${Date.now()}-${index}`,
      fileName: file.name,
      file: file, // Store the actual file object
      vendor: `Vendor ${index + 1}`,
      amount: Math.random() * 10000 + 1000,
      date: new Date().toISOString().split('T')[0],
      status: 'pending',
      anomalies: [
        {
          id: `anom-${Date.now()}-${index}-1`,
          type: 'amount_mismatch',
          priority: 'high',
          description: 'Amount Mismatch',
          details: 'Invoice total doesn\'t match purchase order amount',
          resolved: false
        },
        {
          id: `anom-${Date.now()}-${index}-2`,
          type: 'date_validation',
          priority: 'medium',
          description: 'Date Validation',
          details: 'Invoice date is more than 30 days old',
          resolved: false
        }
      ],
      uploadedAt: new Date(),
    }));

    setInvoices(prev => [...prev, ...newInvoices]);
  };

  const handleUpdateInvoice = (invoiceId, updates) => {
    setInvoices(prev => 
      prev.map(inv => 
        inv.id === invoiceId ? { ...inv, ...updates } : inv
      )
    );
  };

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <Routes>
          <Route 
            path="/" 
            element={
              <Hero 
                isLoggedIn={isLoggedIn}
                onLogin={handleLogin}
                onLogout={handleLogout}
              />
            } 
          />
          <Route 
            path="/upload" 
            element={
              isLoggedIn ? (
                <Upload 
                  onUploadComplete={handleUploadComplete}
                  isLoggedIn={isLoggedIn}
                  onLogout={handleLogout}
                />
              ) : (
                <div className="flex items-center justify-center min-h-screen">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-white mb-4">Please Sign In</h2>
                    <p className="text-gray-400">You need to be signed in to access the upload page.</p>
                  </div>
                </div>
              )
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              isLoggedIn ? (
                <Dashboard 
                  invoices={invoices}
                  isLoggedIn={isLoggedIn}
                  onLogout={handleLogout}
                />
              ) : (
                <div className="flex items-center justify-center min-h-screen">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-white mb-4">Please Sign In</h2>
                    <p className="text-gray-400">You need to be signed in to access the dashboard.</p>
                  </div>
                </div>
              )
            } 
          />
          <Route 
            path="/review/:id" 
            element={
              isLoggedIn ? (
                <Review 
                  invoices={invoices} 
                  onUpdateInvoice={handleUpdateInvoice}
                  isLoggedIn={isLoggedIn}
                  onLogout={handleLogout}
                />
              ) : (
                <div className="flex items-center justify-center min-h-screen">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-white mb-4">Please Sign In</h2>
                    <p className="text-gray-400">You need to be signed in to access the review page.</p>
                  </div>
                </div>
              )
            } 
          />
          <Route 
            path="/summary" 
            element={
              isLoggedIn ? (
                <Summary 
                  isLoggedIn={isLoggedIn}
                  onLogout={handleLogout}
                />
              ) : (
                <div className="flex items-center justify-center min-h-screen">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-white mb-4">Please Sign In</h2>
                    <p className="text-gray-400">You need to be signed in to access the summary page.</p>
                  </div>
                </div>
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;