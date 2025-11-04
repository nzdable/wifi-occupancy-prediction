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

function filterLibraryHours(labels: string[], predicted: number[], hours24: number[]) {
  const filteredLabels: string[] = [];
  const filteredPredicted: number[] = [];
  const filteredHours24: number[] = [];

  labels.forEach((label, index) => {
    const timeString = label.toLowerCase();
    let hour = 0;
    
    if (timeString.includes('am')) {
      hour = parseInt(timeString.replace('am', '').trim());
      if (hour === 12) hour = 0;
    } else if (timeString.includes('pm')) {
      hour = parseInt(timeString.replace('pm', '').trim());
      if (hour !== 12) hour += 12;
    }

    if (hour >= 7 && hour <= 22) {
      filteredLabels.push(label);
      filteredPredicted.push(predicted[index]);
      filteredHours24.push(hours24[index]);
    }
  });

  return { filteredLabels, filteredPredicted, filteredHours24 };
}

export default function GraphSection({
  libKey, date, family, labels, predicted, hours24
}: {
  libKey: string; date: string; family: string;
  labels: string[]; predicted: number[]; hours24: number[]
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const searchKey = sp?.toString() || "";
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setPending(false);
  }, [searchKey, date]);

  const d = useMemo(() => {
    const [y,m,dd] = date.split("-").map(Number);
    return new Date(y, (m ?? 1) - 1, dd ?? 1);
  }, [date]);

  const { filteredLabels, filteredPredicted, filteredHours24 } = useMemo(() => {
    return filterLibraryHours(labels, predicted, hours24);
  }, [labels, predicted, hours24]);

  const go = (newDate: string) => {
    const params = new URLSearchParams(sp?.toString() || "");
    params.set("date", newDate);
    if (family) params.set("family", family);
    else params.delete("family");
    setPending(true);
    router.replace(`/Student/${libKey}?${params.toString()}`, { scroll: false });
    setTimeout(() => setPending(false), 15000);
  };

  const shift = (days: number) => {
    const nd = new Date(d);
    nd.setDate(d.getDate() + days);
    go(fmt(nd));
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-4 gap-8 items-start">
      {/* Main Chart Area */}
      <div className="xl:col-span-3 space-y-6">
        {/* Date Navigation */}
        <div className="bg-gradient-to-r from-addu-navy to-addu-royal rounded-2xl p-6 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button 
                onClick={() => shift(-1)}
                className="px-4 py-3 rounded-xl bg-addu-indigo text-white hover:bg-addu-royal transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2 cursor-pointer"
              >
                <span>←</span>
                <span>Prev</span>
              </button>
              
              <button 
                onClick={() => shift(1)}
                className="px-4 py-3 rounded-xl bg-addu-indigo text-white hover:bg-addu-royal transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2 cursor-pointer"
              >
                <span>Next</span>
                <span>→</span>
              </button>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="date"
                value={date}
                onChange={(e) => go(e.target.value)}
                className="px-4 py-3 rounded-xl border-2 border-addu-mist bg-addu-ink text-white focus:border-addu-gold focus:outline-none transition-colors"
              />
              
              <button 
                onClick={() => go(fmt(new Date()))}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-addu-gold to-addu-amber text-addu-ink font-semibold hover:shadow-lg transition-all duration-200 hover:scale-105 cursor-pointer"
              >
                Today
              </button>
            </div>
          </div>
        </div>

        {/* Chart Container */}
        <div className="relative">
          <div className="bg-gradient-to-br from-addu-navy to-addu-ink rounded-2xl p-6 shadow-2xl border border-addu-royal/30">
            <PredictedLineChart 
              key={date} 
              labels={filteredLabels} 
              values={filteredPredicted} 
            />
          </div>
          
          {pending && (
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm rounded-2xl flex items-center justify-center">
              <div className="flex items-center gap-3 bg-addu-ink/90 px-6 py-4 rounded-xl border border-addu-royal">
                <div className="h-6 w-6 rounded-full border-2 border-addu-gold/40 border-t-addu-gold animate-spin" />
                <span className="text-white text-sm font-medium">Loading new date…</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <BestTimesCard 
          labels={filteredLabels} 
          predicted={filteredPredicted} 
          hours24={filteredHours24} 
        />
        
        {/* Additional Info Card */}
        <div className="rounded-2xl p-6 bg-gradient-to-br from-addu-navy to-addu-royal border border-addu-indigo/30 shadow-xl">
          <h3 className="font-open-sans text-white font-semibold mb-3">Library Hours</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-addu-mist">
              <span>Monday - Friday</span>
              <span>7 AM - 10 PM</span>
            </div>
            <div className="flex justify-between text-addu-mist">
              <span>Saturday</span>
              <span>8 AM - 6 PM</span>
            </div>
            <div className="flex justify-between text-addu-mist">
              <span>Sunday</span>
              <span>Closed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}