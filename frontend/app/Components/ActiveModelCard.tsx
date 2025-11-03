"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type Library = { id: number; key: string; name: string };
type Candidate = { id: number; library_key: string; family: string; version: string };
type Notice = { kind: "success" | "error" | "info"; text: string };

export default function ActiveModelCard() {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [libKey, setLibKey] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [active, setActive] = useState<{ family: string; version: string } | null>(null);
  const [selFamily, setSelFamily] = useState("");
  const [selVersion, setSelVersion] = useState("");
  const [csrf, setCsrf] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  // CSRF (needed for PUT with credentials)
  useEffect(() => {
    fetch(`${API_BASE}/users/csrf/`, { credentials: "include" })
      .then(r => r.ok ? r.json() : { csrfToken: "" })
      .then(d => setCsrf(d?.csrfToken || ""));
  }, []);

  // Load libraries
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/occupancy/libraries/`, { credentials: "include" });
        if (!r.ok) throw new Error("Failed to load libraries");
        setLibraries(await r.json());
      } catch (e: any) {
        setNotice({ kind: "error", text: e.message || "Could not load libraries." });
      }
    })();
  }, []);

  // When library changes: load candidates, then active (404 is OK)
  useEffect(() => {
    if (!libKey) return;
    setNotice(null);

    (async () => {
      try {
        // 1) candidates
        const candRes = await fetch(
          `${API_BASE}/occupancy/models/candidates/?library=${encodeURIComponent(libKey)}`,
          { credentials: "include" }
        );
        if (!candRes.ok) throw new Error("Failed to load candidates");
        const candData: Candidate[] = await candRes.json();
        setCandidates(candData);

        // 2) active (404 means “none”)
        const activeRes = await fetch(
          `${API_BASE}/occupancy/models/active/?library=${encodeURIComponent(libKey)}`,
          { credentials: "include" }
        );

        if (activeRes.status === 404) {
            setActive(null); // show “None”
        } else if (!activeRes.ok) {
            throw new Error("Failed to load active model");
        } else {
        const activeData = await activeRes.json();
            setActive({ family: activeData.family, version: activeData.version });
        }

        // 3) set defaults for selects
        if (candData.length === 0) {
          setSelFamily("");
          setSelVersion("");
          return;
        }

        const allFamilies = Array.from(new Set(candData.map(c => c.family)));
        const initFamily =
          (activeRes.status === 200 && candData.some(c => c.family === (active as any)?.family))
            ? (active as any).family
            : allFamilies[0];

        const versions = candData.filter(c => c.family === initFamily).map(c => c.version);
        const initVersion =
          (activeRes.status === 200 &&
            (active as any) &&
            candData.some(c => c.family === initFamily && c.version === (active as any).version))
            ? (active as any).version
            : versions[0];

        setSelFamily(initFamily);
        setSelVersion(initVersion);
      } catch (e: any) {
        setNotice({ kind: "error", text: e.message || "Load error." });
      }
    })();
  }, [libKey]);

  // Families + versions derived
  const families = useMemo(
    () => Array.from(new Set(candidates.map(c => c.family))),
    [candidates]
  );
  const versionsForSelFamily = useMemo(
    () => candidates.filter(c => c.family === selFamily).map(c => c.version),
    [candidates, selFamily]
  );

  // If family changes, ensure version is valid
  useEffect(() => {
    if (!selFamily) return;
    const versions = candidates.filter(c => c.family === selFamily).map(c => c.version);
    if (versions.length && !versions.includes(selVersion)) {
      setSelVersion(versions[0]);
    }
  }, [selFamily, candidates]); // eslint-disable-line react-hooks/exhaustive-deps

  const onSave = async () => {
    if (!libKey || !selFamily || !selVersion) {
      setNotice({ kind: "error", text: "Please choose library, family, and version." });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const r = await fetch(`${API_BASE}/occupancy/models/active/`, {
        method: "PUT",
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,    // <-- add this
        },
        body: JSON.stringify({ library: libKey, family: selFamily, version: selVersion }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || "Failed to set active model.");
      setActive({ family: selFamily, version: selVersion });
      setNotice({ kind: "success", text: "Student view default updated." });
    } catch (e: any) {
      setNotice({ kind: "error", text: e.message || "Save failed." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="text-left">
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

      <label className="block text-sm font-semibold text-gray-700 mb-1">Library</label>
      <select
        className="w-full border rounded-lg px-3 py-2 mb-3 text-addu-ink bg-white border-gray-300 hover:border-addu-indigo/70 focus:ring-2 focus:ring-addu-indigo outline-none"
        value={libKey}
        onChange={(e) => setLibKey(e.target.value)}
      >
        <option value="">Choose a library</option>
        {libraries.map((lib) => (
          <option key={lib.id} value={lib.key}>{lib.name}</option>
        ))}
      </select>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Model family</label>
          <select
            value={selFamily}
            onChange={(e) => setSelFamily(e.target.value)}
            disabled={!libKey || families.length === 0}
            className="w-full border rounded-lg px-3 py-2 text-addu-ink bg-white border-gray-300 hover:border-addu-indigo/70 focus:ring-2 focus:ring-addu-indigo outline-none"
          >
            {families.length === 0 && <option value="">No candidates</option>}
            {families.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Version</label>
          <select
            value={selVersion}
            onChange={(e) => setSelVersion(e.target.value)}
            disabled={!libKey || versionsForSelFamily.length === 0}
            className="w-full border rounded-lg px-3 py-2 text-addu-ink bg-white border-gray-300 hover:border-addu-indigo/70 focus:ring-2 focus:ring-addu-indigo outline-none"
          >
            {versionsForSelFamily.length === 0 && <option value="">No versions</option>}
            {versionsForSelFamily.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <span className="font-semibold">Current student default:</span>{" "}
        {active ? (
          <span className="text-addu-indigo">{active.family} / {active.version}</span>
        ) : (
          <span className="text-gray-500">None</span>
        )}
      </div>

      <button
        onClick={onSave}
        disabled={saving || !libKey || !selFamily || !selVersion}
        className={`mt-5 w-full rounded-lg px-4 py-2 font-semibold text-addu-ink shadow transition ${
          saving ? "bg-gray-300 cursor-not-allowed" : "bg-addu-gold hover:bg-addu-amber"
        }`}
      >
        {saving ? "Saving…" : "Set as Student Default"}
      </button>
    </div>
  );
}