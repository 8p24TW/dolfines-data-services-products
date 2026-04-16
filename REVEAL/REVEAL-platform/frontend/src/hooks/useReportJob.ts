"use client";

import { useState, useEffect, useRef } from "react";
import type { ReportJob } from "@/types/report";

const API_BASE = "";

export function useReportJob(jobId: string | null) {
  const [job, setJob] = useState<ReportJob | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const url = `${API_BASE}/api/reports/jobs/${jobId}/stream`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (event) => {
      const data = JSON.parse(event.data) as ReportJob;
      setJob(data);
      if (data.status === "complete" || data.status === "error") {
        es.close();
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  return job;
}
