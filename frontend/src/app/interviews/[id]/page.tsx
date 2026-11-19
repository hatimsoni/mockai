import { Suspense } from "react";
import { Spinner } from "@/components/ui";
import { InterviewRoom } from "./InterviewRoom";

// Server component shell. The interactive room is a client component that reads the
// id with useParams(); with Cache Components on, that must sit inside <Suspense>.
export default function InterviewPage() {
  return (
    <Suspense fallback={<Spinner label="Loading interview…" />}>
      <InterviewRoom />
    </Suspense>
  );
}
