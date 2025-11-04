"use client";

import { useEffect, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

interface Library { id: number; key: string; name: string; }
type Notice = { kind: "success" | "error" | "info"; text: string };

export default function UploadCsvPanel() {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [selectedLibrary, setSelectedLibrary] = useState("");
  const [replace, setReplace] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [errors, setErrors] = useState<{ library?: string; file?: string }>({});
  const [csrf, setCsrf] = useState<string>("");

  useEffect(() => {
    // get CSRF token from backend origin
    fetch(`${API_BASE}/users/csrf/`, { credentials: "include" })
      .then(r => r.ok ? r.json() : { csrfToken: "" })
      .then(d => setCsrf(d?.csrfToken || ""));
  }, []);


  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/occupancy/libraries/`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to load libraries");
        const data = await res.json();
        setLibraries(data);
      } catch (err) {
        console.error(err);
        setNotice({ kind: "error", text: "Error loading libraries." });
      }
    })();
  }, []);

  const validate = () => {
    const newErrors: { library?: string; file?: string } = {};
    if (!selectedLibrary) newErrors.library = "Please select a library.";
    if (!file) newErrors.file = "Please choose or drag a .csv file.";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLibraryChange = (value: string) => {
    setSelectedLibrary(value);
    setErrors((e) => ({ ...e, library: value ? undefined : e.library }));
    setNotice(null);
  };

  const handleFileChange = (f: File | null) => {
    if (f && !f.name.toLowerCase().endsWith(".csv")) {
      setErrors((e) => ({ ...e, file: "Only .csv files are accepted." }));
      setFile(null);
      return;
    }
    setFile(f);
    setErrors((e) => ({ ...e, file: f ? undefined : e.file }));
    setNotice(null);
  };

  const handleUpload = async () => {
    setNotice(null);
    if (!validate()) return;
    setUploading(true);
    try {
      if (replace) {
        await fetch(
          `${API_BASE}/occupancy/signals/bulk_delete/?library__key=${encodeURIComponent(selectedLibrary)}`,
          { 
            method: "DELETE", 
            credentials: "include", 
            headers: { "X-CSRFToken": csrf }, }
        );
      }
      const formData = new FormData();
      formData.append("file", file as File);
      formData.append("library", selectedLibrary);

      const res = await fetch(`${API_BASE}/occupancy/uploads/cleaned-wifi/`, {
        method: "POST",
        body: formData,
        credentials: "include",
        headers: { "X-CSRFToken": csrf },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed.");
      }
      const data = await res.json();
      setNotice({ kind: "success", text: `Uploaded successfully. ${data.rows_ingested} rows added.` });
      setFile(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setNotice({ kind: "error", text: message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="text-left">
      {notice && (
        <div
          role="status"
          aria-live="polite"
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

      <label className="block text-sm font-semibold text-gray-700 mb-1">
        Select Library <span className="text-red-600">*</span>
      </label>
      <select
        className={`w-full border rounded-lg px-3 py-2 mb-1 text-addu-ink bg-white focus:ring-2 focus:ring-addu-indigo outline-none transition ${
          errors.library ? "border-red-400" : "border-gray-300 hover:border-addu-indigo/70"
        }`}
        value={selectedLibrary}
        onChange={(e) => handleLibraryChange(e.target.value)}
      >
        <option value="">Choose a library</option>
        {libraries.map((lib) => (
          <option key={lib.id} value={lib.key}>
            {lib.name}
          </option>
        ))}
      </select>
      {errors.library && <p className="text-xs text-red-600 mb-3" role="alert">{errors.library}</p>}
      {!errors.library && <div className="mb-3" />}

      <label className="flex items-center gap-2 text-sm text-gray-600 mb-4">
        <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
        Replace existing data for this library
      </label>

      <label className="block text-sm font-semibold text-addu-ink mb-1">
        Upload CSV File <span className="text-red-600">*</span>
      </label>
      <div
        onDrop={(e) => {
          e.preventDefault();
          const droppedFile = e.dataTransfer.files?.[0] || null;
          handleFileChange(droppedFile);
        }}
        onDragOver={(e) => e.preventDefault()}
        className={`w-full border-2 border-dashed rounded-lg p-6 text-center transition ${
          file
            ? "border-addu-gold bg-addu-gold/10"
            : errors.file
            ? "border-red-400 bg-red-50"
            : "border-gray-300 bg-white hover:border-addu-indigo/60 hover:bg-addu-indigo/5"
        }`}
      >
        <input
          id="csvFile"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
        />
        <label htmlFor="csvFile" className="cursor-pointer text-addu-indigo font-semibold hover:underline">
          {file ? "Change File" : "Choose or drag CSV here"}
        </label>
        <p className="text-sm text-gray-700 mt-2">
          {file ? <span className="font-medium text-addu-ink">{file.name}</span> : "Only .csv files are accepted"}
        </p>
      </div>
      {errors.file && <p className="text-xs text-red-600 mt-1" role="alert">{errors.file}</p>}

      <button
        onClick={handleUpload}
        disabled={uploading}
        className={`cursor-pointer mt-5 w-full rounded-lg px-4 py-2 font-semibold text-addu-ink shadow transition ${
          uploading ? "bg-gray-300 cursor-not-allowed" : "bg-addu-gold hover:bg-addu-amber"
        }`}
      >
        {uploading ? "Uploading…" : "Upload CSV"}
      </button>
    </div>
  );
}
