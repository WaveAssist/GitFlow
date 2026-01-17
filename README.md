<h1 align="center">GitFlow: The Ground Truth Engineering Report</h1>

<p align="center">
  <a href="https://waveassist.io">
    <img src="https://img.shields.io/badge/Deploy_with-WaveAssist-007F3B" alt="Deploy with WaveAssist" />
  </a>
  <img src="https://img.shields.io/badge/GitFlow-weekly%20git%20reports-purple" alt="GitFlow Badge" />
</p>

---

## Overview

GitFlow is the **Ground Truth Report** for CEOs, CTOs, Heads of Product, and Marketing. It is **project-centric**: AI reads all your repos (frontend, backend, infra) to build one **Unified Executive Summary** from the **actual code diffs**, the only source of truth for what really shipped. Every week, GitFlow turns raw diffs into AI-generated, leadership-ready business and technical narratives you can trust for board updates, release notes, and roadmap decisions.

---

## One-Click Deploy on WaveAssist (Recommended)

<p>
  <a href="https://waveassist.io" target="_blank">
    <img src="https://waveassist.io/images/templates/Button.png" alt="Deploy on WaveAssist" width="230" />
  </a>
</p>

Deploy GitFlow instantly on [WaveAssist](https://waveassist.io) — a zero-infrastructure automation platform that handles orchestration, scheduling, secrets, and hosting for you.

> 🔐 You may be prompted to log in or create a free WaveAssist account before continuing.

### How to Use

1. Connect your **GitHub account** (required) — select the repositories you want to track.
2. Set **`project_name`** (required) — the name of your project/team for report headers.
3. Click **Run & Deploy** to schedule weekly reports.

---

## Inputs

- **Required**

  - **`project_name`**: Name of your project or team (e.g. `Acme Backend`, `Mobile App`)
  - **GitHub Integration**: Connect your GitHub account and select repositories to monitor. GitFlow will automatically access:
    - `github_access_token`: GitHub access token with read permissions
    - `github_selected_resources`: List of selected repository paths (e.g., `["owner/repo1", "owner/repo2"]`)

---

## What You Get (Outputs)

GitFlow delivers a **single comprehensive Ground Truth email**—business + technical in one—plus a PDF for sharing. Every claim is backed by the actual code diff.

### 📧 Weekly Ground Truth Email (AI-generated from real diffs)

Audience-specific clarity:

- **For CEO / Head of Product:** Business momentum, user-facing value, zero fluff.
- **For CTO / Head of Engineering:** Architecture alignment, refactors vs. features, risk & drift.
- **For Marketing:** Release notes written from the code, not from wishful PR titles.

Structure:

| Section                     | Description                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| **SUMMARY**                 | 2-sentence executive summary of the week's biggest impact (diff-validated).                        |
| **🚀 PRIMARY UPDATES**      | Top 1-3 user-facing capabilities actually shipped in code.                                         |
| **🛠️ REPOSITORY DEEP DIVE** | Per-repository technical breakdown: status, tags, and specific improvements (2-3 points per repo). |
| **Poem**                    | A 4-line tech-flavored poem capturing the week’s tone.                                             |

Included: activity stats (commits, contributors, total repos, active repos) and a PDF attachment for offline sharing.

---

## Schedule

GitFlow runs on a **weekly schedule** (default: every Monday at 8:30 AM UTC, configurable). Each report covers the previous 7 days of activity across all tracked repositories.

---

## How It Works

GitFlow follows a CID pipeline (Collection, Intelligence, Delivery) anchored on diffs:

1. **Collection:** Fetches repo context and **active-branch commits** across your whole stack, then pulls the actual code diffs (not just commit messages). PR titles are ignored; diffs are truth.
2. **Intelligence (Cross-Repo Synthesis):** AI looks across **all connected repositories** to identify shared themes, cross-functional features, and project-wide progress—bridging frontend, backend, and infra into one **Unified Product Narrative** (with last-week history for continuity).
3. **Delivery:** Sends a single combined HTML + PDF report tailored to executives and engineering leads.

## Notes

- **Code-first accuracy:** Built on code diffs, not PR text—zero-trust, audit-ready. **AI-generated from the actual diffs.**
- **GitHub access:** Requires read access; GitHub integration provides the token and repos.
- **Multi-repo support:** Aggregate across any number of repos into one executive view.
- **Unified report:** One email for business + technical; perfect for CEO, CTO, Product, Marketing.
- **Cross-Repo intelligence:** Aggregates diffs across all repos to produce a **Unified Product Narrative** with full-stack visibility and project-level momentum.
- **Historical context:** References last week’s business summary for continuity.
- **Repository context:** Captures purpose, stack, key files, and tags; reused on subsequent runs.
- **Smart processing:** Tiered token management and non-code filtering to handle mega repos.
- **Active branch detection:** Focuses on branches with real activity to cut noise.
- **PDF attachment:** Leadership-ready PDF included for sharing/printing.
- **Model selection:** Configurable AI model (default: Claude Haiku 4.5).
- **Taglines:** “The ground truth of your engineering week.” · “Stop reading PRs. Start seeing progress.” · “Where your codebase meets your boardroom.”
