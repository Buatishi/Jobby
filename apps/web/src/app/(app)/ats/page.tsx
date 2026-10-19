import { PageBanner } from "@/components/page-banner";

import { AtsJobList } from "./ats-job-list";

export default function AtsPage() {
  return (
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        description="Los reportes ATS se generan desde un puesto analizado."
        eyebrow="ATS Analyzer"
        title="ATS"
      />

      <AtsJobList />
    </main>
  );
}
