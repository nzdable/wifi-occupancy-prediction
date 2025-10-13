// app/Student/page.tsx
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LogoutButton from "../Components/LogoutButton";

export default async function StudentPage() {
  // Forward the user's cookies to Django so it can check the session
  const cookieHeader = cookies().toString();

  const res = await fetch("http://localhost:8000/whoami/", {
    headers: { Cookie: cookieHeader },
    // ensure we don't cache the auth check
    cache: "no-store",
  });

  // If Django is down or whoami fails, be defensive:
  if (!res.ok) {
    redirect("/"); // or show an error page
  }

  const data = await res.json();

  if (!data.authenticated) {
    // Not logged in → send user back to login
    redirect("/");
  }

  // Logged in → render the page
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-[#030B3A] text-white">
      <h1 className="text-3xl font-bold mb-2">Welcome!</h1>
      <p className="opacity-80">Signed in as {data.email}</p>
      <LogoutButton/>
      {/* ...rest of your dashboard... */}
    </main>
  );
}