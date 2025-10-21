"use client";

import { motion } from "framer-motion";

export default function LoadingScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-[var(--color-addu-mist)] text-[var(--color-addu-ink)] relative overflow-hidden">
      {/* Animated background blobs */}
      <motion.div
        className="absolute w-72 h-72 rounded-full bg-[var(--color-addu-indigo)] opacity-20 blur-3xl top-10 left-10"
        animate={{
          x: [0, 30, -30, 0],
          y: [0, -30, 30, 0],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute w-72 h-72 rounded-full bg-[var(--color-addu-yellow)] opacity-20 blur-3xl bottom-10 right-10"
        animate={{
          x: [0, -30, 30, 0],
          y: [0, 30, -30, 0],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Core loader */}
      <motion.div
        className="w-24 h-24 rounded-full bg-[var(--color-addu-royal)] flex items-center justify-center shadow-lg"
        animate={{
          rotate: [0, 360],
        }}
        transition={{
          duration: 2.8,
          repeat: Infinity,
          ease: "linear",
        }}
      >
        <motion.div
          className="w-10 h-10 rounded-full bg-[var(--color-addu-gold)]"
          animate={{
            y: [0, -12, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 1.4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>

      {/* Text */}
      <motion.h1
        className="mt-10 text-[var(--color-addu-navy)] font-cinzel text-2xl tracking-wide"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        Loading...
      </motion.h1>

      <motion.p
        className="mt-2 text-[var(--color-addu-royal)] font-inter text-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.8 }}
      >
        Please wait a moment ✨
      </motion.p>
    </div>
  );
}
