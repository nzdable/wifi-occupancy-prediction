import LogoutButton from "../Components/LogoutButton";
import LibraryCard from "../Components/LibraryCard";
import AuthGate from "../Components/AuthGate";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function StudentPage() {

  return (
    <AuthGate>
      <main className="min-h-screen bg-[#030B3A] text-white flex flex-col items-center p-10 space-y-10">
        <header className="bg-gradient-to-r from-addu-navy via-addu-royal to-addu-indigo py-6 text-center text-3xl font-cinzel font-semibold w-full">
          Library Occupancy Dashboard
        </header>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 w-full max-w-6xl">
          <LibraryCard name="Gisbert Library" occupancy={72}/>
          <LibraryCard name="American Corner" occupancy={54}/>
          <LibraryCard name="Mig Pro" occupancy={28} />
        </div>
        <LogoutButton/>
      </main>
    </AuthGate>
  );
}
