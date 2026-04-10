/**
 * TARS API Service (v2 schema)
 * Shared fetch helpers and TypeScript interfaces for all dashboard pages.
 * All requests proxy through Vite dev server to Flask at localhost:5001.
 */

// ─── QA Dashboard Types ──────────────────────────────────────────────────────

export type QAStatus = 'not_tested' | 'reproduced' | 'escalated';

export interface QATicket {
  _id: string;
  ticket_number: number;
  supportpal_id: number;
  subject: string;
  qa_feature_area: string;
  qa_platform: string;
  qa_error_pattern: string;
  qa_status: QAStatus;
  created_at: string;
}

export interface QATicketsResponse {
  count: number;
  tickets: QATicket[];
}

export interface QAStatsResponse {
  period_days: number;
  total_bugs: number;
  not_tested: number;
  reproduced: number;
  escalated: number;
  dismissed: number;
  by_platform: Record<string, number>;
}

// ─── Existing Types (for Daily Runs + Sentiment pages) ───────────────────────

export interface CategoryBreakdown {
  title: string;
  count: number;
  summary: string;
}

export interface NewTrend {
  title: string;
  count: number;
  description: string;
  geographic_pattern: string | null;
}

export interface AiUsage {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  finish_reason: string;
}

export interface Analysis {
  _id: string;
  run_date: string;
  period_hours: number;
  brand_id: number | null;
  total_tickets: number;
  categories: Record<string, CategoryBreakdown>;
  new_trends: NewTrend[];
  ai_usage: AiUsage | null;
  schema_version: string;
}

export interface Ticket {
  _id: string;
  analysis_id: string;
  ticket_number: number;
  supportpal_id: number;
  subject: string;
  message_snippet: string;
  ai_summary: string;
  category_id: string | null;
  is_new_trend: boolean;
  trend_title: string | null;
  status: string;
  priority: string;
  brand_id: number | null;
  supportpal_created_at: string | null;
  created_at: string;
}

export interface StatsResponse {
  latest_analysis: {
    date: string | null;
    tickets: number;
    categories: number;
    top_category: { category_id: string; title: string; count: number } | null;
  } | null;
  today_analyses: number;
  total_analyses: number;
  last_7_days_tickets: number;
}

export interface SentimentResponse {
  period_days: number;
  total_scored: number;
  sentiment: Record<string, number>;
  urgency: Record<string, number>;
  churn_risk: Record<string, number>;
  high_churn_tickets: Array<{
    ticket_number: number;
    subject: string;
    sentiment_summary: string;
    sentiment: string;
    urgency: string;
  }>;
}

export interface TriggerAnalysisResponse {
  status: 'success' | 'error';
  message: string;
}

// ─── Base ─────────────────────────────────────────────────────────────────────

const BASE = '';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status} on PATCH ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status} on POST ${path}`);
  return res.json() as Promise<T>;
}

// ─── QA Dashboard Endpoints ──────────────────────────────────────────────────

export function fetchQATickets(
  days = 30,
  platform?: string,
  status?: string,
): Promise<QATicketsResponse> {
  let url = `/api/qa/tickets?days=${days}`;
  if (platform) url += `&platform=${platform}`;
  if (status) url += `&status=${status}`;
  return get<QATicketsResponse>(url);
}

export function fetchQAStats(days = 30): Promise<QAStatsResponse> {
  return get<QAStatsResponse>(`/api/qa/stats?days=${days}`);
}

export function updateQATicketStatus(
  ticketId: string,
  newStatus: QAStatus,
): Promise<{ status: string; qa_status: string }> {
  return patch(`/api/qa/tickets/${ticketId}/status`, { status: newStatus });
}

export function dismissQATicket(
  ticketId: string,
): Promise<{ status: string }> {
  return patch(`/api/qa/tickets/${ticketId}/dismiss`, {});
}

// ─── Existing Endpoints (Daily Runs, Sentiment, etc.) ────────────────────────

export function fetchStats(): Promise<StatsResponse> {
  return get<StatsResponse>('/api/stats');
}

export function fetchSentiment(days = 7): Promise<SentimentResponse> {
  return get<SentimentResponse>(`/api/sentiment?days=${days}`);
}

export function triggerAnalysis(hours = 24): Promise<TriggerAnalysisResponse> {
  return post<TriggerAnalysisResponse>('/analyze', { hours });
}

// ─── Constants ───────────────────────────────────────────────────────────────

export const SUPPORTPAL_BASE_URL = 'https://support.int.windscribe.com';

export function ticketUrl(supportpalId: number): string {
  return `${SUPPORTPAL_BASE_URL}/en/admin/ticket/view/${supportpalId}`;
}

export const PLATFORM_LABELS: Record<string, string> = {
  windows: 'Windows',
  macos: 'macOS',
  linux: 'Linux',
  android: 'Android',
  ios: 'iOS',
  router: 'Router',
  browser_extension: 'Browser Ext',
  tv: 'TV',
  unknown: 'Unknown',
};

export const FEATURE_AREA_LABELS: Record<string, string> = {
  connection_engine: 'Connection Engine',
  protocol_wireguard: 'WireGuard',
  protocol_ikev2: 'IKEv2',
  protocol_openvpn: 'OpenVPN',
  protocol_stealth: 'Stealth',
  protocol_amnezia: 'AmneziaWG',
  app_crash: 'App Crash',
  app_ui: 'UI/UX',
  localization: 'Localization',
  look_and_feel: 'Look & Feel',
  dns_robert: 'DNS/ROBERT',
  split_tunneling: 'Split Tunneling',
  allow_lan_traffic: 'LAN Traffic',
  authentication: 'Auth',
  billing_app_bugs: 'Billing',
  static_ip_app_issues: 'Static IP',
  config_generation: 'Config Gen',
  other: 'Other',
};
