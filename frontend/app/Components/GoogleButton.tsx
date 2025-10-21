// app/Components/GoogleButton.tsx
"use client";

declare global {
  interface Window {
    google?: unknown;
  }
}

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export default function GoogleButton() {
  const loginUrl = new URL("/accounts/google/login/", API_BASE);
  loginUrl.searchParams.set("process", "login");

  return (
    <a
      href={loginUrl.toString()}
      className="group inline-flex w-full items-center justify-center gap-3 rounded-xl bg-[#1a2b8a] px-5 py-3 text-sm font-semibold text-white shadow-lg ring-1 ring-white/10 hover:-translate-y-[1px] hover:bg-[#1b34b8]"
    >
      <GoogleMark className="h-4 w-4" />
      Login with Google
    </a>
  );
}

function GoogleMark(props: React.SVGProps<SVGSVGElement>) {

  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" {...props}>
      <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303C33.602 32.991 29.147 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.957 3.043l5.657-5.657C34.046 6.053 29.268 4 24 4 12.954 4 4 12.954 4 24s8.954 20 20 20c10.493 0 19.152-7.594 19.152-20 0-1.341-.147-2.651-.541-3.917z"/>
      <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.328 16.163 18.79 12 24 12c3.059 0 5.842 1.154 7.957 3.043l5.657-5.657C34.046 6.053 29.268 4 24 4 15.798 4 8.741 8.337 6.306 14.691z"/>
      <path fill="#4CAF50" d="M24 44c5.087 0 9.787-1.944 13.317-5.146l-6.148-5.2C29.151 35.915 26.681 36.9 24 36c-5.132 0-9.574-3-11.286-7.234l-6.56 5.048C8.548 39.556 15.676 44 24 44z"/>
      <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-1.342 4.011-5.509 6.917-11.303 6.917 0 0 0 0 0 0-5.132 0-9.574-3-11.286-7.234l-6.56 5.048C8.548 39.556 15.676 44 24 44c10.493 0 19.152-7.594 19.152-20 0-1.341-.147-2.651-.541-3.917z"/>
    </svg>
  );
}