// app/Components/GraphSection.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import PredictedLineChart from "@/app/Components/PredictedLineChart";
import BestTimesCard from "@/app/Components/BestTimesCard";

function fmt(d: Date) {
  const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}`;
}

export default function GraphSection({
  libKey, date, family, labels, predicted, hours24
}: {
  libKey: string; date: string; family: string;
  labels: string[]; predicted: number[]; hours24: number[]
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const searchKey = sp?.toString() || ""; // ← track querystring changes
  const [pending, setPending] = useState(false);

  // ⬇️ Clear the overlay whenever the querystring OR the date prop changes
  useEffect(() => {
    setPending(false);
  }, [searchKey, date]);

  const d = useMemo(() => {
    const [y,m,dd] = date.split("-").map(Number);
    return new Date(y, (m ?? 1) - 1, dd ?? 1);
  }, [date]);

  const go = (newDate: string) => {
    const params = new URLSearchParams(sp?.toString() || "");
    params.set("date", newDate);
    if (family) params.set("family", family);
    else params.delete("family");
    setPending(true); // show overlay until the URL updates and server sends new props
    router.replace(`/Student/${libKey}?${params.toString()}`, { scroll: false });

    // optional safety net so it never sticks forever during dev
    setTimeout(() => setPending(false), 15000);
  };

  const shift = (days: number) => {
    const nd = new Date(d);
    nd.setDate(d.getDate() + days);
    go(fmt(nd));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <div className="lg:col-span-2 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => shift(-1)}
                  className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition">← Prev</button>
          <input
            type="date"
            value={date}
            onChange={(e) => go(e.target.value)}
            className="px-3 py-2 rounded-xl border border-addu-mist bg-white text-addu-ink"
          />
          <button onClick={() => go(fmt(new Date()))}
                  className="px-3 py-2 rounded-xl bg-addu-gold text-addu-ink hover:bg-addu-amber transition">Today</button>
          <button onClick={() => shift(1)}
                  className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition">Next →</button>
        </div>

        <div className="relative">
          {/* key={date} forces a clean chart remount on each date change */}
          <PredictedLineChart key={date} labels={labels} values={predicted} />
          {pending && (
            <div className="absolute inset-0 bg-black/25 backdrop-blur-[1px] rounded-2xl flex items-center justify-center">
              <div className="flex items-center gap-3">
                <span className="h-5 w-5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                <span className="text-white text-sm">Loading new date…</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        <BestTimesCard labels={labels} predicted={predicted} hours24={hours24} />
      </div>
    </div>
  );
}