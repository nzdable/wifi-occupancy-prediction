export default function MetricCard({
  label, value, sub
}: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-2xl p-4 bg-addu-mist text-addu-ink shadow-sm">
      <div className="text-sm opacity-70">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {sub ? <div className="text-xs opacity-60 mt-1">{sub}</div> : null}
    </div>
  );
}
