// app/Components/BestTimesCard.tsx
function compressRanges(values: number[], labels: string[], threshold: number) {
  const out: { start: string; end: string }[] = [];
  let s = -1;
  for (let i = 0; i < values.length; i++) {
    const ok = values[i] <= threshold;
    if (ok && s === -1) s = i;
    if ((!ok || i === values.length - 1) && s !== -1) {
      const e = ok && i === values.length - 1 ? i : i - 1;
      out.push({ start: labels[s], end: labels[e] });
      s = -1;
    }
  }
  return out;
}

export default function BestTimesCard({
  labels, predicted, hours24
}: { labels: string[]; predicted: number[]; hours24: number[] }) {

  const OPEN_START = 8;
  const OPEN_END   = 22;
  const inOpen = hours24.map(h => h >= OPEN_START && h <= OPEN_END);

  const openLabels: string[] = [];
  const openValues: number[] = [];
  for (let i = 0; i < predicted.length; i++) {
    if (inOpen[i]) {
      openLabels.push(labels[i]);
      openValues.push(predicted[i]);
    }
  }

  const peak = Math.max(1, ...openValues);
  const cutoff = Math.round(peak * 0.3);
  const ranges = compressRanges(openValues, openLabels, cutoff).slice(0, 3);

  return (
    <div className="group relative">
      <div className="absolute inset-0 bg-gradient-to-r from-addu-gold to-addu-amber rounded-2xl blur-sm opacity-20 group-hover:opacity-30 transition-opacity" />
      
      <div className="relative rounded-2xl p-6 bg-gradient-to-br from-addu-navy to-addu-ink border border-addu-royal/30 shadow-xl hover:shadow-2xl transition-all duration-300">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-2 h-8 bg-gradient-to-b from-addu-gold to-addu-amber rounded-full" />
          <h2 className="font-open-sans text-white text-lg font-semibold">Best times to visit</h2>
        </div>
        
        {ranges.length === 0 ? (
          <div className="text-center py-6">
            <div className="text-addu-mist text-sm opacity-70">No low-crowd windows within open hours.</div>
          </div>
        ) : (
          <ul className="space-y-3">
            {ranges.map((r, i) => (
              <li key={i} className="flex items-center justify-between p-3 bg-addu-royal/20 rounded-xl border border-addu-royal/30 hover:bg-addu-royal/30 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-addu-gold animate-pulse" />
                  <span className="text-white font-medium">{r.start} – {r.end}</span>
                </div>
                <span className="text-addu-amber text-sm font-medium px-2 py-1 bg-addu-ink/50 rounded-lg">
                  ≤ {cutoff} ppl
                </span>
              </li>
            ))}
          </ul>
        )}
        
        <div className="text-xs text-addu-mist opacity-60 mt-4 pt-3 border-t border-addu-royal/20">
          Based on predicted occupancy ≤ 30% of peak, limited to 8 AM–10 PM.
        </div>
      </div>
    </div>
  );
}