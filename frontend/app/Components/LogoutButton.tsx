"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export default function LogoutButton() {
  return (
    <button
      onClick={() => (window.location.href = `${API_URL}/accounts/logout/`)}
      className="mt-6 rounded-xl bg-red-600 px-5 py-2 font-semibold text-white shadow-lg hover:bg-red-700 cursor-pointer"
    >
      Logout
    </button>
  );
}
