// app/Student/page.tsx
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LogoutButton from "../Components/LogoutButton";

export default async function StudentPage() {
  // 👇 await it
  const store = await cookies();

  // Option A: Next exposes a header string
  const cookieHeader = store.toString();

  // Option B: build manually (works everywhere)
  // const cookieHeader = store.getAll().map(c => `${c.name}=${c.value}`).join("; ");

  const res = await fetch("http://localhost:8000/whoami/", {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });

  if (!res.ok) redirect("/");
  const data = await res.json();
  if (!data.authenticated) redirect("/");

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-[#030B3A] text-white">
      <h1 className="text-3xl font-bold mb-2">Welcome!</h1>
      <p className="opacity-80">Signed in as {data.email}</p>
      <LogoutButton/>
    </main>
  );
}
