"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

function fmt(d: Date) {
  // YYYY-MM-DD in local time (works for your backend parser)
  const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

export default function DateControls({
  libKey,
  date,          // "YYYY-MM-DD" from server
  family = "cnn",
}: { libKey: string; date: string; family?: string }) {
  const router = useRouter();
  const sp = useSearchParams();

  const go = useCallback((newDate: string) => {
    const params = new URLSearchParams(sp?.toString() || "");
    params.set("date", newDate);
    params.set("family", family);
    router.replace(`/Student/${libKey}?${params.toString()}`, { scroll: false });
  }, [router, sp, libKey, family]);

  const d = useMemo(() => {
    // safe parse YYYY-MM-DD in local tz
    const [y, m, dd] = date.split("-").map(Number);
    return new Date(y, (m ?? 1) - 1, dd ?? 1);
  }, [date]);

  const shift = (days: number) => {
    const nd = new Date(d);
    nd.setDate(d.getDate() + days);
    go(fmt(nd));
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => shift(-1)}
        className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition"
        aria-label="Previous day"
      >
        ← Prev
      </button>

      <input
        type="date"
        className="px-3 py-2 rounded-xl border border-addu-mist bg-white text-addu-ink"
        value={date}
        onChange={(e) => go(e.target.value)}
        aria-label="Pick a date"
      />

      <button
        onClick={() => go(fmt(new Date()))}
        className="px-3 py-2 rounded-xl bg-addu-gold text-addu-ink hover:bg-addu-amber transition"
        aria-label="Today"
      >
        Today
      </button>

      <button
        onClick={() => shift(1)}
        className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition"
        aria-label="Next day"
      >
        Next →
      </button>
    </div>
  );
}
