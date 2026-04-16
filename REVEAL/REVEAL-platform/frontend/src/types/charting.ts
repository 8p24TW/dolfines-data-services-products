export interface ChartingSeriesConfig {
  column: string;
  label: string;
  unit?: string;
  chartType: "line" | "bar";
  color: string;
  yAxis: "left" | "right";
  sourceColumn?: string;
  derivedMetric?: "specific_yield";
  capacityKwp?: number;
}

export interface ChartingResultRow {
  timestamp: string;
  [key: string]: string | number | null;
}

export interface ChartingResult {
  series: ChartingSeriesConfig[];
  rows: ChartingResultRow[];
  summary: {
    filename: string;
    worksheet?: string | null;
    rowCount: number;
    aggregation: "raw" | "hourly" | "daily" | "monthly" | string;
    dateRange: [string, string];
  };
}

export interface ChartingDateRangeResult {
  timeColumn: string;
  worksheet?: string | null;
  dateRange: [string, string];
  rowCount: number;
}

export interface ChartingReferenceIrradianceResult {
  source: string;
  label: string;
  unit: string;
  mode: string;
  rows: Array<{
    timestamp: string;
    reference_irradiance_era5_land: number | null;
  }>;
  summary: {
    rowCount: number;
    aggregation: "raw" | "hourly" | "daily" | "monthly" | string;
    dateRange: [string, string];
  };
}
