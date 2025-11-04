// app/(protected)/Student/[libkey]/page.tsx
import "server-only";
import GraphSection from "@/app/Components/GraphSection";
import LibraryNav from "@/app/Components/LibraryNav";
import MetricCard from "@/app/Components/MetricCard";

type Point = { time_local: string; predicted?: number };
type RawParams = { libkey: string };
type RawSearchParams = Record<string, string | string[] | undefined>;
type PageProps = {
params: Promise<{ libkey: string }>;
searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const pickOne = (v: string | string[] | undefined) =>
Array.isArray(v) ? v[0] : v;
const safeToken = (v: string | undefined) =>
(v ?? "").replace(/['"]/g, "").toLowerCase();

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function LibraryDetailPage({ params, searchParams }: PageProps) {
  const resolvedParams = await params
  const resolvedSearch = await searchParams
  const base = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
  const libKey = safeToken(resolvedParams.libkey);
  const family = safeToken(pickOne(resolvedSearch?.family)) || "";
  const date = pickOne(resolvedSearch?.date) ?? new Date().toISOString().slice(0, 10);

  const u = new URL(`${base}/occupancy/forecast/day`);
  u.searchParams.set("library", libKey);
  u.searchParams.set("date", date);
  if (family) u.searchParams.set("family", family);

  const res = await fetch(u.toString(), { cache: "no-store" });
  const js = res.ok ? await res.json().catch(() => null) : null;
  const points: Point[] = Array.isArray(js?.points) ? js.points : [];

  const labels = points.map((p) =>
    new Date(p.time_local).toLocaleTimeString([], { hour: "2-digit" })
  );
  const hours24 = points.map((p) => new Date(p.time_local).getHours());
  const predicted = points.map((p) => p.predicted ?? 0);

  const peak = Math.max(0, ...predicted);
  const peakIdx = predicted.indexOf(peak);

  return (
    <div className="min-h-screen px-6 py-6 space-y-6 bg-addu-ink text-white font-inter">
      <div className="bg-gradient-to-r from-addu-navy via-addu-royal to-addu-indigo rounded-2xl p-4 shadow-md">
        <LibraryNav current={libKey} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="Peak (predicted)" value={`${peak} ppl`} sub={labels[peakIdx] ?? "--"} />
        <MetricCard
          label="Average (predicted)"
          value={`${Math.round(predicted.reduce((a, b) => a + b, 0) / Math.max(predicted.length, 1))} ppl`}
          sub="across the day"
        />
        <MetricCard
          label="Current hour (predicted)"
          value={`${predicted[new Date().getHours()] ?? "--"} ppl`}
          sub={new Date().toLocaleString([], { hour: "numeric" })}
        />
      </div>

      <GraphSection
        libKey={libKey}
        date={date}
        family={family}
        labels={labels}
        predicted={predicted}
        hours24={hours24}
      />
    </div>
  );
}
