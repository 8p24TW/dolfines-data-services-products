"use client";

import { useState, useEffect, useRef } from "react";
import type { ReportJob } from "@/types/report";

const API_BASE = "";
const MAX_RETRIES = 10;
const RETRY_DELAY_MS = 3000;

export function useReportJob(jobId: string | null) {
  const [job, setJob] = useState<ReportJob | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const doneRef = useRef(false);
  const retriesRef = useRef(0);

  useEffect(() => {
    if (!jobId) return;

    doneRef.current = false;
    retriesRef.current = 0;

    let retryTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (doneRef.current) return;

      const url = `${API_BASE}/api/reports/jobs/${jobId}/stream`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onmessage = (event) => {
        const data = JSON.parse(event.data) as ReportJob;
        setJob(data);
        retriesRef.current = 0; // reset retry counter on successful message
        if (data.status === "complete" || data.status === "error") {
          doneRef.current = true;
          es.close();
        }
      };

      es.onerror = () => {
        es.close();
        if (doneRef.current) return;
        if (retriesRef.current < MAX_RETRIES) {
          retriesRef.current += 1;
          retryTimeout = setTimeout(connect, RETRY_DELAY_MS);
        }
      };
    }

    connect();

    return () => {
      doneRef.current = true;
      if (retryTimeout) clearTimeout(retryTimeout);
      esRef.current?.close();
    };
  }, [jobId]);

  return job;
}
