"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState("checking…");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main className="mx-auto max-w-2xl p-10">
      <h1 className="text-3xl font-semibold">AI Mock Interview Coach</h1>
      <p className="mt-4 text-neutral-500">API status: {status}</p>
    </main>
  );
}
