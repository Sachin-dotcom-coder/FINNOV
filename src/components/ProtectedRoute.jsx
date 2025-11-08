// src/components/ProtectedRoute.jsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const ProtectedRoute = ({ children }) => {
  const navigate = useNavigate();
  
  useEffect(() => {
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    if (!isLoggedIn) {
      navigate('/');
    }
  }, [navigate]);

  const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
  
  return isLoggedIn ? children : null;
};

export default ProtectedRoute;