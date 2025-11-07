import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { Upload as UploadIcon, Loader, CheckCircle2, Cloud, FileText } from 'lucide-react';

const UploadZone = ({ onUploadComplete }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 10;
      });
    }, 200);

    // Simulate AI processing
    setTimeout(() => {
      clearInterval(progressInterval);
      onUploadComplete(acceptedFiles);
      navigate('/dashboard');
    }, 2500);
  }, [onUploadComplete, navigate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png', '.tiff']
    },
    multiple: true
  });

  return (
    <div className="w-full max-w-4xl mx-auto animate-float">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300
          glass-panel hover-lift hover-glow
          ${isDragActive 
            ? 'border-blue-400 bg-blue-500/10 animate-glow' 
            : 'border-gray-600 hover:border-blue-400'
          }
          ${isUploading ? 'pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        {isUploading ? (
          <div className="space-y-6">
            <div className="relative">
              <Loader className="h-16 w-16 text-blue-400 animate-spin mx-auto" />
              <CheckCircle2 
                className={`h-16 w-16 text-green-400 absolute inset-0 mx-auto transition-all duration-500 ${
                  uploadProgress === 100 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'
                }`}
              />
            </div>
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-white animate-pulse">
                {uploadProgress < 100 ? 'Analyzing with AI...' : 'Analysis Complete!'}
              </h3>
              <div className="w-full bg-gray-600 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-blue-400 to-green-400 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-400">
                <span>Uploading...</span>
                <span className="font-mono">{uploadProgress}%</span>
              </div>
              <p className="text-gray-400">
                {uploadProgress < 100 
                  ? 'Extracting data and detecting anomalies...' 
                  : 'Redirecting to dashboard...'
                }
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="relative">
              <div className={`p-6 rounded-2xl bg-blue-500/10 mx-auto w-24 h-24 flex items-center justify-center transition-all duration-500 ${
                isDragActive ? 'scale-110 rotate-12' : ''
              }`}>
                {isDragActive ? (
                  <Cloud className="h-12 w-12 text-blue-400 animate-bounce" />
                ) : (
                  <UploadIcon className="h-12 w-12 text-blue-400 transition-transform duration-300 hover:scale-110" />
                )}
              </div>
              {isDragActive && (
                <div className="absolute -top-2 -right-2">
                  <div className="w-6 h-6 bg-green-400 rounded-full animate-ping"></div>
                </div>
              )}
            </div>
            
            <div className="space-y-4">
              <h3 className="text-2xl font-semibold text-white transition-all duration-300">
                {isDragActive ? (
                  <span className="text-green-400 animate-pulse">Release to upload</span>
                ) : (
                  'Upload Your Invoices'
                )}
              </h3>
              <p className="text-gray-400 text-lg">
                {isDragActive ? 'Drop your files here' : 'Drag & drop files or click to browse'}
              </p>
              <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span>PDF</span>
                </div>
                <div className="w-1 h-1 bg-gray-500 rounded-full"></div>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span>Images</span>
                </div>
              </div>
            </div>

            {!isDragActive && (
              <button className="bg-blue-500 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-600 transition-all duration-300 hover-lift hover-glow inline-flex items-center gap-2">
                <UploadIcon className="h-4 w-4" />
                Browse Files
              </button>
            )}
          </div>
        )}
      </div>

      {/* File type info cards */}
      {!isUploading && !isDragActive && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <div className="glass-panel rounded-lg p-4 text-center transition-all duration-300 hover-lift">
            <FileText className="h-8 w-8 text-blue-400 mx-auto mb-2" />
            <h4 className="text-white font-medium text-sm">PDF Documents</h4>
            <p className="text-gray-400 text-xs">Scanned or digital invoices</p>
          </div>
          <div className="glass-panel rounded-lg p-4 text-center transition-all duration-300 hover-lift">
            <FileText className="h-8 w-8 text-green-400 mx-auto mb-2" />
            <h4 className="text-white font-medium text-sm">JPEG/PNG Images</h4>
            <p className="text-gray-400 text-xs">Photo of paper invoices</p>
          </div>
          <div className="glass-panel rounded-lg p-4 text-center transition-all duration-300 hover-lift">
            <FileText className="h-8 w-8 text-purple-400 mx-auto mb-2" />
            <h4 className="text-white font-medium text-sm">TIFF Files</h4>
            <p className="text-gray-400 text-xs">High-quality scans</p>
          </div>
        </div>
      )}
    </div>
  );
};

const Upload = ({ onUploadComplete }) => {
  return (
    <div className="min-h-screen gradient-dark">
      <Header />
      <main className="flex items-center justify-center min-h-[calc(100vh-80px)]">
        <div className="container mx-auto px-6 py-8">
          <div className="max-w-6xl mx-auto space-y-8">
            <div className="text-center space-y-4 animate-fade-in">
              <h1 className="text-4xl md:text-5xl font-bold text-white">
                AI-Powered{' '}
                <span className="bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
                  Invoice Analysis
                </span>
              </h1>
              <p className="text-lg text-gray-400 max-w-2xl mx-auto">
                Upload your invoices and let our advanced AI detect anomalies, validate data, and streamline your financial workflows.
              </p>
            </div>

            <UploadZone onUploadComplete={onUploadComplete} />

            {/* Features section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <div className="glass-panel rounded-xl p-6 text-center transition-all duration-300 hover-lift animate-fade-in stagger-1">
                <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <FileText className="h-6 w-6 text-blue-400" />
                </div>
                <h3 className="text-white font-semibold mb-2">Smart Extraction</h3>
                <p className="text-gray-400 text-sm">
                  Automatically extract key data from any invoice format
                </p>
              </div>
              
              <div className="glass-panel rounded-xl p-6 text-center transition-all duration-300 hover-lift animate-fade-in stagger-2">
                <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="h-6 w-6 text-green-400" />
                </div>
                <h3 className="text-white font-semibold mb-2">Anomaly Detection</h3>
                <p className="text-gray-400 text-sm">
                  AI-powered detection of discrepancies and errors
                </p>
              </div>
              
              <div className="glass-panel rounded-xl p-6 text-center transition-all duration-300 hover-lift animate-fade-in stagger-3">
                <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Cloud className="h-6 w-6 text-purple-400" />
                </div>
                <h3 className="text-white font-semibold mb-2">Secure Processing</h3>
                <p className="text-gray-400 text-sm">
                  Enterprise-grade security for your financial data
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Upload;