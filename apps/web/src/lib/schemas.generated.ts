/* Generated from packages/schemas by npm run gen:types. Do not edit. */

/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "Badge".
 */
export type Badge = "primary_data" | "news_reported" | "verified" | "attributed_view" | "single_source" | "withheld";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "ClaimType".
 */
export type ClaimType = "market_number" | "news_event" | "forecast" | "opinion";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "EvidenceKind".
 */
export type EvidenceKind = "feed" | "article";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "SourceTier".
 */
export type SourceTier = "T1" | "T2" | "T3" | "TX";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "Verdict".
 */
export type Verdict = "publish" | "withhold";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "ReportType".
 */
export type ReportType = "morning" | "midday" | "eod" | "flows";
/**
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "SourceKind".
 */
export type SourceKind = "rss" | "api" | "search" | "manual";

export interface Citebell {
  [k: string]: unknown;
}
/**
 * An atomic statement pulled from a draft, with the evidence gathered for it.
 *
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "Claim".
 */
export interface Claim {
  id: string;
  claim_type: ClaimType;
  text: string;
  field?: string | null;
  unit?: string | null;
  value?: string | null;
  as_of?: string | null;
  attributed_to?: string | null;
  evidence?: Evidence[];
}
/**
 * One piece of support for a claim: a feed value or an article that states it.
 *
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "Evidence".
 */
export interface Evidence {
  kind: EvidenceKind;
  source_id: string;
  tier: SourceTier;
  url?: string | null;
  syndication_group?: string | null;
  published_at?: string | null;
  fetched_at: string;
  http_status?: number | null;
  quote?: string | null;
  quote_found?: boolean;
  value?: string | null;
  as_of?: string | null;
}
/**
 * The publish gate's verdict for one claim. Reasons are written to the audit log.
 *
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "GateDecision".
 */
export interface GateDecision {
  claim_id: string;
  verdict: Verdict;
  badge: Badge;
  independent_sources?: number;
  reasons?: string[];
}
/**
 * Identifies a report run, so a retry never publishes twice (PRD §8.11).
 *
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "RunKey".
 */
export interface RunKey {
  report_type: ReportType;
  trading_date: string;
  version?: number;
}
/**
 * One entry in the source registry (the registry itself lives in the private config repo).
 *
 * This interface was referenced by `Citebell`'s JSON-Schema
 * via the `definition` "Source".
 */
export interface Source {
  id: string;
  name: string;
  domain: string;
  tier: SourceTier;
  kind: SourceKind;
  url?: string | null;
  active?: boolean;
}
