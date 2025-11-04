'use client';

import React, { useEffect, useMemo, useState } from 'react';

type FamilyKey = 'cnn' | 'lstm' | 'cnn_lstm' | 'cnn_lstm_attn';

type LibraryDto = {
  key: string;
  title: string;
};

type DefaultDto = {
  family: FamilyKey;
  version: string;
} | null;

type CandidateFamily = {
  family: FamilyKey;
  versions: string[];
};

type Props = {
  onChange?: (value: { library: string; family: FamilyKey; version: string } | null) => void;
  apiBase?: string;
};

const familiesOrder: FamilyKey[] = ['cnn', 'lstm', 'cnn_lstm', 'cnn_lstm_attn'];

export default function ActiveModelCard({ onChange, apiBase }: Props) {
  const API = useMemo(
    () => (apiBase || process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, ''),
    [apiBase]
  );

  // form state
  const [libraries, setLibraries] = useState<LibraryDto[]>([]);
  const [libKey, setLibKey] = useState<string>('');
  const [candidates, setCandidates] = useState<CandidateFamily[]>([]);
  const [currentDefault, setCurrentDefault] = useState<DefaultDto>(null);
  const [family, setFamily] = useState<FamilyKey | ''>('');
  const [version, setVersion] = useState<string>('');

  // csrf + refresh + sync status
  const [csrf, setCsrf] = useState<string>('');
  const [refreshTick, setRefreshTick] = useState<number>(0);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncMsg, setSyncMsg] = useState<{ kind: 'success' | 'info' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetch(`${API}/users/csrf/`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { csrfToken: '' }))
      .then((d) => setCsrf(d?.csrfToken || ''));
  }, [API]);

  const selectedFamily = useMemo(
    () => candidates.find((f) => f.family === family) || null,
    [candidates, family]
  );
  const versionOptions = selectedFamily?.versions ?? [];

  // ----- helpers -----
  const safeOnChange = (payload: { library: string; family: FamilyKey; version: string } | null) => {
    if (typeof onChange === 'function') onChange(payload);
  };

  const resetSelection = () => {
    setFamily('');
    setVersion('');
    safeOnChange(null);
  };

  const flashMsg = (msg: { kind: 'success' | 'info' | 'error'; text: string }) => {
    setSyncMsg(msg);
    // auto-hide after 5s
    window.setTimeout(() => setSyncMsg(null), 5000);
  };

  // ----- fetch libraries once -----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API}/occupancy/libraries/`);
        if (!res.ok) throw new Error(`Libraries fetch failed (${res.status})`);
        const data: LibraryDto[] = await res.json();
        if (!cancelled) setLibraries(data);
      } catch (e) {
        console.error(e);
        if (!cancelled) setLibraries([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [API]);

  // ----- fetch candidates when library changes or refreshTick bumps -----
  useEffect(() => {
    if (!libKey) {
      setCandidates([]);
      setCurrentDefault(null);
      resetSelection();
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API}/occupancy/models/candidates?library=${encodeURIComponent(libKey)}`
        );
        if (!res.ok) throw new Error(`Candidates fetch failed (${res.status})`);
        const raw = await res.json();

        let families: CandidateFamily[] = [];
        let current_default: DefaultDto = null;
        let library = libKey;

        if (Array.isArray(raw)) {
          const grouped: Record<string, string[]> = {};
          for (const c of raw) {
            if (!grouped[c.family]) grouped[c.family] = [];
            grouped[c.family].push(c.version);
          }
          families = Object.entries(grouped).map(([fam, versions]) => ({
            family: fam as FamilyKey,
            versions,
          }));
        } else if (raw && Array.isArray(raw.families)) {
          families = raw.families;
          current_default = raw.current_default ?? null;
          library = raw.library ?? libKey;
        } else {
          throw new Error('Unexpected response format');
        }

        const sorted = [...families].sort(
          (a, b) => familiesOrder.indexOf(a.family) - familiesOrder.indexOf(b.family)
        );

        if (!cancelled) {
          setCandidates(sorted);
          setCurrentDefault(current_default ?? null);

          if (current_default) {
            setFamily(current_default.family);
            setVersion(current_default.version);
            safeOnChange({
              library: library,
              family: current_default.family,
              version: current_default.version,
            });
          } else if (sorted.length) {
            const f = sorted[0].family;
            const v = sorted[0].versions?.[0] || '';
            setFamily(f);
            setVersion(v);
            if (f && v) safeOnChange({ library: library, family: f, version: v });
          } else {
            resetSelection();
          }
        }
      } catch (e) {
        console.error(e);
        if (!cancelled) {
          setCandidates([]);
          setCurrentDefault(null);
          resetSelection();
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API, libKey, refreshTick]);

  // ----- propagate changes upward -----
  useEffect(() => {
    if (!libKey || !family || !version) return;
    safeOnChange({ library: libKey, family, version });
  }, [libKey, family, version]); // eslint-disable-line react-hooks/exhaustive-deps

  // ----- actions -----
  const setAsDefault = async () => {
    if (!libKey || !family || !version) return;
    try {
      const res = await fetch(`${API}/occupancy/models/active/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ library: libKey, family, version }),
      });
      if (!res.ok) throw new Error(`Failed to set default (${res.status})`);
      setCurrentDefault({ family, version });
    } catch (e) {
      console.error(e);
    }
  };

  const syncModels = async () => {
    try {
      setSyncing(true);
      const res = await fetch(`${API}/occupancy/models/sync/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrf ? { 'X-CSRFToken': csrf } : {}),
        },
        credentials: 'include',
      });

      interface SyncResponse{
        created?: number;
        detail?: string;
      }

      // try to read the JSON even when !ok (backend may still return details)
      const data: SyncResponse = await res.json().catch(() => ({} as SyncResponse));

      if (!res.ok) {
        throw new Error(data?.detail || `Sync failed (${res.status})`);
      }

      const created = Number(data?.created ?? 0);
      if (created > 0) {
        flashMsg({ kind: 'success', text: `Synced ${created} new model${created === 1 ? '' : 's'}.` });
      } else {
        flashMsg({ kind: 'info', text: 'Models already in sync (0 added).' });
      }

      // re-fetch candidates for current library
      setRefreshTick((t) => t + 1);
      console.log('Sync complete', data);
    } catch (e) {
      const errorMessage =
      e instanceof Error ? e.message : 'Unexpected error during sync.';
      console.error(e);
      flashMsg({ kind: 'error', text: errorMessage });
    } finally {
      setSyncing(false);
    }
  };

  // banner ui
  const banner =
    syncMsg &&
    ({
      success: 'bg-green-50 text-green-800 border-green-200',
      info: 'bg-blue-50 text-blue-800 border-blue-200',
      error: 'bg-red-50 text-red-800 border-red-200',
    } as const)[syncMsg.kind];

  return (
    <div className="w-full rounded-2xl bg-white p-6 shadow">
      {/* Sync status banner */}
      {syncMsg && (
        <div
          className={`mb-4 rounded-xl border px-4 py-3 text-sm ${banner}`}
          role="status"
          aria-live="polite"
        >
          {syncMsg.text}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Library */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium">Library</label>
          <select
            className="rounded-lg border px-3 py-2"
            value={libKey}
            onChange={(e) => setLibKey(e.target.value)}
          >
            <option value="">Choose a library</option>
            {libraries.map((l) => (
              <option key={l.key} value={l.key}>
                {l.title || l.key}
              </option>
            ))}
          </select>
        </div>

        {/* Family */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium">Model family</label>
          <select
            className="rounded-lg border px-3 py-2"
            value={family}
            onChange={(e) => {
              const next = e.target.value as FamilyKey | '';
              setFamily(next);
              const first = candidates.find((c) => c.family === next)?.versions?.[0] || '';
              setVersion(first);
            }}
            disabled={!libKey || candidates.length === 0}
          >
            {(!libKey || candidates.length === 0) && <option>No candidates</option>}
            {candidates.map((f) => (
              <option key={f.family} value={f.family}>
                {f.family}
              </option>
            ))}
          </select>
        </div>

        {/* Version */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium">Version</label>
          <select
            className="rounded-lg border px-3 py-2"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            disabled={!family || versionOptions.length === 0}
          >
            {(!family || versionOptions.length === 0) && <option>No versions</option>}
            {versionOptions.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-3 text-sm">
        Current student default:{' '}
        {currentDefault ? (
          <span className="font-medium">
            {currentDefault.family} / {currentDefault.version}
          </span>
        ) : (
          <span className="italic text-gray-500">None</span>
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <button
          onClick={syncModels}
          disabled={syncing}
          className="w-full rounded-xl border border-gray-300 px-4 py-3 font-semibold text-[#0F172A] disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer"
        >
          {syncing ? 'Syncing…' : 'Sync Models from Artifacts'}
        </button>

        <button
          onClick={setAsDefault}
          disabled={!libKey || !family || !version}
          className="w-full rounded-xl bg-[#FBC02D] px-4 py-3 font-semibold text-[#0F172A] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Set as Student Default
        </button>
      </div>
    </div>
  );
}
