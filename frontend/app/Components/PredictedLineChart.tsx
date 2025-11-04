// app/Components/PredictedLineChart.tsx
"use client";
import { useMemo } from "react";

export default function PredictedLineChart({
  labels, values, className,
}: { labels: string[]; values: number[]; className?: string }) {
  const width = 800, height = 260, pad = { t:20, r:20, b:32, l:40 };
  
  const { maxY, points, xTicks, areaPoints } = useMemo(() => {
    const n = Math.max(values.length, 1);
    const maxY = Math.max(10, ...values);
    const xStep = (width - pad.l - pad.r) / Math.max(n - 1, 1);
    const yScale = (v:number) => height - pad.b - (v/maxY)*(height - pad.t - pad.b);
    const xScale = (i:number) => pad.l + i*xStep;
    
    const points = values.map((v,i) => `${xScale(i)},${yScale(v)}`).join(" ");
    const areaPoints = `${points} ${xScale(values.length-1)},${height-pad.b} ${pad.l},${height-pad.b}`;
    const xTicks = labels.map((lab,i) => ({ x: xScale(i), label: lab }));
    
    return { maxY, points, xTicks, areaPoints };
  }, [labels, values]);

  return (
    <div className={`w-full overflow-hidden ${className ?? ""}`}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[320px]">
        {/* Background Grid */}
        <defs>
          <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#2F3590" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#2F3590" stopOpacity="0.1" />
          </linearGradient>
        </defs>
        
        {/* Grid Lines */}
        {Array.from({length:5}).map((_,i)=>{
          const y = pad.t + i*((height-pad.t-pad.b)/4);
          return (
            <g key={i}>
              <line x1={pad.l} x2={width-pad.r} y1={y} y2={y} stroke="#E6E9F9" strokeWidth="1" strokeOpacity="0.3"/>
              <text x={pad.l-8} y={y+3} textAnchor="end" fill="#E6E9F9" fontSize="10" fontFamily="Inter" opacity="0.7">
                {Math.round(maxY*(1-i/4))}
              </text>
            </g>
          );
        })}

        {/* Area Fill */}
        <polygon fill="url(#areaGradient)" points={areaPoints} />
        
        {/* Main Line */}
        <polyline fill="none" stroke="#FDF036" strokeWidth="3" points={points} strokeLinecap="round" strokeLinejoin="round"/>
        
        {/* Data Points */}
        {values.map((v,i)=>{
          const x = xTicks[i].x;
          const y = height - pad.b - (v/Math.max(maxY,1))*(height-pad.t-pad.b);
          return (
            <g key={i}>
              <circle cx={x} cy={y} r="4" fill="#FDF036" stroke="#040354" strokeWidth="2"/>
              <circle cx={x} cy={y} r="6" fill="#FDF036" fillOpacity="0.2"/>
            </g>
          );
        })}

        {/* X-axis Labels */}
        {xTicks.map((t,i) => (
          <text 
            key={i} 
            x={t.x} 
            y={height-8} 
            textAnchor="middle" 
            fill="#E6E9F9" 
            fontSize="11" 
            fontFamily="Inter"
            fontWeight="500"
          >
            {t.label}
          </text>
        ))}

        {/* Axes */}
        <line x1={pad.l} y1={height-pad.b} x2={width-pad.r} y2={height-pad.b} stroke="#E6E9F9" strokeWidth="2" strokeOpacity="0.5"/>
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={height-pad.b} stroke="#E6E9F9" strokeWidth="2" strokeOpacity="0.5"/>
      </svg>
    </div>
  );
}