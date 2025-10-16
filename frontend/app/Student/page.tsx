// app/Student/page.tsx
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LogoutButton from "../Components/LogoutButton";
import LibraryCard from "../Components/LibraryCard";
import { API_BASE } from "../lib/config";

export default async function StudentPage() {
  // 👇 await it
  const store = await cookies();

  // Option A: Next exposes a header string
  const cookieHeader = store.toString();

  // Option B: build manually (works everywhere)
  // const cookieHeader = store.getAll().map(c => `${c.name}=${c.value}`).join("; ");

  const res = await fetch(`${API_BASE}/whoami/`, {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });

  if (!res.ok) redirect("/");
  const data = await res.json();
  if (!data.authenticated) redirect("/");

  return (
    <main className="min-h-screen bg-[#030B3A] text-white flex flex-col items-center p-10 space-y-10">
      <header className="bg-gradient-to-r from-addu-navy via-addu-royal to-addu-indigo py-6 text-center text-3xl font-cinzel font-semibold w-full">
        Library Occupancy Dashboard
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 w-full max-w-6xl">
        <LibraryCard name="Gisbert Library" occupancy={72}/>
        <LibraryCard name="American Corner" occupancy={54}/>
        <LibraryCard name="Mig Pro" occupancy={28} />
      </div>
    </main>
  );
}
