export function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl bg-white shadow-lg ring-1 ring-gray-100">
      {title ? (
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="text-[15px] font-semibold text-[var(--color-addu-ink)]">{title}</h2>
        </div>
      ) : null}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}
