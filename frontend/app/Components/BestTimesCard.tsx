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
  labels, predicted
}: { labels: string[]; predicted: number[] }) {
  const peak = Math.max(1, ...predicted);
  const cutoff = Math.round(peak * 0.3); // <= 30% of peak is “low”
  const ranges = compressRanges(predicted, labels, cutoff).slice(0, 3);

  return (
    <div className="rounded-2xl p-4 bg-white border border-addu-mist shadow-sm">
      <h2 className="font-open-sans text-addu-ink mb-2">Best times to visit</h2>
      {ranges.length === 0 ? (
        <p className="text-sm opacity-70">No low-crowd windows detected today.</p>
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
        Based on predicted occupancy ≤ 30% of peak.
      </p>
    </div>
  );
}
