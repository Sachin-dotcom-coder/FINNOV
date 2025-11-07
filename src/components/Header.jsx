import { Link, useLocation } from 'react-router-dom';
import { FileText } from 'lucide-react';

const Header = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <header className="glass-panel border-b border-white/10 sticky top-0 z-50">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <FileText className="h-7 w-7 text-blue-400" /> {/* Increased icon size */}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">InvoiceAI</h1> {/* Increased from text-xl to text-2xl */}
              <p className="text-sm text-gray-400">AI-Powered Intelligence Platform</p> {/* Increased from text-xs to text-sm */}
            </div>
          </Link>

          <nav className="flex items-center gap-8">
            <Link
              to="/"
              className={`text-base font-medium transition-colors ${
                isActive('/') ? 'text-blue-400' : 'text-gray-400 hover:text-white'
              }`}
            >
              Home
            </Link>
            <Link
              to="/upload"
              className={`text-base font-medium transition-colors ${
                isActive('/upload') ? 'text-blue-400' : 'text-gray-400 hover:text-white'
              }`}
            >
              Upload
            </Link>
            <Link
              to="/dashboard"
              className={`text-base font-medium transition-colors ${
                isActive('/dashboard') ? 'text-blue-400' : 'text-gray-400 hover:text-white'
              }`}
            >
              Dashboard
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            <button className="text-base font-medium text-gray-400 hover:text-white transition-colors">
              Log In
            </button>
            <button className="bg-blue-500 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-600 transition-colors">
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;