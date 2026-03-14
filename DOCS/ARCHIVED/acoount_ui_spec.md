# Accounts Page Product Specification (Derived from `frontend/js/pages/accounts.js`)

## System Purpose
The Accounts page is an operations workspace for managing game accounts in a roster. It supports:
- Viewing account records in either a sortable table or card grid.
- Reviewing account health/status, emulator linkage, and resource snapshots.
- Creating and editing account records.
- Reviewing and resolving newly discovered “pending accounts” from scan processes.
- Inspecting account detail in a slide-out panel with Overview, Resources, and Activity Log tabs.
- Triggering account data refresh across all accounts.

## Feature Inventory
- **Dual list presentation**
  - Table view with sortable columns.
  - Grid/card view for visual summary.
- **Sorting**
  - Sort by account ID, emulator, name, game ID, power, runtime state, provider, and each resource metric.
  - Sort direction toggles between ascending/descending.
- **Page-level actions**
  - Sync All action.
  - Add Account action.
  - Export CSV button shown as disabled/coming soon.
- **Account detail slide panel**
  - Header with identity/status metadata.
  - Tabs: Overview, Resources, Activity Log.
  - Edit entry point from detail header.
  - Delete entry point from detail header.
- **Add/Edit account form (in slide panel)**
  - Identity fields, login/access fields, internal notes.
  - Inline validation and inline error messaging.
  - Save loading state and saved feedback.
- **Pending accounts banner**
  - Horizontal list of newly discovered accounts.
  - Confirm flow opens an inline mini-form.
  - Dismiss flow removes pending item until future scans.
- **Resource comparison deltas**
  - Per-account delta indicators in table cells (if available).
  - Detailed deltas in Resources tab.
  - Comparison timestamp (“vs [date]”).
- **Operator notes (Activity tab)**
  - Editable note area.
  - Save button enabled only when text changed.
  - Save feedback states (saving/success/error).

## User Interactions
- Toggle between **List** and **Grid** modes.
- Click sortable headers to reorder data.
- Click row/card or “View” CTA to open account detail panel.
- Close panel by close button or overlay click.
- Switch detail tabs (Overview / Resources / Activity Log).
- Start add flow via **Add Account** button.
- Start edit flow via **Edit** button in detail panel.
- Submit add/edit form.
- Delete account via detail header delete action, then confirmation.
- In pending banner:
  - Click **Confirm** to open inline form.
  - Fill method/email/provider/alliance/note.
  - Click **Create Account**.
  - Click **Dismiss** to ignore pending entry.
- Click **Sync All** to reload datasets.
- Edit and save operator note from Activity tab.

## Data Visible to Users
### Account list (table/grid)
- Account ID.
- Emulator label (name or inferred index label).
- Lord name.
- Game ID (legacy IDs are visually flagged).
- Power.
- Runtime state badge.
- Provider.
- Resource values: Gold, Wood, Ore, Pet Token, Mana.
- Optional resource deltas (up/down/neutral) when comparison data exists.
- Last sync datetime (grid cards).
- Hall level (grid cards).
- Alliance tag (grid cards and detail).

### Detail panel
- Avatar initial (from lord name).
- Online/offline badge.
- Matched/unsynced indicator.
- Game ID/legacy warning.
- Emulator label.
- Stat cards: Power, Hall Level progression, Last Sync date/time.

### Overview tab
- Login method + dot indicator.
- Login email.
- Emulator instance + online/offline dot.
- Provider tag.
- Alliance tag.
- Hall and Market levels with meters.

### Resources tab
- Current stockpile values (Gold, Wood, Ore, Mana, Pet Token).
- Fill bars as percentages of displayed cap model.
- Delta values against previous scan when present.
- “AI insight” narrative based on deltas and ore criticality.
- Last updated time and comparison date label.

### Activity Log tab
- Operator Notes text area.
- Save status feedback.
- Placeholder timeline area for future activity history.

### Pending accounts
- Candidate name (or unknown fallback).
- Candidate game ID.
- Emulator association.
- Pending count badge.
- Confirm mini-form fields: login method, login email, provider, alliance, notes.

## System States
- **Loading**
  - Header count text indicates loading.
  - Skeleton rows/cards displayed.
- **Ready**
  - Accounts rendered in selected view mode.
- **Empty**
  - Empty-state prompt encouraging Add Account.
- **Error**
  - Error banner/message in list area.
- **Detail panel open/closed**
  - Overlay and slide animation states.
- **Form saving**
  - Submit/cancel disabled; spinner visible.
- **Note-saving microstates**
  - Idle, changed-enabled, saving, saved, error.
- **Pending form expanded/collapsed**
  - Inline confirm form shown for selected pending account.

## User Flows
1. **Browse and inspect account**
   - Open Accounts page → view list/grid → open detail panel → review tabs.

2. **Sort and compare roster quickly**
   - Click target column headers → alternate sort direction → compare key metrics.

3. **Add account manually**
   - Click Add Account → complete form → submit → success feedback → panel closes and list refreshes.

4. **Edit existing account**
   - Open account detail → click Edit → update allowed fields → submit → refreshed data reopens context.

5. **Delete account**
   - Open detail → click Delete → confirm deletion → list refresh.

6. **Process pending account**
   - Find item in Pending banner → click Confirm → fill required context → create account → refresh roster.

7. **Dismiss pending item**
   - Click dismiss on pending card → confirm → item removed from current pending list.

8. **Update operator note**
   - Open Activity tab → edit note → Save Note enabled → save via API → success/error feedback.

9. **View resource trends**
   - Open detail → Resources tab → inspect current stock and deltas vs prior scan.

## UI Structure
- **Page shell**
  - Header area (title, count/status text, view toggle, action buttons).
  - Pending banner zone.
  - Main content zone (table or grid).
  - Overlay + right slide panel container.
  - Delete modal container placeholder.

- **Detail panel shell**
  - Header (identity/status + actions).
  - Stats row.
  - Tab strip.
  - Tab content area.

- **Form shell (add/edit or pending-confirm)**
  - Section labels.
  - Field groups.
  - Inline errors/hints.
  - Footer actions and feedback.

## Screen Inventory
- Accounts page — table mode.
- Accounts page — grid mode.
- Accounts page — loading skeleton.
- Accounts page — empty state.
- Accounts page — error state.
- Accounts page — with pending banner.
- Account detail slide panel — Overview tab.
- Account detail slide panel — Resources tab.
- Account detail slide panel — Activity tab.
- Add account form (slide panel).
- Edit account form (slide panel).
- Pending account confirm mini-form (inline within banner).

## Component Inventory
- Page header/title + connected count text.
- View mode segmented toggle (List/Grid).
- Action buttons: Export CSV (disabled), Sync All, Add Account.
- Pending accounts banner + cards + count badge.
- Accounts table with sticky header and frozen leading columns.
- Grid account card.
- Runtime status badge system.
- Resource value cell with inline delta glyph.
- Slide panel + overlay.
- Detail header badges (online/offline, matched/unsynced, legacy).
- Stat cards with progress bars.
- Tabs control.
- Resource cards with progress fills and delta tags.
- AI insight callout.
- Operator note editor + save row.
- Add/Edit form controls.
- Inline validation error text and hints.
- Form footer feedback + spinner.

## UI State Variants
- View mode: table vs grid.
- Sort: unsorted / sorted asc / sorted desc.
- Runtime statuses:
  - Running (active + online).
  - Ready (active + emulator offline).
  - Linked (has emulator link, inactive).
  - Unlinked (no emulator link).
- Emulator status dots: online / offline / idle styling.
- Account selection state (selected row highlight when detail open).
- Legacy game ID visual warning state.
- Delta states: up / down / neutral / unavailable.
- Ore critical visual treatment when below threshold in Resources tab.
- Save controls: enabled/disabled/loading/success/error.
- Pending banner visible/hidden based on pending count.

## Error Conditions
- Account list fetch failure shows page-level error state.
- Pending accounts fetch issues contribute to refresh failure behavior.
- Add/edit submission network failures show toast error.
- Add/edit API logical failures show toast error.
- Delete network/API failure shows toast error.
- Pending confirm/dismiss network/API failures show toast error.
- Note save failure shows inline red feedback.
- Input validation errors are shown inline for invalid form values.

## Edge Conditions
- Missing/null values are normalized with safe fallbacks (e.g., “—”, “No Emulator”, “Never”, zero-formatted metrics).
- Legacy IDs (prefixed) are accepted and visually flagged differently.
- Email requirement is conditionally shown based on selected login method.
- Duplicate game ID is blocked for new-account creation.
- Resource comparisons may be absent; UI shows placeholder deltas.
- Pending accounts can be absent; banner is fully hidden.
- If no accounts exist, page transitions to explicit empty state.

## Design Considerations
- Prioritize **scanability** for high-density operational data (especially table mode).
- Maintain parity between **table and card view** for critical account facts.
- Ensure clear visual hierarchy in detail panel: identity → key stats → deep-dive tabs.
- Preserve quick-action ergonomics: add, sync, edit, delete, and pending resolution should remain one-hop actions.
- Use explicit empty/error/loading states to avoid ambiguous blank screens.
- Keep validation messages close to relevant fields and preserve entered data during failures.
- Highlight risk/attention indicators consistently (legacy ID, low ore, offline state, unsynced).
- Keep transitions lightweight but informative (panel slide, save feedback).
