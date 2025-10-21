"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!API_BASE) {
      router.replace("/");       // no API configured
      return;
    }
    const url = new URL("/users/whoami/", API_BASE).toString();
    fetch(url, { credentials: "include" })
      .then(r => (r.ok ? r.json() : { authenticated: false }))
      .then(d => {
        if (!d?.authenticated) router.replace("/");
        else setReady(true);
      })
      .catch(() => router.replace("/"));
  }, [router]);

  if (!ready) return null;       // or a spinner
  return <>{children}</>;
}