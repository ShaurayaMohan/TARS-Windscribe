/**
 * TARS API Service (v2 schema)
 * Shared fetch helpers and TypeScript interfaces for all dashboard cards.
 * All requests proxy through Vite dev server to Flask at localhost:5001.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

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
  run_date: string;                                  // ISO datetime
  period_hours: number;
  brand_id: number | null;
  total_tickets: number;
  categories: Record<string, CategoryBreakdown>;     // keyed by category_id
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

export interface TopCategorySummary {
  category_id: string;
  title: string;
  count: number;
}

export interface LatestAnalysisSummary {
  date: string | null;
  tickets: number;
  categories: number;
  top_category: TopCategorySummary | null;
}

export interface StatsResponse {
  latest_analysis: LatestAnalysisSummary | null;
  today_analyses: number;
  total_analyses: number;
  last_7_days_tickets: number;
}

export interface DailyBreakdownEntry {
  tickets: number;
  categories: number;
  analyses: number;
}

export interface TopIssue {
  title: string;
  count: number;
}

export interface TrendsResponse {
  period_days: number;
  total_analyses: number;
  total_tickets: number;
  total_categories: number;
  avg_tickets_per_analysis: number;
  daily_breakdown: Record<string, DailyBreakdownEntry>;
  top_recurring_issues: TopIssue[];
}

export interface AnalysesResponse {
  count: number;
  analyses: Analysis[];
}

export interface TicketsResponse {
  count: number;
  tickets: Ticket[];
}

export interface TriggerAnalysisResponse {
  status: 'success' | 'error';
  message: string;
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

export interface QAClusterTicket {
  ticket_number: number;
  supportpal_id: number;
  subject: string;
  error_pattern: string;
}

export interface QACluster {
  platform: string;
  feature_area: string;
  count: number;
  tickets: QAClusterTicket[];
}

export interface QAResponse {
  period_days: number;
  total_bugs: number;
  clusters: QACluster[];
}

// ─── Base ─────────────────────────────────────────────────────────────────────

const BASE = '';  // Vite proxy forwards /api/* → http://localhost:5001

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status} on POST ${path}`);
  }
  return res.json() as Promise<T>;
}

// Some backends (e.g. mock-master) wrap singleton responses in an array.
function unwrapArray<T>(data: T | T[]): T {
  return Array.isArray(data) ? data[0] : data;
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

/** GET /api/stats — Dashboard summary statistics */
export async function fetchStats(): Promise<StatsResponse> {
  const raw = await get<StatsResponse | StatsResponse[]>('/api/stats');
  return unwrapArray(raw);
}

/** GET /api/analyses?limit=N — Most recent N analyses */
export function fetchAnalyses(limit = 50): Promise<AnalysesResponse> {
  return get<AnalysesResponse>(`/api/analyses?limit=${limit}`);
}

/** GET /api/trends?days=N — Trend data for charts */
export async function fetchTrends(days = 30): Promise<TrendsResponse> {
  const raw = await get<TrendsResponse | TrendsResponse[]>(`/api/trends?days=${days}`);
  return unwrapArray(raw);
}

/** GET /api/analyses/:id — Single analysis by MongoDB ID */
export async function fetchAnalysis(id: string): Promise<Analysis> {
  const raw = await get<Analysis | Analysis[]>(`/api/analyses/${id}`);
  return unwrapArray(raw);
}

/** GET /api/tickets?analysis_id=X — Tickets for a specific analysis run */
export function fetchTicketsByAnalysis(analysisId: string): Promise<TicketsResponse> {
  return get<TicketsResponse>(`/api/tickets?analysis_id=${analysisId}`);
}

/** GET /api/tickets?category_id=X&days=N — Tickets for a category */
export function fetchTicketsByCategory(categoryId: string, days = 30): Promise<TicketsResponse> {
  return get<TicketsResponse>(`/api/tickets?category_id=${categoryId}&days=${days}`);
}

/** GET /api/prompt — Returns the AI analysis prompt template */
export function fetchPrompt(): Promise<{ prompt: string; source?: string }> {
  return get<{ prompt: string; source?: string }>('/api/prompt');
}

/** POST /api/prompt — Save a custom prompt template */
export function savePrompt(text: string): Promise<{ status: string }> {
  return post<{ status: string }>('/api/prompt', { prompt: text });
}

/** GET /api/sentiment?days=N — Aggregated sentiment stats */
export async function fetchSentiment(days = 7): Promise<SentimentResponse> {
  const raw = await get<SentimentResponse | SentimentResponse[]>(`/api/sentiment?days=${days}`);
  return unwrapArray(raw);
}

/** GET /api/qa?days=N&min_count=M — Aggregated QA cluster data */
export async function fetchQAClusters(days = 7, minCount = 3): Promise<QAResponse> {
  const raw = await get<QAResponse | QAResponse[]>(`/api/qa?days=${days}&min_count=${minCount}`);
  return unwrapArray(raw);
}

/** POST /analyze — Manually trigger a new analysis run */
export async function triggerAnalysis(hours = 24): Promise<TriggerAnalysisResponse> {
  const res = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hours }),
  });
  return res.json() as Promise<TriggerAnalysisResponse>;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format an ISO datetime string as a relative time string.
 * e.g. "3 min ago", "2 hours ago", "Yesterday"
 */
export function timeAgo(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? 's' : ''} ago`;
  if (diffDay === 1) return 'yesterday';
  return `${diffDay} days ago`;
}

/** Get sorted category entries from an Analysis, by count descending */
export function sortedCategories(analysis: Analysis): Array<{ id: string } & CategoryBreakdown> {
  return Object.entries(analysis.categories)
    .map(([id, data]) => ({ id, ...data }))
    .sort((a, b) => b.count - a.count);
}
