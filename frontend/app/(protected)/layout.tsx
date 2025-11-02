// app/(protected)/layout.tsx
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function getUser() {
  const cookieHeader = (await cookies()).toString();
  const hdrs = await headers(); // <-- await

  const res = await fetch(`${API_BASE}/users/whoami/`, {
    method: "GET",
    headers: {
      cookie: cookieHeader,
      // optional passthroughs; safe to remove if you don't use them server-side
      "x-forwarded-for": hdrs.get("x-forwarded-for") ?? "",
      "user-agent": hdrs.get("user-agent") ?? "",
    },
    cache: "no-store",
  });

  if (!res.ok) return null;
  const data = await res.json();
  return data?.authenticated ? data : null;
}

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const user = await getUser();
  if (!user) redirect("/"); // not logged in
  return <>{children}</>;
}
