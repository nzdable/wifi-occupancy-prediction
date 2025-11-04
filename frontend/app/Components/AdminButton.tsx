"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type Variant = "primary" | "inverse";

export default function AdminButton({ variant = "primary" }: { variant?: Variant }) {
  const router = useRouter();
  const pathname = usePathname();

  const [isAdmin, setIsAdmin] = useState(false);
  const [checked, setChecked] = useState(false);
  const [swapping, setSwapping] = useState(false);

  useEffect(() => {
    fetch(new URL("/users/whoami/", API_BASE).toString(), { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const role = (d?.role ?? "").toString().trim().toLowerCase();
        if (role === "admin") setIsAdmin(true);
      })
      .finally(() => setChecked(true));
  }, []);

  const handleSwap = useCallback(() => {
    if (swapping) return;
    setSwapping(true);
    const onAdmin = pathname.startsWith("/admin");
    router.push(onAdmin ? "/Student" : "/admin");
    setTimeout(() => setSwapping(false), 600);
  }, [pathname, router, swapping]);

  if (!checked || !isAdmin) return null;

  const label = pathname.startsWith("/admin")
    ? "Switch to Student Page"
    : "Switch to Admin Page";

  const base =
    "px-4 py-2 rounded-md font-inter font-medium transition-colors focus:outline-none focus-visible:ring-2";
  const styles =
    variant === "inverse"
      ? // For dark headers (navy background)
        "border border-white text-white hover:bg-white hover:text-[var(--color-addu-navy)] hover:shadow-[0_0_12px_rgba(255,255,255,0.4)] hover:-translate-y-[2px] focus-visible:ring-white/60 active:translate-y-[0px]"
      : // For light backgrounds
        "border border-[var(--color-addu-navy)] text-[var(--color-addu-navy)] hover:bg-[var(--color-addu-indigo)] hover:text-white hover:shadow-md hover:-translate-y-[2px] focus-visible:ring-[var(--color-addu-indigo)]/60 active:translate-y-[0px]";

  const disabled = "disabled:opacity-60 disabled:cursor-not-allowed";

  return (
    <button
      onClick={handleSwap}
      disabled={swapping}
      aria-label={label}
      title={`${label} (Shift+S)`}
      className={`${base} ${styles} ${disabled} cursor-pointer transform`} 
    >
      {swapping ? "Switching…" : label}
    </button>
  );
}