// Shell component (Shell.tsx)
import AdminButton from "../Components/AdminButton";

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#EEF1FF] font-inter">
      <header className="bg-gradient-to-r from-addu-navy via-addu-royal to-addu-indigo py-6 text-center text-3xl font-cinzel font-semibold">
        Library Occupancy System
        <AdminButton/>
      </header>

      {/* Main Content */}
      <div className="flex">
        <nav className="w-1/4 bg-addu-ink text-white py-8 px-4 space-y-4">
          <h2 className="font-semibold text-xl">Library Sections</h2>
          <ul>
            <li><a href="#" className="block py-2">Gisbert Library</a></li>
            <li><a href="#" className="block py-2">American Corner</a></li>
            <li><a href="#" className="block py-2">Mig Pro</a></li>
          </ul>
        </nav>

        <main className="w-3/4 p-8 bg-white rounded-lg shadow-lg">
          {children}
        </main>
      </div>

      <footer className="bg-addu-navy text-white py-4 text-center">
        <p>© 2025 Ateneo de Davao University</p>
      </footer>
    </div>
  );
}
