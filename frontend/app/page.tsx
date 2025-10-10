"use client";

import Image from "next/image";
import Link from "next/link";
import GoogleButton from "./Components/GoogleButton";

export default function Home() {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <Image
          src="/Library.jpg"
          alt="Ateneo de Davao University Library"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#030B3A]/90 via-[#030B3A]/80 to-[#030B3A]/95" />
      </div>

      {/* Card */}
      <section className="mx-4 w-full max-w-md">
        <div className="rounded-3xl bg-white/95 p-8 text-slate-900 shadow-2xl ring-1 ring-black/5 backdrop-blur-md">
          <div className="flex justify-center mb-4">
            <Image
              src="/AdDUSeal.png"
              alt="AdDU Seal"
              width={120}
              height={120}
              className="h-auto w-24 md:w-28 lg:w-32 object-contain"
            />
          </div>
          <h1 className="mt-1 text-center text-[1.2rem] font-extrabold tracking-[0.18em] text-slate-700 font-cinzel">
            ATENEO DE DAVAO
            <br />
            <span className="text-slate-800 font-cinzel">UNIVERSITY</span>
          </h1>
          <p className="mt-2 text-center text-xs font-medium uppercase tracking-wide text-slate-500 text-openSans">
            Library Occupancy System
          </p>

          <p className="mt-6 text-center text-sm leading-6 text-slate-600 text-inter">
            Find the perfect time to study with
            <br /> real-time occupancy data and AI-powered predictions
          </p>

          <div className="mt-8 text-inter">
            <GoogleButton href="/api/auth/signin">Login with Google</GoogleButton>
          </div>
        </div>
      </section>
    </main>
  );
}
