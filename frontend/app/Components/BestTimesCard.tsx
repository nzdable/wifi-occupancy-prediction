function compressRanges(values: number[], labels: string[], threshold: number) {
  // contiguous ranges where value <= threshold
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

    // Keep only the indices within open hours
    const openLabels: string[] = [];
    const openValues: number[] = [];
    for (let i = 0; i < predicted.length; i++) {
      if (inOpen[i]) {
        openLabels.push(labels[i]);
        openValues.push(predicted[i]);
      }
    }

  const peak = Math.max(1, ...openValues);
  const cutoff = Math.round(peak * 0.3); // <= 30% of peak is “low”
  const ranges = compressRanges(openValues, openLabels, cutoff).slice(0, 3);

  return (
    <div className="rounded-2xl p-4 bg-white border border-addu-mist shadow-sm">
      <h2 className="font-open-sans text-addu-ink mb-2">Best times to visit</h2>
      {ranges.length === 0 ? (
        <p className="text-sm opacity-70">No low-crowd windows within open hours.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {ranges.map((r, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-addu-gold" />
              <span className="text-addu-ink">{r.start} – {r.end}</span>
              <span className="opacity-60">(≤ {cutoff} people)</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs opacity-60 mt-3 text-addu-ink">
        Based on predicted occupancy ≤ 30% of peak, limited to 8 AM–10 PM.
      </p>
    </div>
  );
}
