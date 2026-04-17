import useSWRMutation from "swr/mutation";
import { detectColumns, runAnalysis } from "@/lib/python-client";
import type { AnalysisResult, ColumnDetectionResult } from "@/types/analysis";
import type { Site } from "@/types/site";

interface DetectArgs {
  file: File;
  siteType: string;
  worksheet?: string;
}

interface RunArgs {
  files: File[];
  site: Site;
  columnMappings: Record<string, unknown>;
  siteConfigOverrides: Record<string, unknown>;
  lang?: string;
}

export function useAnalysisRun() {
  return useSWRMutation<AnalysisResult, Error, string, RunArgs>(
    "analysis/run",
    (_, { arg }) =>
      runAnalysis(arg.files, arg.site, arg.columnMappings, arg.siteConfigOverrides, arg.lang)
  );
}

export function useColumnDetect() {
  return useSWRMutation<ColumnDetectionResult, Error, string, DetectArgs>(
    "analysis/detect-columns",
    (_, { arg }) => detectColumns(arg.file, arg.siteType, arg.worksheet)
  );
}
