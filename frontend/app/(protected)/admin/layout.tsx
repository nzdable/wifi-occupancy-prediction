import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function getUser() {
  const cookieHeader = (await cookies()).toString();
  const res = await fetch(`${API_BASE}/users/whoami/`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!res.ok) return null;
  const d = await res.json();
  return d?.authenticated ? d : null;
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getUser();
  if (!user) redirect("/");
  if ((user.role || "").toLowerCase() !== "admin") redirect("/student");
  return <>{children}</>;
}
