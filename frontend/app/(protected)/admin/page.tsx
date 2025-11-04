"use client";

import AdminShell from "../../Components/AdminShell";
import { Card } from "../../Components/Card";
import UploadCsvPanel from "../../Components/UploadCsvPanel";
import ActiveModelCard from "@/app/Components/ActiveModelCard";

export default function AdminInsightsPage() {
  return (
    <AdminShell>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Upload CSV">
          <UploadCsvPanel />
        </Card>

        <Card title="Student View Model (Default)">
          <ActiveModelCard/>
        </Card>

        <Card title="Insights">
          {/* Replace with real charts later */}
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-16 text-center text-sm text-gray-600">
            Graphs / KPIs placeholder
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}
