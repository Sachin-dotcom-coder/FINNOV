import { useState } from 'react';
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

  const handleUploadComplete = (files) => {
    const newInvoices = files.map((file, index) => ({
      id: `INV-${Date.now()}-${index}`,
      fileName: file.name,
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
          <Route path="/" element={<Hero />} />
          <Route 
            path="/upload" 
            element={<Upload onUploadComplete={handleUploadComplete} />} 
          />
          <Route 
            path="/dashboard" 
            element={<Dashboard invoices={invoices} />} 
          />
          <Route 
            path="/review/:id" 
            element={
              <Review 
                invoices={invoices} 
                onUpdateInvoice={handleUpdateInvoice} 
              />
            } 
          />
          <Route path="/summary" element={<Summary />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;