// app/Components/PredictedLineChart.tsx
"use client";
import { useMemo } from "react";
export default function PredictedLineChart({
  labels, values, className,
}: { labels: string[]; values: number[]; className?: string }) {
  const width = 800, height = 260, pad = { t:16, r:16, b:28, l:36 };
  const { maxY, points, xTicks } = useMemo(() => {
    const n = Math.max(values.length, 1);
    const maxY = Math.max(10, ...values);
    const xStep = (width - pad.l - pad.r) / Math.max(n - 1, 1);
    const yScale = (v:number)=>height - pad.b - (v/maxY)*(height - pad.t - pad.b);
    const xScale = (i:number)=> pad.l + i*xStep;
    const points = values.map((v,i)=>`${xScale(i)},${yScale(v)}`).join(" ");
    const xTicks = labels.map((lab,i)=>({ x: xScale(i), label: lab }));
    return { maxY, points, xTicks };
  }, [labels, values]);

  return (
    <div className={`w-full overflow-hidden rounded-2xl bg-white shadow-sm border border-addu-mist ${className ?? ""}`}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[320px]">
        <rect x="0" y="0" width={width} height={height} fill="white" />
        {Array.from({length:5}).map((_,i)=>{
          const y = 16 + i*((height-16-28)/4);
          return <line key={i} x1={36} x2={width-16} y1={y} y2={y} stroke="#E6E9F9" strokeWidth="1"/>;
        })}
        <line x1={36} y1={height-28} x2={width-16} y2={height-28} stroke="#0A0F3D" strokeWidth="1"/>
        <line x1={36} y1={16} x2={36} y2={height-28} stroke="#0A0F3D" strokeWidth="1"/>

        <polyline fill="none" stroke="#2F3590" strokeWidth="3" points={points}/>
        {values.map((v,i)=>{
          const x = xTicks[i].x;
          const y = height - 28 - (v/Math.max(maxY,1))*(height-16-28);
          return <circle key={i} cx={x} cy={y} r="3" fill="#1611B1"/>;
        })}

        {xTicks.map((t,i)=> i%2===0 ? (
          <text key={i} x={t.x} y={height-8} textAnchor="middle" fill="#0A0F3D" fontSize="10" fontFamily="Inter">
            {t.label}
          </text>
        ) : null)}

        {[0,0.25,0.5,0.75,1].map((p,i)=>{
          const y = 16 + (1-p)*(height-16-28);
          const v = Math.round(maxY*p);
          return <text key={i} x={30} y={y+3} textAnchor="end" fill="#0A0F3D" fontSize="10" fontFamily="Inter">{v}</text>;
        })}
      </svg>
    </div>
  );
}
