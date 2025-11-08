import { useEffect, useState } from "react";

const NumbersBackground = () => {
  const [columns, setColumns] = useState([]);

  useEffect(() => {
    const generateColumn = () => {
      const numbers = [];
      for (let i = 0; i < 30; i++) {
        numbers.push(Math.random().toString().slice(2, 8));
      }
      return numbers;
    };

    const cols = Array.from({ length: 30 }, generateColumn);
    setColumns(cols);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none opacity-10 z-0">
      <div className="flex gap-8 h-[200vh]">
        {columns.map((column, colIndex) => (
          <div
            key={colIndex}
            className="flex flex-col gap-4 text-xs font-mono text-blue-400 animate-number-scroll"
            style={{
              animationDelay: `${colIndex * 0.5}s`,
              animationDuration: `${20 + colIndex * 2}s`,
            }}
          >
            {column.map((num, numIndex) => (
              <div key={numIndex} className="whitespace-nowrap opacity-70">
                {num}
              </div>
            ))}
            {column.map((num, numIndex) => (
              <div key={`repeat-${numIndex}`} className="whitespace-nowrap opacity-70">
                {num}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NumbersBackground;