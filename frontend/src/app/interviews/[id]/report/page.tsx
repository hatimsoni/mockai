import { Suspense } from "react";
import { Spinner } from "@/components/ui";
import { ReportView } from "./ReportView";

export default function ReportPage() {
  return (
    <Suspense fallback={<Spinner label="Loading report…" />}>
      <ReportView />
    </Suspense>
  );
}
