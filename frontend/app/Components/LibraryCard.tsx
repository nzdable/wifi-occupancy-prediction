"use client";

import React from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

type LibraryCardProps = {
  name: string;
  occupancy: number; // value between 0–100
};

export default function LibraryCard({ name, occupancy }: LibraryCardProps) {
  // Determine color based on occupancy percentage
  const getColor = (value: number) => {
    if (value < 40) return "#22c55e"; // green
    if (value < 70) return "#eab308"; // yellow
    return "#ef4444"; // red
  };

  const color = getColor(occupancy);

  const data = {
    labels: ["Occupied", "Available"],
    datasets: [
      {
        data: [occupancy, 100 - occupancy],
        backgroundColor: [color, "#E5E7EB"], // active + gray remainder
        borderWidth: 0,
      },
    ],
  };

  const options = {
    cutout: "75%", // controls how hollow the donut looks
    plugins: {
      tooltip: { enabled: false },
      legend: { display: false },
    },
  };

  return (
    <div className="flex flex-col justify-between items-center bg-[#0D1B5E] text-center rounded-2xl shadow-lg p-6 w-full max-w-sm transition-transform transform hover:scale-[1.02] hover:shadow-xl">
      {/* Library Name */}
      <h2 className="font-cinzel text-xl font-semibold mb-4">{name}</h2>

      {/* Doughnut Chart */}
      <div className="relative w-40 h-40 mb-4">
        <Doughnut data={data} options={options} />
        {/* Percentage overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{occupancy}%</span>
        </div>
      </div>

      {/* Status label */}
      <p className="text-sm text-gray-300">
        Crowd Level:{" "}
        <span className="font-semibold" style={{ color }}>
          {occupancy < 40
            ? "Low"
            : occupancy < 70
            ? "Moderate"
            : "High"}
        </span>
      </p>
    </div>
  );
}
