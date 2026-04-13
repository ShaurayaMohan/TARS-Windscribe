# TARS Dashboard — Claude Code Build Prompt

## Context

TARS is a ticket analysis system for Windscribe VPN. The dashboard lives at `dashboard/` and is a React 19 + Vite 7 + Tailwind v4 + TypeScript app. The backend is Flask, proxied via Vite at `http://localhost:5001`.

The previous dashboard has been gutted. All old components are deleted. You are building fresh.

**Do NOT touch any files outside `dashboard/src/`.** The backend, `vite.config.ts`, `package.json`, and `postcss.config.js` are already set up.

## What to Build

Build the **QA page** of the TARS dashboard. This is the first of three tabs (Daily Runs, QA, Sentiment) — only the QA tab needs to be functional now. The other two tabs should exist in the navigation but show a "Coming Soon" placeholder.

## Tech Stack (already installed)

- React 19, TypeScript, Tailwind v4
- `react-icons` for icons
- No router needed — use simple state-based tab switching

## Theme — Windscribe Dark

Reference: dark cyberpunk/terminal aesthetic. Think dark navy background with green/teal accent.

**Color Palette:**
- Background: `#0a0f1a`
- Card background: `#111827` with border `#1e2a3a`
- Primary accent: `#00d09c` (Windscribe green)
- Dimmer accent: `#0ecb81`
- Text primary: `#e5e7eb`
- Text muted: `#9ca3af`
- Status colors:
  - not_tested: `#6b7280` (gray)
  - reproduced: `#f59e0b` (amber)
  - escalated: `#ef4444` (red)

**Typography:**
- Headers/branding: monospace font (`font-mono` in Tailwind)
- Body: system default sans-serif

**Cards:** Use `glass-card` utility class (already defined in `index.css`):
```css
.glass-card {
  background: rgba(17, 24, 39, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(30, 42, 58, 0.8);
}
```

## Layout

```
+--------------------------------------------------------------+
| [Daily Runs] [QA] [Sentiment]              T.A.R.S  [logo]  |
+--------------------------------------------------------------+
|                                                                |
|  [Total Bugs]  [Not Tested]  [Reproduced]  [Escalated]       |
|     card           card           card          card           |
|                                                                |
|  Platform filter: [All ▼]    Status filter: [All] [NT] [R] [E]|
|                                                                |
|  +----+-------------------+-----------+----------+-----------+ |
|  | #  | Description       | Platform  | Status   | Actions   | |
|  +----+-------------------+-----------+----------+-----------+ |
|  |1234| WireGuard freeze  | Windows   | [dropdown]| [Delete] | |
|  |5678| DNS leak ROBERT   | Android   | [dropdown]| [Delete] | |
|  +----+-------------------+-----------+----------+-----------+ |
|                                                                |
+--------------------------------------------------------------+
```

## Component Structure

Create these files in `dashboard/src/components/`:

### `TabNav.tsx`
- Horizontal tab bar with three tabs: "Daily Runs", "QA", "Sentiment"
- Active tab gets green underline accent (`#00d09c`)
- Right side: "T.A.R.S" text in monospace with a small green dot indicator

### `QAPage.tsx`
- Main QA page container
- Fetches data from `fetchQAStats()` and `fetchQATickets()` on mount
- Contains `StatsCards` and `TicketTable`
- Handles re-fetching when filters change or when a ticket is updated/dismissed

### `StatsCards.tsx`
- Row of 4 stat cards: Total Bugs, Not Tested, Reproduced, Escalated
- Each card shows the count number large, with the label below
- Cards use the `glass-card` class with rounded corners
- The number should match the status color (gray for not_tested, amber for reproduced, red for escalated, green for total)

### `TicketTable.tsx`
- Table of QA tickets
- Above the table: platform filter dropdown + status filter pills
- Columns: Ticket #, Description (subject + error pattern), Feature Area, Platform, Status, Actions
- **Ticket # column**: The ticket number should be a hyperlink that opens in a new tab. Use the `ticketUrl()` helper from `api.ts` with the ticket's `supportpal_id`
- **Description column**: Show `subject` as primary text, and `qa_error_pattern` below in muted text
- **Feature Area column**: Show the human label from `FEATURE_AREA_LABELS` in `api.ts`
- **Platform column**: Show the human label from `PLATFORM_LABELS` in `api.ts`
- **Status column**: A small dropdown/select with three options (not_tested, reproduced, escalated). When changed, call `updateQATicketStatus(ticket._id, newStatus)`. Color-code the dropdown based on current status.
- **Actions column**: A delete/dismiss button (trash icon from react-icons). On click, show a confirmation dialog (NOT browser `confirm()` — use a custom modal). The modal says: "Are you sure you want to dismiss this ticket from QA tracking? This action hides the ticket from the QA board." Two buttons: "Cancel" and "Dismiss". On confirm, call `dismissQATicket(ticket._id)` and remove the row from the table.

### `DismissModal.tsx`
- Confirmation modal for dismissing tickets
- Dark overlay background
- Card with warning text, ticket subject shown, and Cancel/Dismiss buttons
- Dismiss button is red

### `PlaceholderPage.tsx`
- Simple "Coming Soon" centered text for Daily Runs and Sentiment tabs

## `App.tsx`

The root component should:
1. Manage the active tab state (`'daily_runs' | 'qa' | 'sentiment'`)
2. Render `TabNav` at the top
3. Render the appropriate page component based on active tab
4. Default to the QA tab

## API Contract

All API functions are already defined in `src/api.ts`. Import and use them directly. Do NOT create a new API file.

### Endpoints used by QA page:

**`fetchQAStats(days?: number)`** → `GET /api/qa/stats?days=30`
```json
{
  "period_days": 30,
  "total_bugs": 42,
  "not_tested": 28,
  "reproduced": 10,
  "escalated": 4,
  "dismissed": 3,
  "by_platform": { "windows": 15, "android": 12, "macos": 8, "ios": 7 }
}
```

**`fetchQATickets(days?, platform?, status?)`** → `GET /api/qa/tickets?days=30&platform=windows&status=not_tested`
```json
{
  "count": 28,
  "tickets": [
    {
      "_id": "6651a2b3...",
      "ticket_number": 9310221,
      "supportpal_id": 48201,
      "subject": "App freezes after connecting to WireGuard",
      "qa_feature_area": "protocol_wireguard",
      "qa_platform": "windows",
      "qa_error_pattern": "App UI freezes for 10s after WireGuard handshake on v2.8.1",
      "qa_status": "not_tested",
      "created_at": "2026-04-10T..."
    }
  ]
}
```

**`updateQATicketStatus(ticketId, newStatus)`** → `PATCH /api/qa/tickets/:id/status` body: `{"status": "reproduced"}`

**`dismissQATicket(ticketId)`** → `PATCH /api/qa/tickets/:id/dismiss`

**`ticketUrl(supportpalId)`** → returns `https://support.int.windscribe.com/en/admin/ticket/view/{supportpalId}`

**`PLATFORM_LABELS`** and **`FEATURE_AREA_LABELS`** — maps from API values to human-readable labels. Already in `api.ts`.

## Important Notes

1. All API functions are already in `src/api.ts`. Just import them.
2. The Vite proxy is already configured in `vite.config.ts` — requests to `/api/*` go to Flask on port 5001.
3. `index.css` already has Tailwind imported and the Windscribe theme variables. Don't replace it.
4. Use `react-icons/hi2` (Heroicons 2) for icons — it's already installed via `react-icons`.
5. Keep the code clean and minimal. No excessive comments. No over-engineering.
6. The delete/dismiss action MUST have a custom modal confirmation (double verification). Not a browser `confirm()`.
7. Make the table responsive — on smaller screens, consider horizontal scroll.
8. Empty state: if no tickets, show a centered message "No QA tickets found for this period."
9. Loading state: show a simple loading indicator while data is being fetched.
10. When a status is updated or a ticket is dismissed, optimistically update the UI (remove from list / change status) and then refetch stats to keep counts in sync.

---

# Sentiment Dashboard Page

## What to Build

Build the **Sentiment** tab of the TARS dashboard. The QA tab already exists and is functional. Now the "Sentiment" tab (currently showing "Coming Soon") should be replaced with a fully working Sentiment page. **Do not modify the QA page or TabNav — only add/change what's needed for the Sentiment tab.**

## Additional Dependencies

- `recharts` — already installed. Use it for the donut charts.

## Layout

```
+--------------------------------------------------------------+
| [Daily Runs] [QA] [Sentiment]              T.A.R.S           |
+--------------------------------------------------------------+
| Customer Health Score: 72/100 ████████░░ "Stable" [?]        |
+--------------------------------------------------------------+
| [Total Scored] [Positive %] [Frustrated+Angry %] [High Churn]|
|     card            card            card             card      |
+--------------------------------------------------------------+
| [Sentiment Donut]   [Urgency Donut]    [Churn Risk Donut]    |
|  + legend below      + legend below     + legend below        |
+--------------------------------------------------------------+
| Filter: [All Sentiment ▼] [All Urgency ▼] [All Churn ▼]     |
| +------+-----------------------+-------+------+-------+----+ |
| | #    | Summary               | Sent. | Urg. | Churn | ->  | |
| | 1234 | WireGuard failing...  | frust | high | high  | [->]| |
| +------+-----------------------+-------+------+-------+----+ |
+--------------------------------------------------------------+
```

## Component Structure

Create these files in `dashboard/src/components/`:

### `SentimentPage.tsx`
- Main Sentiment page container
- Fetches data from `fetchSentiment(days)` and `fetchSentimentTickets(days, sentiment?, urgency?, churn_risk?)` on mount
- `days` defaults to 30
- Contains `HealthScore`, `StatsCards` (sentiment variant), `SentimentCharts`, and `SentimentTable`
- Re-fetches ticket list when any filter dropdown changes

### `HealthScore.tsx`
- Full-width bar at the top of the Sentiment page
- Shows: "Customer Health Score: **72** / 100" with a horizontal progress bar and the label ("Healthy" / "Stable" / "Concerning" / "Critical")
- Progress bar fill color:
  - `>= 80`: green (`#22c55e`)
  - `>= 60`: teal (`#00d09c`)
  - `>= 40`: amber (`#f59e0b`)
  - `< 40`: red (`#ef4444`)
- **`[?]` icon**: A small question-mark icon (use `HiQuestionMarkCircle` from `react-icons/hi2`) positioned next to the label. On hover/click, show a tooltip or popover with this text:

  > **How is this calculated?**
  >
  > Score = 100 − (sentiment penalty + urgency penalty + churn penalty)
  >
  > **Sentiment** (max 40 pts): positive 0, neutral/confused 10, frustrated 30, angry 40
  > **Urgency** (max 30 pts): low 0, medium 10, high 20, critical 30
  > **Churn risk** (max 30 pts): low 0, medium 15, high 30
  >
  > Each penalty is the weighted average across all scored tickets, scaled to its max.

- The tooltip should be a floating card with `glass-card` styling, positioned above or to the right. Dismiss on click-outside or second click.

### `SentimentCharts.tsx`
- Row of three donut charts side by side (use `recharts` `PieChart` + `Pie` + `Cell`)
- Each chart has a centered label showing the chart name
- **Chart 1 — Sentiment Distribution:**
  - Slices: positive (green `#22c55e`), neutral_confused (slate `#64748b`), frustrated (amber `#f59e0b`), angry (red `#ef4444`)
- **Chart 2 — Urgency Distribution:**
  - Slices: low (green `#22c55e`), medium (amber `#f59e0b`), high (orange `#f97316`), critical (red `#ef4444`)
- **Chart 3 — Churn Risk Distribution:**
  - Slices: low (green `#22c55e`), medium (amber `#f59e0b`), high (red `#ef4444`)
- Below each chart, show a legend with colored dots and labels with counts (e.g., "● Positive: 42")
- Use the color constants `SENTIMENT_COLORS`, `URGENCY_COLORS`, `CHURN_COLORS` from `api.ts`
- Charts should be responsive — on narrow screens, stack vertically

### `SentimentTable.tsx`
- Filterable ticket table for individual sentiment tickets
- **Filters** (above the table): Three dropdowns — Sentiment (All / Positive / Neutral·Confused / Frustrated / Angry), Urgency (All / Low / Medium / High / Critical), Churn Risk (All / Low / Medium / High)
- Use `SENTIMENT_LABELS`, `URGENCY_LABELS`, `CHURN_LABELS` from `api.ts` for display names
- **Columns**:
  - **Ticket #**: Hyperlinked to SupportPal using `ticketUrl(ticket.supportpal_id)`, opens new tab
  - **Summary**: `sentiment_summary` text, truncated to ~100 chars with ellipsis if longer
  - **Sentiment**: Colored badge/pill using `SENTIMENT_COLORS`
  - **Urgency**: Colored badge/pill using `URGENCY_COLORS`
  - **Churn**: Colored badge/pill using `CHURN_COLORS`
  - **Link**: External link icon that opens the SupportPal ticket
- When filters change, call `fetchSentimentTickets(days, sentiment, urgency, churn_risk)` with the selected values
- Empty state: "No sentiment tickets found for this period."
- Loading state: simple loading indicator

### Sentiment Stats Cards
- Reuse the same card style as QA (`glass-card`, same layout)
- Four cards:
  1. **Total Scored** — `total_scored` count, green accent
  2. **Positive %** — percentage of positive tickets, green text
  3. **Frustrated + Angry %** — combined percentage, amber/red text
  4. **High Churn** — count of `churn_risk.high`, red text

## API Contract

All API functions are already in `src/api.ts`. Import and use them directly.

### Endpoints used by Sentiment page:

**`fetchSentiment(days?: number)`** → `GET /api/sentiment?days=30`
```json
{
  "period_days": 30,
  "total_scored": 120,
  "sentiment": { "positive": 42, "neutral_confused": 50, "frustrated": 22, "angry": 6 },
  "urgency": { "low": 30, "medium": 45, "high": 35, "critical": 10 },
  "churn_risk": { "low": 55, "medium": 40, "high": 25 },
  "high_churn_tickets": [],
  "health_score": 72,
  "health_label": "Stable"
}
```

**`fetchSentimentTickets(days?, sentiment?, urgency?, churn_risk?)`** → `GET /api/sentiment/tickets?days=30&sentiment=frustrated&urgency=high`
```json
{
  "count": 22,
  "tickets": [
    {
      "_id": "6651a2b3...",
      "ticket_number": 9310221,
      "supportpal_id": 48201,
      "subject": "App freezes on WireGuard",
      "sentiment": "frustrated",
      "urgency": "high",
      "churn_risk": "high",
      "sentiment_summary": "WireGuard failing on all US East servers from school WiFi",
      "created_at": "2026-04-10T..."
    }
  ]
}
```

**`ticketUrl(supportpalId)`** → returns `https://support.int.windscribe.com/en/admin/ticket/view/{supportpalId}`

**Label & color constants** (all in `api.ts`): `SENTIMENT_LABELS`, `URGENCY_LABELS`, `CHURN_LABELS`, `SENTIMENT_COLORS`, `URGENCY_COLORS`, `CHURN_COLORS`.

## Important Notes for Sentiment Page

1. All API functions and type interfaces are already in `src/api.ts`. Just import them. Do NOT create new API files.
2. Use `recharts` for the donut charts. It's already installed.
3. The `[?]` tooltip for Health Score must be a custom floating card, NOT a browser `title` attribute. It should look native to the dark theme.
4. Keep the same Windscribe dark theme — all color variables and `glass-card` are already in `index.css`.
5. The Sentiment tab should be the default active tab after this build (change the default from `'qa'` to `'sentiment'` in `App.tsx`).
6. Badge/pill colors for sentiment, urgency, and churn should use the color maps from `api.ts` with semi-transparent backgrounds (e.g., `bg-opacity-20` equivalent).
7. The table needs horizontal scroll on narrow screens.
8. Loading and empty states are required for both the charts and the table.

---

# Daily Runs Page

## What to Build

Build the **Daily Runs** tab of the TARS dashboard. The QA and Sentiment tabs already exist and are functional. Now the "Daily Runs" tab (currently showing "Coming Soon") should be replaced with a fully working Daily Runs page. **Do not modify the QA or Sentiment pages — only add/change what's needed for the Daily Runs tab.**

## Layout

```
+--------------------------------------------------------------+
| [Daily Runs] [QA] [Sentiment]              T.A.R.S           |
+--------------------------------------------------------------+
| [Total Runs] [Today's Runs] [7-Day Tickets] [Latest Run]     |
|     card          card           card           card          |
+--------------------------------------------------------------+
| Run: [Apr 10, 2026 — 48 tickets ▼]       [Run Analysis Now]  |
+--------------------------------------------------------------+
| Categories (6)                | New Trends (2)                |
| ┌──────────────────────────┐  | ┌──────────────────────────┐  |
| │ VPN Connectivity    (12) │  | │ ▲ WireGuard handshake    │  |
| │ Account & Billing    (8) │  | │   failures on v2.8.1     │  |
| │ Protocol Issues      (6) │  | │   5 tickets · US East    │  |
| │ App Crashes          (4) │  | │                          │  |
| └──────────────────────────┘  | │ ▲ German locale missing  │  |
|                               | │   translations           │  |
|                               | └──────────────────────────┘  |
+--------------------------------------------------------------+
| Tickets from this run                                         |
| +------+---------------------+----------+--------+-----------+|
| | #    | AI Summary          | Category | Status | Link      ||
| | 9310 | WireGuard freeze... | VPN Conn | Open   | [->]      ||
| +------+---------------------+----------+--------+-----------+|
+--------------------------------------------------------------+
```

## Component Structure

Create these files in `dashboard/src/components/`:

### `DailyRunsPage.tsx`
- Main Daily Runs page container
- On mount, fetch `fetchStats()` and `fetchAnalyses(20)`
- Store `selectedAnalysisId` state — defaults to the first (latest) analysis from the list
- When `selectedAnalysisId` changes, fetch `fetchAnalysisTickets(selectedAnalysisId)` to load that run's tickets
- The selected `Analysis` object itself (with categories, trends) comes from the already-fetched analyses list — no extra API call needed
- Contains `RunStatsCards`, `RunSelector`, `RunDetail`, and `RunTicketTable`
- Re-fetches everything after a successful "Run Analysis Now"

### `RunStatsCards.tsx`
- Row of 4 stat cards (same pattern as `SentimentStats.tsx` — use `glass-card`, staggered animation, icon + label pill + large number)
- Cards:
  1. **Total Runs** — `stats.total_analyses`, accent `#00d09c` (green), icon `HiOutlinePlayCircle`
  2. **Today's Runs** — `stats.today_analyses`, accent `#0ecb81` (teal), icon `HiOutlineClock`
  3. **7-Day Tickets** — `stats.last_7_days_tickets`, accent `#f59e0b` (amber), icon `HiOutlineTicket`
  4. **Latest Run** — formatted date from `stats.latest_analysis.date` (e.g., "Apr 10, 2026"), accent `#9ca3af` (muted), icon `HiOutlineCalendarDays`. If `null`, show "No runs yet"
- Props: `stats: StatsResponse | null`, `loading: boolean`

### `RunSelector.tsx`
- Full-width row with two elements:
  - **Left**: A `<select>` dropdown listing all analyses. Each option shows: formatted date + " — " + ticket count + " tickets" (e.g., "Apr 10, 2026 — 48 tickets"). The value is the analysis `_id`.
  - **Right**: A "Run Analysis Now" button. Green background (`bg-ws-green`), white text, icon `HiOutlinePlay`. On click: call `triggerAnalysis(24)`, show a spinner while loading, and on success call the `onRunComplete` callback. On error, show the error message briefly.
- Props: `analyses: Analysis[]`, `selectedId: string`, `onSelect: (id: string) => void`, `onRunComplete: () => void`
- Style: `glass-card rounded-xl p-4`, flex between the select and button

### `RunDetail.tsx`
- Two-column layout (`grid grid-cols-1 md:grid-cols-2 gap-4`)
- **Left column — Categories**: A `glass-card` panel. Header: "Categories" with count in parentheses. Body: list of category rows sorted by `count` descending. Each row shows the category `title` on the left and `count` as a small pill/badge on the right with green accent. Category `summary` shown below the title in muted text, truncated to one line.
- **Right column — New Trends**: A `glass-card` panel. Header: "New Trends" with count. Body: list of trend cards. Each trend shows: an upward-arrow icon (`HiOutlineArrowTrendingUp`) in amber, the `title` in bold, `count` + " tickets" as a muted tag, `description` in muted text below. If `geographic_pattern` is non-null, show it as a small muted italic tag (e.g., "US East"). If no trends exist, show "No new trends detected" centered in muted text.
- Props: `analysis: Analysis | null`, `loading: boolean`
- Empty state: if `analysis` is null and not loading, show "Select a run to view details"

### `RunTicketTable.tsx`
- Table of tickets from the selected run. Same styling as `SentimentTable.tsx` (glass-card wrapper, horizontal scroll on narrow screens).
- **Columns**:
  - **Ticket #**: Hyperlinked to SupportPal using `ticketUrl(ticket.supportpal_id)`, opens new tab. Green monospace text.
  - **AI Summary**: `ai_summary` text, truncated to ~120 chars with ellipsis
  - **Category**: The `category_id` value, displayed as-is (these are human-readable titles like "VPN Connectivity")
  - **Status**: Small colored badge. Map status values: use green for "open"/"active", amber for "pending", muted for others
  - **Link**: External link icon (`HiOutlineArrowTopRightOnSquare`)
- Loading state: spinner with "Loading tickets..."
- Empty state: "No tickets found for this run."
- Props: `tickets: Ticket[]`, `loading: boolean`

## App.tsx Changes

- Change the default active tab to `'daily_runs'` (from `'sentiment'`)
- Replace `<PlaceholderPage title="Daily Runs" />` with `<DailyRunsPage />`
- Import `DailyRunsPage` from `./components/DailyRunsPage`

## API Contract

All API functions are already in `src/api.ts`. Import and use them directly.

### Endpoints used by Daily Runs page:

**`fetchStats()`** → `GET /api/stats`
```json
{
  "latest_analysis": {
    "date": "2026-04-10T13:00:00",
    "tickets": 48,
    "categories": 6,
    "top_category": { "category_id": "vpn_connectivity", "title": "VPN Connectivity", "count": 12 }
  },
  "today_analyses": 2,
  "total_analyses": 145,
  "last_7_days_tickets": 312
}
```

**`fetchAnalyses(limit)`** → `GET /api/analyses?limit=20`
```json
{
  "count": 20,
  "analyses": [
    {
      "_id": "6651a2b3...",
      "run_date": "2026-04-10T13:00:00",
      "period_hours": 24,
      "brand_id": 1,
      "total_tickets": 48,
      "categories": {
        "vpn_connectivity": { "title": "VPN Connectivity", "count": 12, "summary": "Connection drops and tunnel failures..." },
        "account_billing": { "title": "Account & Billing", "count": 8, "summary": "Payment issues and subscription..." }
      },
      "new_trends": [
        {
          "title": "WireGuard handshake failures on v2.8.1",
          "count": 5,
          "description": "Multiple reports of WireGuard failing to complete handshake after app update",
          "geographic_pattern": "US East"
        }
      ],
      "ai_usage": { "model": "gpt-4o", "prompt_tokens": 12000, "completion_tokens": 3000, "total_tokens": 15000, "finish_reason": "stop" },
      "schema_version": "2"
    }
  ]
}
```

**`fetchAnalysisTickets(analysisId)`** → `GET /api/tickets?analysis_id=<id>`
```json
{
  "count": 48,
  "tickets": [
    {
      "_id": "...",
      "analysis_id": "6651a2b3...",
      "ticket_number": 9310221,
      "supportpal_id": 48201,
      "subject": "App freezes after connecting to WireGuard",
      "message_snippet": "I connected to WireGuard and the app froze for 10 seconds...",
      "ai_summary": "User reports app UI freeze for 10s after WireGuard handshake on Windows v2.8.1",
      "category_id": "vpn_connectivity",
      "is_new_trend": true,
      "trend_title": "WireGuard handshake failures on v2.8.1",
      "status": "Open",
      "priority": "High",
      "brand_id": 1,
      "supportpal_created_at": "2026-04-10T12:30:00",
      "created_at": "2026-04-10T13:00:00"
    }
  ]
}
```

**`triggerAnalysis(hours)`** → `POST /analyze` body: `{ "hours": 24 }`
```json
{ "status": "success", "message": "Analysis completed: 48 tickets processed" }
```

**`ticketUrl(supportpalId)`** → returns `https://support.int.windscribe.com/en/admin/ticket/view/{supportpalId}`

## Important Notes for Daily Runs Page

1. All API functions and type interfaces are already in `src/api.ts`. Just import them — `fetchStats`, `fetchAnalyses`, `fetchAnalysisTickets`, `triggerAnalysis`, `ticketUrl`, and their associated types.
2. The "Run Analysis Now" button should be clearly visible but not overly prominent. When clicked, it should show a loading spinner inside the button and disable the button until the request completes.
3. The run dropdown should format dates nicely (e.g., "Apr 10, 2026 — 48 tickets"). Use `new Date(run_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })`.
4. Categories should be sorted by count descending so the most common issues are at the top.
5. Keep the same Windscribe dark theme — all color variables and `glass-card` are already in `index.css`.
6. The Daily Runs tab should be the default active tab after this build.
7. Loading and empty states are required for all sections.
8. The ticket table needs horizontal scroll on narrow screens.
