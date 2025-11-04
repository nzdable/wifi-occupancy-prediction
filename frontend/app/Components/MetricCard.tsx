// app/Components/MetricCard.tsx
export default function MetricCard({
  label, value, sub, accent = "gold"
}: { 
  label: string; 
  value: string | number; 
  sub?: string;
  accent?: "gold" | "amber" | "yellow";
}) {
  const accentColors = {
    gold: "from-addu-gold to-addu-amber",
    amber: "from-addu-amber to-addu-yellow",
    yellow: "from-addu-yellow to-addu-gold"
  };

  return (
    <div className="group relative">
      {/* Background Glow Effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-addu-royal to-addu-indigo rounded-2xl blur-sm opacity-50 group-hover:opacity-75 transition-opacity duration-300" />
      
      <div className="relative rounded-2xl p-6 bg-gradient-to-br from-addu-navy to-addu-ink border border-addu-royal/30 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-[1.02]">
        {/* Accent Bar */}
        <div className={`absolute top-0 left-0 w-1 h-full bg-gradient-to-b ${accentColors[accent]} rounded-l-2xl`} />
        
        <div className="ml-3">
          <div className="text-sm opacity-80 font-medium mb-2">{label}</div>
          <div className="text-3xl font-bold bg-gradient-to-r from-addu-gold to-addu-amber bg-clip-text text-transparent">
            {value}
          </div>
          {sub ? (
            <div className="text-xs opacity-60 mt-2 font-medium">{sub}</div>
          ) : null}
        </div>
      </div>
    </div>
  );
}