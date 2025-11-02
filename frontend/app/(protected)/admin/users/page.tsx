"use client";

import AdminShell from "../../../Components/AdminShell";
import { Card } from "../../../Components/Card";
import AdminUsersTable from "@/app/Components/AdminUsersTable";

export default function AdminUsersPage() {
  return (
    <AdminShell>
      <Card title="User Management">
        <AdminUsersTable />
      </Card>
    </AdminShell>
  );
}
