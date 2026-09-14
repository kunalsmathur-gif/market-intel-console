import type { ReportType } from "./schemas.generated";

// Display copy for the four daily reports. The worker's schedule.py is the source of truth for timing.
export const REPORTS: readonly { type: ReportType; title: string; readyBy: string }[] = [
  { type: "morning", title: "Morning Insights", readyBy: "08:45" },
  { type: "midday", title: "Mid-day Markets", readyBy: "12:15" },
  { type: "eod", title: "End-of-day Insights", readyBy: "16:00" },
  { type: "flows", title: "Institutional Flows", readyBy: "20:00" },
];

export type PublishedReport = {
  report_type: ReportType;
  trading_date: string;
  version: number;
  title: string;
  published_at: string;
};

export function todayInIst(now = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(now);
}

export function formatIstTime(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}
