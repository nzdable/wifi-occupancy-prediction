import LogoutButton from "../../Components/LogoutButton";
import AdminButton from "../../Components/AdminButton";
import LibraryPredictCard from "../../Components/LibraryPredictCard";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function StudentPage() {
  // Replace capacities with real values (or fetch from /occupancy/libraries/)
  const libs = [
    { key: "gisbert_2nd_floor", title: "Gisbert Library (2nd Floor)", capacity: 80 },
    { key: "gisbert_3rd_floor", title: "Gisbert Library (3rd Floor)", capacity: 40 },
    { key: "gisbert_4th_floor", title: "Gisbert Library (4th Floor)", capacity: 40 },
    { key: "gisbert_5th_floor", title: "Gisbert Library (5th Floor)", capacity: 50 },
    { key: "american_corner",  title: "American Corner",              capacity: 70 },
    { key: "miguel_pro",       title: "Miguel Pro",                   capacity: 70 },
  ];

  return (
    <main className="min-h-screen bg-addu-ink text-white flex flex-col items-center p-0">
      {/* Branded header */}
      <header className="w-full bg-gradient-to-r from-addu-navy via-addu-royal to-addu-indigo">
        <div className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between">
          <h1 className="text-addu-mist text-2xl sm:text-3xl font-cinzel">
            Library Occupancy Dashboard
          </h1>
          <AdminButton variant="inverse"/>
        </div>
      </header>

      {/* Content container */}
      <section className="w-full">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {libs.map((lib) => (
              <LibraryPredictCard
                key={lib.key}
                libKey={lib.key}
                title={lib.title}
                capacity={lib.capacity}
              />
            ))}
          </div>
        </div>
      </section>

      <footer className="w-full pb-10">
        <div className="mx-auto max-w-7xl px-6 flex justify-center">
          <LogoutButton />
        </div>
      </footer>
    </main>
  );
}
