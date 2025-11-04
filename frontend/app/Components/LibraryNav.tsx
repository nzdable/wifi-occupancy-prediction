"use client";

import Link from "next/link";
import { useMemo } from "react";

export type LibInfo = { key: string; title: string };
const LIBS: LibInfo[] = [
  { key: "gisbert_2nd_floor", title: "Gisbert Library (2nd Floor)" },
  { key: "gisbert_3rd_floor", title: "Gisbert Library (3rd Floor)" },
  { key: "gisbert_4th_floor", title: "Gisbert Library (4th Floor)" },
  { key: "gisbert_5th_floor", title: "Gisbert Library (5th Floor)" },
  { key: "american_corner",  title: "American Corner"              },
  { key: "miguel_pro",       title: "Miguel Pro"                   },
  // add more here if you have them
];

export default function LibraryNav({ current }: { current: string }) {
  const { prev, next, currentTitle } = useMemo(() => {
    const i = Math.max(0, LIBS.findIndex(l => l.key === current));
    const prev = LIBS[(i - 1 + LIBS.length) % LIBS.length];
    const next = LIBS[(i + 1) % LIBS.length];
    const cur  = LIBS[i] ?? { key: current, title: current };
    return { prev, next, currentTitle: cur.title };
  }, [current]);

  return (
    <div className="flex items-center justify-between w-full">
      <Link
        href={`/Student/${prev.key}`}
        className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition"
        aria-label={`Go to ${prev.title}`}
      >
        ← {prev.title}
      </Link>
      <Link
        href={'/Student'}
        className="cursor-pointer"
      >
        <h1 className="font-cinzel text-xl text-addu-ink">{currentTitle}</h1>
      </Link>

      <Link
        href={`/Student/${next.key}`}
        className="px-3 py-2 rounded-xl bg-addu-royal text-white hover:bg-addu-indigo transition"
        aria-label={`Go to ${next.title}`}
      >
        {next.title} →
      </Link>
    </div>
  );
}
