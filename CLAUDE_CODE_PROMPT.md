# TARS QA Dashboard — Claude Code Build Prompt

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
