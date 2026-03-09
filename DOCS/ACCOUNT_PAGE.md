# Account Page - Developer Guide

This document explains how the **Accounts Page** works (`frontend/js/pages/accounts.js`) so future changes are faster and safer.

## 1) What this page does

- Render account data in **Table** and **Grid** view modes.
- Show account detail in slide panel (Overview / Resources / Activity tabs).
- Create and edit account metadata (login method, provider, email, alliance, notes).
- Consume pending accounts discovered by Full Scan.
- Show resource comparison deltas from `/api/accounts/{game_id}/comparison`.

## 2) Main frontend state

`AccountsPage` keeps all page state in-memory:

- `_accountsData`: resolved account list.
- `_pendingAccounts`: Full-scan queue not yet confirmed.
- `_selectedAccountId`: active row/card detail target.
- `_activeDetailTab`: overview/resources/activity.
- `_viewMode`: `table` or `grid`.
- `_pageState`: loading/ready/error/empty.
- `_comparisonCache`: per-game id delta cache used by table + resources tab.

## 3) Data APIs used by page

### Read

- `GET /api/accounts`
  - Primary account list.
- `GET /api/pending-accounts`
  - Accounts waiting for user confirmation.
- `GET /api/accounts/{game_id}/comparison`
  - Previous snapshot + delta for resources.

### Write

- `POST /api/accounts`
  - Create account.
- `PUT /api/accounts/{game_id}`
  - Update account fields.
- `DELETE /api/accounts/{game_id}`
  - Delete account.
- `POST /api/pending-accounts/{id}/confirm`
  - Promote pending account.
- `POST /api/pending-accounts/{id}/dismiss`
  - Ignore pending account.

## 4) Rules currently enforced in UI

### Provider

Only two provider options are exposed on Accounts page:

- `Global`
- `Funtap`

Helper: `_normalizeProvider()`

### Login method

Only three login methods are exposed on Accounts page:

- `Facebook`
- `Google`
- `Email`

Helper: `_normalizeLoginMethod()`

### Runtime State (table column)

Table column meaning:

- `🟢 Running`: account active and emulator online.
- `🟡 Ready`: account active but emulator offline.
- `⚪ Linked`: emulator linked but account not active.
- `🔴 Unlinked`: no emulator linked.

Helper: `_getRuntimeStatus(row)`

### Last Sync display

All sync timestamps use `formatDateTime()` so date and time are shown (not only time-of-day).

## 5) Resource comparison flow

- During `fetchData()` accounts are loaded first.
- Then comparison requests are preloaded for all accounts and stored in `_comparisonCache`.
- Table inline deltas read from cache so they can appear without opening each account.
- If delta is exactly `0`, UI shows a neutral bullet (`•`) for explicit "no change".

Key methods:

- `_fetchComparison(gameId)`
- `_updateDeltaUI(delta, previous)`
- `mkInlineDelta()` in table renderer

## 6) Fast-change map (where to edit)

- **Table columns / labels**: `render()` header + `_renderTableBody()`.
- **Grid card content**: `_renderGridBody()`.
- **Slide panel summary cards**: `_renderSlideContent()`.
- **Overview tab**: `_renderActiveTab()` branch `overview`.
- **Resources tab**: `_renderActiveTab()` branch `resources`.
- **Add/Edit form fields**: `_renderAddEditForm()`.
- **Pending confirm form**: `showConfirmForm()`.

## 7) Backend references

Backend account schema and writes are handled in:

- `backend/storage/database.py`
- `backend/api.py`

If you change frontend option sets (provider/login method), ensure backend validation (if added later) matches these values.

## 8) Recommended regression checks

1. Open Accounts page, verify list renders both table and grid.
2. Check runtime state badges for online/offline/unlinked examples.
3. Open account detail and verify Last Sync includes date + time.
4. Add/edit account and verify provider/login method options.
5. Confirm pending account form uses same option sets.
6. Verify deltas show in list without needing manual Sync All.
7. Verify Resources tab still updates deltas after tab open.

## 9) Table sorting

The account list table supports click-to-sort on every visible data header.

- Click a header once => ascending sort.
- Click the same header again => descending sort.
- Click another header => switch field, reset to ascending.

Implementation in `frontend/js/pages/accounts.js`:

- `_sortField`, `_sortDirection` state
- `sortBy(field)`
- `_sortedAccounts()`
- `_sortValue(row, field)`
- `_sortIndicator(field)`

Current sortable fields: id, emulator, name, game id, power, runtime state, provider, and all resource columns.

