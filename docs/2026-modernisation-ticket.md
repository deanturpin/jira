# Modernise reporting tool for 2026 (MCP + GitLab-native delivery)

## Context

This tool was built around two constraints that no longer apply:

1. **No MCP existed** — so it ships a hand-rolled Jira REST client (`bin/jira_client.py`)
   plus a fleet of one-off poke-at-Jira scripts (`list_*.py`, `check_*.py`,
   `inspect_*.py`, `dump_epics.py`).
2. **Couldn't send email without a VPS** — so it has `deploy-to-vps.sh`,
   `bin/send_daily_report.py` (Resend), and cron-based scheduling.

We now have: Atlassian (Jira) MCP available at work, and full access to work
GitLab/infrastructure. Goal for 2026: **keep the scheduled stakeholder reports,
add an interactive/agentic planning layer, and retire the VPS in favour of
GitLab CI + Pages with work email.**

## Workstreams

### 1. Adopt Atlassian MCP for ad-hoc/agentic planning

- Use the Jira MCP server for interactive, on-demand planning Q&A over **live**
  Jira (velocity, remaining work, epic projections) instead of pre-generating
  everything statically.
- Keep `jira_client.py` for the batch report pipeline for now (MCP is for the
  interactive layer); revisit consolidating once the MCP path is proven.
- **Cull dead scripts**: the `list_*` / `check_*` / `inspect_*` / `dump_*`
  debug helpers were scaffolding for the pre-MCP era. Audit which are still
  referenced by the Makefile / `generate_all.py` (the four `generate_*` +
  `velocity_calculator` + `stats_logger` + `view_backlog` + `close_sprint` are
  live; most others look like one-offs) and delete the rest. Trust git history.

### 2. Retire VPS → GitLab CI + Pages

- `.gitlab-ci.yml` already runs `generate_all.py` on a Monday 1am schedule and
  publishes `public/` to Pages, with stats-CSV delta continuity. Make this the
  sole delivery path.
- Remove `deploy-to-vps.sh`, `make deploy`, `VPS_DEPLOYMENT.md`, and the
  cron setup (`CRON_SETUP.md`, `bin/daily_report_cron.sh`) once parity is
  confirmed.
- Move project config fully to GitLab CI/CD variables (already partially done).

### 3. Replace Resend email with work email system

- Swap `bin/send_daily_report.py`'s Resend dependency for the work
  email/SMTP relay now available.
- Send from the scheduled GitLab pipeline (after `generate_all.py`) rather than
  a separate cron + VPS step, so generation and delivery are one job.

## Notes / cleanup spotted during review

- `SPRINT_LENGTH_WEEKS_N` is documented in `.env`/README but **not wired into
  the projection code** — projections assume 1-week sprints
  (`generate_dashboard.py:199`). Either wire it up or remove the false config.
- No automated tests — verification is visual via generated output. Consider a
  lightweight smoke test now that infra is being touched.
- `.claude/CLAUDE.md` updated alongside this ticket with Commands / Data Flow /
  Deployment sections.

## Acceptance criteria

- [ ] Interactive planning works against live Jira via MCP (no script run needed).
- [ ] Scheduled reports generate + deliver entirely from GitLab CI (no VPS, no cron).
- [ ] Emails sent via work system, Resend dependency removed.
- [ ] Dead pre-MCP scripts removed; `make` still produces all current outputs.
