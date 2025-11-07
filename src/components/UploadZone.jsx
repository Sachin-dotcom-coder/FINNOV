import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { Upload, CheckCircle2, Loader } from 'lucide-react';

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
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 200);

    // Simulate AI processing
    setTimeout(() => {
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setTimeout(() => {
        onUploadComplete(acceptedFiles);
        navigate('/dashboard');
      }, 1000);
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
    <div className="w-full max-w-4xl mx-auto">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-300 backdrop-blur-sm
          ${isDragActive 
            ? 'border-primary bg-primary/10 glow-primary' 
            : 'border-border hover:border-primary/50 hover:bg-card/30'
          }
          ${isUploading ? 'pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        {isUploading ? (
          <div className="space-y-6">
            <div className="flex justify-center">
              <div className="relative">
                <Loader className="h-16 w-16 text-primary animate-spin" />
                <CheckCircle2 
                  className={`h-16 w-16 text-primary absolute inset-0 transition-opacity duration-300 ${
                    uploadProgress === 100 ? 'opacity-100' : 'opacity-0'
                  }`}
                />
              </div>
            </div>
            
            <div className="space-y-4">
              <h3 className="text-xl font-semibold">
                {uploadProgress < 100 ? 'Analyzing with AI...' : 'Analysis Complete!'}
              </h3>
              
              <div className="w-full bg-muted rounded-full h-3">
                <div 
                  className="bg-gradient-to-r from-primary to-accent h-3 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              
              <p className="text-muted-foreground">
                {uploadProgress < 100 
                  ? 'Extracting data and detecting anomalies...' 
                  : 'Redirecting to dashboard...'
                }
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex justify-center">
              <div className="p-4 rounded-full bg-primary/10">
                {isDragActive ? (
                  <CheckCircle2 className="h-12 w-12 text-primary" />
                ) : (
                  <Upload className="h-12 w-12 text-primary" />
                )}
              </div>
            </div>
            
            <div className="space-y-3">
              <h3 className="text-2xl font-semibold">
                {isDragActive ? 'Drop files here' : 'Upload Your Invoices'}
              </h3>
              <p className="text-muted-foreground text-lg">
                Drag & drop files or click to browse
              </p>
              <p className="text-sm text-muted-foreground">
                Supported formats: PDF, JPG, PNG, TIFF
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadZone;