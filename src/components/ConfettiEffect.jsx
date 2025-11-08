import { useEffect, useState } from 'react';

const ConfettiEffect = () => {
  const [confettiPieces, setConfettiPieces] = useState([]);

  useEffect(() => {
    const colors = ['#0a84ff', '#00d4aa', '#8a2be2', '#ff4757', '#ffa502', '#2ed573'];
    const pieces = [];

    for (let i = 0; i < 100; i++) {
      pieces.push({
        id: i,
        color: colors[Math.floor(Math.random() * colors.length)],
        left: Math.random() * 100,
        animationDelay: Math.random() * 3,
        size: Math.random() * 10 + 5
      });
    }

    setConfettiPieces(pieces);

    const timer = setTimeout(() => {
      setConfettiPieces([]);
    }, 4000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {confettiPieces.map((piece) => (
        <div
          key={piece.id}
          className="absolute rounded-sm"
          style={{
            backgroundColor: piece.color,
            left: `${piece.left}%`,
            top: '-20px',
            width: `${piece.size}px`,
            height: `${piece.size}px`,
            animation: `confettiFall 3s ease-out ${piece.animationDelay}s forwards`
          }}
        />
      ))}
    </div>
  );
};

export default ConfettiEffect;