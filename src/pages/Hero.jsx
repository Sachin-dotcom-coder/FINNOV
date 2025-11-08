import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import NumbersBackground from '../components/NumbersBackground';
import { FileText, ArrowRight, Sparkles } from 'lucide-react';

const Hero = ({ isLoggedIn, onLogin, onLogout }) => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen gradient-dark relative overflow-hidden flex flex-col">
      {/* NumbersBackground - Full width and height with forced stretching */}
      <div className="fixed inset-0 z-0 w-screen h-screen">
        <NumbersBackground />
      </div>
      
      <div className="relative z-10 flex-1 flex flex-col">
        <Header 
          isLoggedIn={isLoggedIn}
          onLogin={onLogin}
          onLogout={onLogout}
        />
        
        {/* Hero Content */}
        <div className="flex-1 flex items-center justify-center py-8">
          <div className="container mx-auto px-6">
            <div className="max-w-4xl mx-auto text-center space-y-12">
              <div className="space-y-8 animate-fade-in">
                {/* Animated Badge with Bounce */}
                <div className="inline-flex items-center gap-3 px-6 py-3 rounded-2xl glass-panel mb-8 animate-bounce glow-accent border border-cyan-400/30">
                  <Sparkles className="h-5 w-5 text-cyan-400" />
                  <span className="text-cyan-400 font-semibold text-sm">Powered by Advanced AI</span>
                </div>

                {/* Main Heading */}
                <div className="space-y-6 -mt-6">
                  <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
                    Smarter Finance{' '}
                    <span className="bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
                      Starts Here
                    </span>
                  </h1>

                  <p className="text-xl md:text-2xl text-gray-300 max-w-2xl mx-auto leading-relaxed">
                    Automating invoice understanding for modern enterprises.
                  </p>
                </div>

                {/* CTA Buttons */}
                <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
                  <button
                    onClick={() => navigate('/upload')}
                    className="glass-panel bg-gradient-to-r from-blue-400 to-green-400 text-white px-12 py-6 rounded-2xl font-bold text-lg hover:scale-105 transition-all duration-300 glow-gradient flex items-center gap-3 group border border-blue-400/30 backdrop-blur-sm relative overflow-hidden"
                  >
                    {/* Glass overlay */}
                    <div className="absolute inset-0 bg-white/10 backdrop-blur-sm rounded-2xl"></div>
                    <div className="relative z-10 flex items-center gap-3">
                      <FileText className="h-6 w-6" />
                      Upload Your Invoices
                      <ArrowRight className="h-5 w-5 group-hover:translate-x-2 transition-transform duration-300" />
                    </div>
                  </button>
                  
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="glass-panel border border-white/20 text-white px-12 py-6 rounded-2xl font-bold text-lg hover:scale-105 transition-all duration-300 hover:glow-primary"
                  >
                    See How It Works
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 glass-panel border-t border-white/10 py-6">
        <div className="container mx-auto px-6">
          <div className="text-center">
            <p className="text-gray-400 text-base">
              Built to empower next-generation industries — inspired by the{' '}
              <span className="text-blue-400 font-semibold">Adani Group's</span> commitment to innovation.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Hero;