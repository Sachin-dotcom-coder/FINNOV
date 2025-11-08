import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { ArrowLeft, ZoomIn, ZoomOut, Download, CheckCircle, XCircle, AlertTriangle, FileText, Image, File } from 'lucide-react';
import { API_URL, updateAnomaly } from '../api/client';

const Review = ({ invoices, onUpdateInvoice, isLoggedIn, onLogout }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [documentUrl, setDocumentUrl] = useState(null);

  useEffect(() => {
    const foundInvoice = invoices.find(inv => inv.id === id);
    if (foundInvoice) {
      setInvoice(foundInvoice);
      if (foundInvoice.anomalies.length > 0) {
        setSelectedAnomaly(foundInvoice.anomalies[0]);
      }
      
      // Prefer local File for preview, fall back to server URL
      if (foundInvoice.file) {
        const url = URL.createObjectURL(foundInvoice.file);
        setDocumentUrl(url);
      } else if (foundInvoice.fileUrl) {
        const url = foundInvoice.fileUrl.startsWith('http') ? foundInvoice.fileUrl : `${API_URL}${foundInvoice.fileUrl}`;
        setDocumentUrl(url);
      }
    }
  }, [id, invoices]);

  // Clean up object URL
  useEffect(() => {
    return () => {
      if (documentUrl) {
        URL.revokeObjectURL(documentUrl);
      }
    };
  }, [documentUrl]);

  const handleResolveAnomaly = async (anomalyId) => {
    if (!invoice) return;

    // Optimistic update
    const optimistic = {
      ...invoice,
      anomalies: invoice.anomalies.map(a => a.id === anomalyId ? { ...a, resolved: true } : a),
    };
    optimistic.status = optimistic.anomalies.every(a => a.resolved) ? 'verified' : 'pending';
    setInvoice(optimistic);
    onUpdateInvoice(invoice.id, optimistic);

    try {
      const { invoice: saved } = await updateAnomaly(invoice.id, anomalyId, true);
      setInvoice(saved);
      onUpdateInvoice(invoice.id, saved);
    } catch (e) {
      alert('Failed to update anomaly. Reverting.');
      setInvoice(invoice);
      onUpdateInvoice(invoice.id, invoice);
    }
  };

  const handleReopenAnomaly = async (anomalyId) => {
    if (!invoice) return;

    const optimistic = {
      ...invoice,
      anomalies: invoice.anomalies.map(a => a.id === anomalyId ? { ...a, resolved: false } : a),
      status: 'pending'
    };
    setInvoice(optimistic);
    onUpdateInvoice(invoice.id, optimistic);

    try {
      const { invoice: saved } = await updateAnomaly(invoice.id, anomalyId, false);
      setInvoice(saved);
      onUpdateInvoice(invoice.id, saved);
    } catch (e) {
      alert('Failed to update anomaly. Reverting.');
      setInvoice(invoice);
      onUpdateInvoice(invoice.id, invoice);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      case 'low': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
    }
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'high': return <AlertTriangle className="h-4 w-4" />;
      case 'medium': return <AlertTriangle className="h-4 w-4" />;
      case 'low': return <AlertTriangle className="h-4 w-4" />;
      default: return <AlertTriangle className="h-4 w-4" />;
    }
  };

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (!isFullscreen) {
      setZoomLevel(1.5);
    } else {
      setZoomLevel(1);
    }
  };

  const handleDownload = () => {
    if (!invoice) return;
    const url = invoice.id ? `${API_URL}/api/invoices/${invoice.id}/download` : documentUrl;
    if (!url) return;
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase();
    if (['pdf'].includes(extension)) {
      return <FileText className="h-8 w-8 text-red-400" />;
    } else if (['jpg', 'jpeg', 'png', 'tiff'].includes(extension)) {
      return <Image className="h-8 w-8 text-green-400" />;
    } else {
      return <File className="h-8 w-8 text-blue-400" />;
    }
  };

  const renderDocumentPreview = () => {
    if (!invoice || !documentUrl) {
      return (
        <div className="flex flex-col items-center justify-center p-8 min-h-[500px] text-gray-400">
          <File className="h-16 w-16 mb-4" />
          <p>No document available for preview</p>
        </div>
      );
    }

    const extension = invoice.fileName.split('.').pop().toLowerCase();
    
    if (extension === 'pdf') {
      return (
        <div className="w-full h-full">
          <iframe
            src={documentUrl}
            className="w-full h-full min-h-[500px] border-0"
            title={invoice.fileName}
            style={{ transform: `scale(${zoomLevel})`, transformOrigin: '0 0' }}
          />
        </div>
      );
    } else if (['jpg', 'jpeg', 'png', 'tiff'].includes(extension)) {
      return (
        <div className="flex items-center justify-center p-8 min-h-[500px]">
          <img
            src={documentUrl}
            alt={invoice.fileName}
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
            style={{ 
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'center center'
            }}
          />
        </div>
      );
    } else {
      return (
        <div className="flex flex-col items-center justify-center p-8 min-h-[500px] text-gray-400">
          {getFileIcon(invoice.fileName)}
          <p className="mt-4 text-lg">Preview not available for this file type</p>
          <p className="text-sm">File: {invoice.fileName}</p>
        </div>
      );
    }
  };

  if (!invoice) {
    return (
      <div className="min-h-screen gradient-dark">
        <Header isLoggedIn={isLoggedIn} onLogout={onLogout} />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white mb-4">Invoice Not Found</h2>
            <button
              onClick={() => navigate('/dashboard')}
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-dark">
      <Header isLoggedIn={isLoggedIn} onLogout={onLogout} />
      
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </button>
            <div>
              <h1 className="text-3xl font-bold text-white">Invoice Review</h1>
              <div className="flex items-center gap-2 text-gray-400">
                {getFileIcon(invoice.fileName)}
                <span>{invoice.fileName}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${
              invoice.status === 'verified' 
                ? 'text-green-400 bg-green-400/10 border-green-400/20'
                : 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20'
            }`}>
              {invoice.status === 'verified' ? 'Verified' : 'Under Review'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Document Viewer */}
          <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">Document Preview</h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleZoomOut}
                    disabled={zoomLevel <= 0.5}
                    className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ZoomOut className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-400 min-w-12 text-center">
                    {Math.round(zoomLevel * 100)}%
                  </span>
                  <button
                    onClick={handleZoomIn}
                    disabled={zoomLevel >= 3}
                    className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ZoomIn className="h-4 w-4" />
                  </button>
                  <button
                    onClick={handleResetZoom}
                    className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors text-sm"
                  >
                    Reset
                  </button>
                  <button
                    onClick={toggleFullscreen}
                    className="p-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
                  >
                    {isFullscreen ? 'Exit' : 'Fullscreen'}
                  </button>
                </div>
              </div>

              {/* Document Display Area */}
              <div 
                className={`border-2 border-dashed border-gray-600 rounded-xl bg-gray-900/50 overflow-hidden transition-all duration-300 ${
                  isFullscreen ? 'fixed inset-4 z-50 bg-slate-900' : 'relative'
                }`}
              >
                {renderDocumentPreview()}

                {/* Fullscreen overlay */}
                {isFullscreen && (
                  <div className="absolute top-4 right-4">
                    <button
                      onClick={toggleFullscreen}
                      className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                    >
                      <XCircle className="h-6 w-6" />
                    </button>
                  </div>
                )}
              </div>

              {/* Download Button */}
              <div className="flex justify-center mt-4">
                <button 
                  onClick={handleDownload}
                  className="flex items-center gap-2 px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  Download Document
                </button>
              </div>
            </div>
          </div>

          {/* Right Column - Anomalies List */}
          <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Detected Anomalies</h2>
              
              <div className="space-y-4">
                {invoice.anomalies.map((anomaly) => (
                  <div
                    key={anomaly.id}
                    className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      selectedAnomaly?.id === anomaly.id
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-gray-600 bg-slate-800/50 hover:border-gray-500'
                    } ${anomaly.resolved ? 'opacity-60' : ''}`}
                    onClick={() => setSelectedAnomaly(anomaly)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg border ${getPriorityColor(anomaly.priority)}`}>
                          {getPriorityIcon(anomaly.priority)}
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{anomaly.description}</h3>
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            anomaly.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                            anomaly.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-blue-500/20 text-blue-400'
                          }`}>
                            {anomaly.priority} priority
                          </span>
                        </div>
                      </div>
                      
                      {anomaly.resolved ? (
                        <div className="flex items-center gap-2 text-green-400">
                          <CheckCircle className="h-4 w-4" />
                          <span className="text-sm">Resolved</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-yellow-400">
                          <AlertTriangle className="h-4 w-4" />
                          <span className="text-sm">Pending</span>
                        </div>
                      )}
                    </div>
                    
                    <p className="text-gray-400 text-sm mb-3">{anomaly.details}</p>
                    
                    {!anomaly.resolved ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResolveAnomaly(anomaly.id);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm"
                      >
                        <CheckCircle className="h-4 w-4" />
                        Mark as Resolved
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReopenAnomaly(anomaly.id);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors text-sm"
                      >
                        <AlertTriangle className="h-4 w-4" />
                        Reopen Issue
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {invoice.anomalies.length === 0 && (
                <div className="text-center py-8">
                  <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">No Anomalies Detected</h3>
                  <p className="text-gray-400">This invoice has been verified and is ready for processing.</p>
                </div>
              )}
            </div>

            {/* Invoice Summary */}
            <div className="glass-panel rounded-2xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Invoice Summary</h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Vendor</span>
                  <span className="text-white font-medium">{invoice.vendor}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Invoice Date</span>
                  <span className="text-white">{invoice.date}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Amount</span>
                  <span className="text-white font-semibold text-lg">
                    ${invoice.amount.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Status</span>
                  <span className={`font-semibold ${
                    invoice.status === 'verified' ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {invoice.status === 'verified' ? 'Verified' : 'Under Review'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Anomalies Found</span>
                  <span className="text-white">
                    {invoice.anomalies.filter(a => !a.resolved).length} / {invoice.anomalies.length}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Review;