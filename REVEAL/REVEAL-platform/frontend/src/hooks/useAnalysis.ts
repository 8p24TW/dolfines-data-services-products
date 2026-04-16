import useSWRMutation from "swr/mutation";
import { api } from "@/lib/api";
import type { AnalysisResult, ColumnDetectionResult } from "@/types/analysis";

export function useAnalysisRun() {
  return useSWRMutation<AnalysisResult, Error, string, FormData>(
    "analysis/run",
    (_, { arg: form }) => api.analysis.run(form)
  );
}

export function useColumnDetect() {
  return useSWRMutation<ColumnDetectionResult, Error, string, FormData>(
    "analysis/detect-columns",
    (_, { arg: form }) => api.analysis.detectColumns(form)
  );
}
