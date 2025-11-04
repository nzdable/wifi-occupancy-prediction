"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type UserRow = {
  id: number;
  email: string;
  name: string | null;
  role: string;      // "Admin"|"Student" from backend (Title-case)
  status: string;    // "Active"/"Inactive"
  is_staff: boolean;
};

type PageResp = {
  count: number;
  next: string | null;
  previous: string | null;
  results: UserRow[];
};

export default function AdminUsersTable() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [data, setData] = useState<PageResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<{ kind: "success" | "error" | "info"; text: string } | null>(null);

  const url = useMemo(() => {
    const u = new URL("/users/admin/manage/", API_BASE);
    if (q.trim()) u.searchParams.set("q", q.trim());
    u.searchParams.set("page", String(page));
    u.searchParams.set("page_size", String(pageSize));
    return u.toString();
  }, [q, page, pageSize]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetch(url, { credentials: "include" })
      .then(r => {
        if (!r.ok) throw new Error("Failed to load users (are you admin?)");
        return r.json();
      })
      .then(json => { if (active) setData(json); })
      .catch(err => setNotice({ kind: "error", text: err.message }))
      .finally(() => setLoading(false));
    return () => { active = false; };
  }, [url]);

  const total = data?.count ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  const handleRoleChange = async (user: UserRow, newRoleLower: "admin" | "student") => {
    // Optimistic UI: convert back to Title-case for display
    const newDisplay = newRoleLower === "admin" ? "Admin" : "Student";
    const prev = data;
    try {
      // optimistic update
      if (data) {
        const next: PageResp = {
          ...data,
          results: data.results.map(r => (r.id === user.id ? { ...r, role: newDisplay } : r)),
        };
        setData(next);
      }

      const endpoint = `${API_BASE}/users/admin/manage/${user.id}/`;
      const res = await fetch(endpoint, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRoleLower }),
      });

      if (!res.ok) { 
        const err = await res.json().catch(() => ({})); 
        throw new Error((err as { detail?: string }).detail || "Failed to update role"); 
      } 
      setNotice({ kind: "success", text: `Updated ${user.email} → ${newDisplay}` }); 
    } 
    catch (err) { 
      if (prev) setData(prev); 
      const message = err instanceof Error ? err.message : "Update failed"; 
      setNotice({ kind: "error", text: message }); }
  };

  return (
    <main className="min-h-screen bg-[#EEF1FF] p-6 font-inter">
      <div className="mx-auto max-w-5xl bg-white/95 border border-gray-200 shadow-xl rounded-2xl p-6">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-cinzel text-addu-navy">Manage Users</h1>
            <p className="text-sm text-gray-500">Search, view, and change user roles.</p>
          </div>
          {/* Optional: reuse your AdminButton here if you want */}
        </div>

        {notice && (
          <div
            className={`mb-4 text-sm rounded-lg px-3 py-2 ${
              notice.kind === "success"
                ? "bg-green-50 border border-green-200 text-green-800"
                : notice.kind === "error"
                ? "bg-red-50 border border-red-200 text-red-800"
                : "bg-blue-50 border border-blue-200 text-blue-800"
            }`}
          >
            {notice.text}
          </div>
        )}

        <div className="flex items-center gap-3 mb-4">
          <input
            value={q}
            onChange={(e) => { setPage(1); setQ(e.target.value); }}
            placeholder="Search by email, name, or role…"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-addu-indigo outline-none"
          />
          <button
            onClick={() => { setPage(1); setQ(""); }}
            className="px-3 py-2 rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Clear
          </button>
        </div>

        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td className="px-3 py-4 text-gray-500" colSpan={4}>Loading…</td></tr>
              )}
              {!loading && data?.results.length === 0 && (
                <tr><td className="px-3 py-4 text-gray-500" colSpan={4}>No users found.</td></tr>
              )}
              {!loading && data?.results.map(u => (
                <tr key={u.id} className="border-t">
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2">{u.name || "—"}</td>
                  <td className="px-3 py-2">
                    <select
                      value={u.role} // "Admin"/"Student"
                      onChange={(e) =>
                        handleRoleChange(u, e.target.value.toLowerCase() as "admin" | "student")
                      }
                      className="border border-gray-300 rounded px-2 py-1 bg-white"
                    >
                      <option value="Admin">Admin</option>
                      <option value="Student">Student</option>
                    </select>
                  </td>
                  <td className="px-3 py-2">{u.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-gray-600">
            {total > 0 ? `Showing ${(page-1)*pageSize + 1}–${Math.min(page*pageSize, total)} of ${total}` : "—"}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-2 rounded border disabled:opacity-50"
            >
              Prev
            </button>
            <span className="text-sm">{page} / {pages}</span>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="px-3 py-2 rounded border disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}