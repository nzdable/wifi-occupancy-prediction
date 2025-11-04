"use client";

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Link from "next/link";

type Props = {
  libKey: string;
  title: string;
  capacity: number;
  family?: string;
};

type AtResponse = {
  ok?: boolean;
  prediction?: number;
  generated_at?: string;
  library?: string;
  detail?: string;
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

// Build 'YYYY-MM-DDTHH:mm' in Asia/Manila
function fmtPHNowYmdHM(): string {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(fmt.formatToParts(new Date()).map(p => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

export default function LibraryPredictCard({ libKey, title, capacity, family }: Props) {
  const [count, setCount] = useState<number | null>(null);
  const [when, setWhen] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inflight = useRef<AbortController | null>(null);

  const percent = useMemo(() => {
    if (count == null || capacity <= 0) return null;
    const pct = Math.round((count / capacity) * 100);
    return Math.max(0, Math.min(100, pct));
  }, [count, capacity]);

  const level = useMemo(() => {
    const p = percent ?? 0;
    if (p < 40) return { text: "Low", color: "text-green-500", stroke: "#22c55e" };
    if (p < 70) return { text: "Moderate", color: "text-addu-amber", stroke: "#FFDB58" };
    return { text: "High", color: "text-red-500", stroke: "#ef4444" };
  }, [percent]);

  const fetchNow = useCallback(async () => {
    setErr(null);
    setLoading(true);
    inflight.current?.abort();
    const ac = new AbortController();
    inflight.current = ac;

    const whenPH = fmtPHNowYmdHM();
    const u = new URL(`${API_BASE}/occupancy/forecast/at`);
    u.searchParams.set("library", libKey);
    u.searchParams.set("when", whenPH);
    if (family) u.searchParams.set("family", family);

    try {
      const res = await fetch(u.toString(), {
        signal: ac.signal,
        cache: "no-store",
        credentials: "omit",
      });
      const js: AtResponse | null = res.ok ? await res.json().catch(() => null) : null;

      if (!res.ok || !js || typeof js.prediction !== "number") {
        throw new Error(js?.detail || `HTTP ${res.status}`);
      }

      setCount(Math.max(0, Math.round(js.prediction)));
      setWhen(js.generated_at || whenPH);
    } catch (e) {
      const errObj = e as Error;
      const msg = errObj?.message ?? "Request failed";
      if (errObj.name === "AbortError" || msg.includes("aborted")) return;
      setErr(msg);
    } finally {
      setLoading(false);
    }
  }, [libKey, family]);

  useEffect(() => {
    fetchNow();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(fetchNow, 60_000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      inflight.current?.abort();
    };
  }, [fetchNow]);

  const r = 54;
  const C = 2 * Math.PI * r;
  const dash = useMemo(() => {
    const p = percent ?? 0;
    const filled = (p / 100) * C;
    return `${filled} ${C - filled}`;
  }, [percent, C]);

  const href = family ? `/Student/${libKey}?family=${encodeURIComponent(family)}` : `/Student/${libKey}`;

  return (
    <Link
      href={href}
      prefetch={false}
      aria-label={`Open insights for ${title}`}
      className="group block rounded-2xl"
    >
      <div
        className="
          group relative flex flex-col items-center justify-between
          rounded-2xl border border-addu-mist/20 bg-addu-ink
          shadow-[0_10px_30px_rgba(4,3,84,0.25)]
          hover:shadow-[0_12px_36px_rgba(22,17,177,0.35)]
          transition-all duration-200 p-6 w-full max-w-sm
        "
      >
        <h2 className="text-addu-mist font-open-sans text-lg font-semibold text-center mb-4">
          {title}
        </h2>

        <div className="relative w-40 h-40 mb-3">
          <svg viewBox="0 0 140 140" className="w-40 h-40 -rotate-90">
            <circle cx="70" cy="70" r={r} stroke="#E6E9F922" strokeWidth="12" fill="none" />
            <circle
              cx="70"
              cy="70"
              r={r}
              stroke={level.stroke}
              strokeWidth="12"
              strokeLinecap="round"
              fill="none"
              strokeDasharray={dash}
              className="transition-[stroke-dasharray] duration-500 ease-out"
            />
          </svg>

          <div className="absolute inset-0 rotate-0 flex flex-col items-center justify-center">
            {percent == null ? (
              <span className="text-addu-mist/80 text-sm">Loading…</span>
            ) : (
              <>
                <span className="text-3xl font-bold text-white">{percent}%</span>
                <span className="text-[11px] text-addu-mist/70">
                  {count} / {capacity}
                </span>
              </>
            )}
          </div>
        </div>

        <p className="text-sm text-addu-mist/80">
          Crowd Level: <span className={`font-semibold ${level.color}`}>{level.text}</span>
        </p>

        <div className="flex items-center gap-2 mt-1 h-[18px]">
          {loading && (
            <span className="h-4 w-4 rounded-full border-2 border-white/40 border-t-addu-royal animate-spin" />
          )}
          {when && !loading && (
            <p className="text-[11px] text-addu-mist/60">Updated {new Date(when).toLocaleString()}</p>
          )}
        </div>

        {err && <p className="text-xs text-red-400 mt-2">Error: {err}</p>}

        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-0 ring-addu-yellow/0 group-hover:ring-4 group-hover:ring-addu-yellow/20 transition-all duration-200" />
      </div>
    </Link>
  );
}
