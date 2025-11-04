"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import AdminButton from "../Components/AdminButton";

export default function AdminShell({
  children,
  title = "Library Occupancy System",
}: { children: React.ReactNode; title?: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const v = localStorage.getItem("adminSidebarCollapsed");
    if (v !== null) setCollapsed(v === "1");
  }, []);
  useEffect(() => {
    localStorage.setItem("adminSidebarCollapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className="min-h-svh bg-[var(--color-addu-mist)] text-[var(--color-addu-ink)]">
      {/* HEADER: fixed height 56px (h-14) so we can compute remaining height */}
      <header className="sticky top-0 z-50 w-full h-14 bg-[var(--color-addu-navy)] text-white shadow">
        <div className="flex h-full items-center justify-between gap-3 px-3 sm:px-6">
          <div className="flex items-center gap-2">
            {/* mobile menu */}
            <button
              className="inline-flex md:hidden rounded-md px-2 py-1.5 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
              aria-label="Open menu"
              onClick={() => setMobileOpen(true)}
            >
              ☰
            </button>
            {/* desktop collapse */}
            <button
              className="hidden md:inline-flex rounded-md px-2 py-1.5 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setCollapsed(v => !v)}
            >
              {collapsed ? "›" : "‹"}
            </button>
            <h1 className="text-lg sm:text-2xl font-cinzel tracking-wide">{title}</h1>
          </div>
          <AdminButton variant="inverse" />
        </div>
      </header>

      {/* BODY: fill the rest of the viewport height */}
      <div className="flex w-full min-h-[calc(100svh-56px)]">
        {/* SIDEBAR (desktop) */}
        <aside
          className={[
            "hidden md:block shrink-0 transition-all duration-200",
            "sticky top-14 self-start",                            // sticks under the 56px header
            "min-h-[calc(100svh-56px)]",                            // fill remaining height
            "bg-[color-mix(in_oklab,var(--color-addu-royal)_20%,white)] text-white",
            collapsed ? "w-[64px]" : "w-[220px]",
          ].join(" ")}
        >
          <div className="px-2 py-4">
            <Nav collapsed={collapsed} />
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 min-h-[calc(100svh-56px)]">
          <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 py-6">
            {children}
          </div>
        </main>
      </div>

      {/* MOBILE DRAWER */}
      {mobileOpen && (
        <>
          <button
            aria-label="Close menu"
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside
            className="fixed left-0 top-0 z-50 h-svh w-64 bg-[color-mix(in_oklab,var(--color-addu-royal)_20%,white)] text-white shadow-2xl md:hidden"
            role="dialog" aria-modal="true"
          >
            <div className="flex items-center justify-between px-3 py-3">
              <span className="font-semibold">Menu</span>
              <button
                className="rounded-md px-2 py-1.5 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>
            <div className="px-3 pb-4">
              <Nav collapsed={false} onNavigate={() => setMobileOpen(false)} />
            </div>
          </aside>
        </>
      )}
    </div>
  );
}

function Nav({
  collapsed, onNavigate,
}: { collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const items = useMemo(
    () => [
      { href: "/admin", label: "Insights", icon: "📊" },
      { href: "/admin/users", label: "Users", icon: "👥" },
    ],
    []
  );

  return (
    <nav className="space-y-1">
      {items.map((it) => {
        const active = pathname === it.href;
        return (
          <Link
            key={it.href}
            href={it.href}
            onClick={onNavigate}
            className={[
              "group flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-white text-[var(--color-addu-ink)]"
                : "text-[color-mix(in_srgb,white_80%,var(--color-addu-yellow))] hover:bg-white/10",
            ].join(" ")}
            title={collapsed ? it.label : undefined}
          >
            <span className="text-base">{it.icon}</span>
            <span className={collapsed ? "sr-only" : ""}>{it.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
