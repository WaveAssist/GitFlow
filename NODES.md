# GitFlow: Node Structure

This document defines all workflow nodes for GitFlow, organized by the CID pipeline (Collection, Intelligence, Delivery). GitFlow is the **Ground Truth Report**: it reads **actual code diffs** (not PR titles or commit messages) and uses AI to produce leadership-ready business and technical narratives. It is **project-centric** and **multi-repo**—synthesizing your entire stack (frontend, backend, infra) into one unified product narrative.

---

## Primary Inputs

The following inputs are available at the start of the GitFlow workflow:

- **`project_name`** (string): Name of the project or team (e.g., `Acme system`). Stored in WaveAssist and available via `waveassist.fetch_data("project_name")`.

- **GitHub Integration** (via WaveAssist GitHub integration):

  - **`github_access_token`** (string): GitHub access token with read permissions. Available via `waveassist.fetch_data("github_access_token")`.
  - **`github_selected_resources`** (list of dictionaries or strings): Available via `waveassist.fetch_data("github_selected_resources")`. Format:
    ```python
    [
      {
        "id": "owner/repo_name",
        "name": "repo_name",
        "extra": ... (other properties from the GitHub API, not used in the workflow)
      },
    ]
    ```
    Or may be a list of strings: `["owner/repo1", "owner/repo2"]`

- **`model_name`** (string, optional): AI model to use for analysis and report generation. Defaults to `"anthropic/claude-haiku-4.5"`. Available via `waveassist.fetch_data("model_name")`.

---

## Collection Nodes

### Node 1: `check_credits_and_init`

**What does it do:** Initializes the workflow, checks available credits using `waveassist.check_credits_and_notify()`, and validates required inputs (`project_name`).

**Inputs:**

- `project_name` (string, from WaveAssist storage)

**LLM calls:** None

### **Stored data:** None

### Node 2: `fetch_repository_context`

**What does it do:** Fetches repository context files (README, requirements files, main entry points, etc.) for each repository and generates a one-time summary about each repository. Only processes repositories that don't already have context stored. This context is used in later nodes to provide better understanding of the repository structure and purpose.

**Inputs:**

- `github_selected_resources` (list of strings): List of repository paths
- `github_access_token` (string): GitHub access token

**Processing:**

- For each repository, checks if context already exists
- If not, fetches key files:
  - README files (README.md, README.rst, etc.)
  - Requirements files (requirements.txt, package.json, Pipfile, etc.)
  - Main entry points (main.py, index.js, app.py, etc.)
  - List of all files in repository (for structure understanding)
- Reads and summarizes repository purpose, structure, and key files
- Stores context per repository for future use
- Stores some tags for displaying in the UI. Can be the primary language, or the framework, or the database, or the cloud provider, etc. Limited to 3 tags.

**LLM calls:** `waveassist.call_llm()` with model `anthropic/claude-haiku-4.5` (or configurable via `model_name` input) and response model `RepositoryContext`

**Stored data:**

- `repository_contexts` (dict): Key-value pairs where key is repository path (e.g., `"owner/repo"`) and value is a dict containing:
  ```python
  {
      "summary": "Brief description of repository purpose and structure",
      "stack": "Summary of the stack of technologies used in the repository"
      "tags": ["tag1", "tag2", "tag3"]
  }
  ```

---

### Node 3: `fetch_github_activity`

**What does it do:** Fetches GitHub activity data for the past 7 days across all specified repositories. Uses GraphQL to identify active branches (branches with commits after the since date), then fetches commits from those active branches only. Collects commits and pull requests (open and merged). Filters out bot activity. Does not fetch file diffs or repository metadata. **Purpose:** isolate real, recent work so later stages can read the actual diffs.

**Inputs:**

- `github_selected_resources` (list of strings): List of repository paths
- `github_access_token` (string): GitHub access token

**Processing:**

- For each repository:
  1. Fetches all branches using GraphQL API (with pagination support, up to 50 pages)
  2. Filters branches to find active ones (branches with commits after the since date)
  3. Fetches commits from active branches only (commit SHA, message, author, timestamp, URL)
  4. Fetches pull requests (open and merged) from the past 7 days (PR number, title, description, status, author, timestamp, URL, head SHA, base branch)
- Filters out commits and PRs from bot accounts
- Deduplicates commits across branches (same SHA appears only once)
- Does NOT fetch:
  - File diffs (fetched later in Node 4)
  - Repository metadata
  - Activity summaries

**LLM calls:** None

**Stored data:**

- `github_activity_data` (dict): Per-repository activity data structure:
  ```python
  {
      "owner/repo1": {
          "commits": [
              {
                  "sha": "abc123...",
                  "message": "Fix bug in authentication",
                  "author": "username",
                  "timestamp": "2024-01-15T10:30:00Z",
                  "url": "https://github.com/owner/repo1/commit/abc123..."
              },
              # ... more commits
          ],
          "pull_requests": [
              {
                  "number": 42,
                  "title": "Add new feature",
                  "description": "Description text",
                  "status": "open",  # or "closed"
                  "author": "username",
                  "timestamp": "2024-01-15T11:00:00Z",
                  "created_at": "2024-01-15T11:00:00Z",
                  "url": "https://github.com/owner/repo1/pull/42",
                  "head_sha": "def456...",
                  "base_branch": "main"
              },
              # ... more PRs
          ]
      },
      "owner/repo2": {
          # ... same structure
      }
  }
  ```
- `report_date_range` (dict): Date range information for email display:
  ```python
  {
      "start_date": "2024-01-08T00:00:00+00:00",
      "end_date": "2024-01-15T00:00:00+00:00",
      "start_date_formatted": "January 08, 2024",
      "end_date_formatted": "January 15, 2024"
  }
  ```

---

## Intelligence Nodes

### Node 4: `analyze_repository_activity`

**What does it do:** Processes each repository's activity data separately. For each repository, processes commits one by one. For each commit, fetches all **file diffs** (zero-trust: ignores PR titles and commit text). Applies a three-tier splitting strategy based on total token count to handle large volumes of data. Converts commit data and code changes into structured summaries. Outputs a list of changes, where each change contains summary, category, and contributing commits—grounded in the actual diff. **Sets up cross-repo synthesis** by producing clean per-repo change sets that later roll into a unified project narrative.

**Processing Strategy:**

- **Repository-wise:** Each repository is processed independently
- **Commit-wise:** For each repository, processes commits sequentially
- **Diff fetching:** For each commit, fetches all file diffs from GitHub API
- **LLM Call Frequency:** 0-7+ calls per repository (0 if no commits in last 7 days, up to 7+ based on token volume and splitting tier)
- **Token Calculation:** Calculates total tokens across all commits (messages + file diffs) for the repository in the last 7 days

**File Processing Logic:**

- **Non-code file removal:** Filters out and removes all non-code files:
  - Images (jpg, png, gif, svg, webp, etc.)
  - Videos (mp4, avi, mov, etc.)
  - Binary blobs
  - Other media files
- **File size limiting:** Applies a maximum size limit per file. If a file's diff exceeds this limit, it is cropped/truncated. This limit is quite large and primarily serves to prevent processing of accidentally included media files or extremely large generated files.

**Splitting Logic (Three-Tier System):**

**Tier 1: The "Happy Path" (< 100K Tokens)**

- **Action:** Single LLM call for the entire 7-day period
- **Context:** All commits (messages + file diffs) + PRs, sorted chronologically
- **Benefit:** Maximum "dot-connecting" - the LLM sees the full narrative of the week

**Tier 2: The "Busy Week" (100K – 700K Tokens)**

- **Action:** Split by Day
- **Logic:**
  1. Group commits/diffs into 7 buckets (Mon–Sun)
  2. Fill a "Batch" with Day 1, check size
  3. If Day 1 + Day 2 < 100K, combine them
  4. Once the batch hits ~90-100K, ship it to the LLM
- **Frequency:** Max 7 LLM calls (one per day, or combined days)
- **Benefit:** Maintains daily context - even if a dev worked on something across 3 commits in one day, the LLM sees that entire "day's thought process" together

**Tier 3: The "Mega Repo" (> 700K Tokens)**

- **Action:** Hybrid approach - process normal days like Tier 2, compress oversized days
- **Logic:**
  1. Group commits/diffs into 7 buckets (Mon–Sun)
  2. Identify which days exceed 100K tokens
  3. For days that do NOT exceed 100K: Process them using Tier 2 logic (can combine with adjacent days if total < 100K)
  4. For days that DO exceed 100K: Compress them to fit within 100K budget:
     - Calculate budget per commit: `100000 / number_of_commits_in_day`
     - Fit each commit within its budget (most commits will fit, those that don't are truncated)
     - For files within each commit:
       - Calculate budget per file: `commit_budget / number_of_files_in_commit`
       - Crop files that exceed their budget (similar to file cutting logic)
     - Apply file size limiting and non-code file removal as described above
- **Frequency:** Multiple batches as needed (typically 7+ calls)
- **Benefit:** Handles major refactors, library migrations, or noisy commits (like lock files) without losing critical context, while preserving daily context where possible

**Context Structure for Each LLM Call:**

- **Commits:** All commit info (author, message, timestamp, SHA)
- **Files:** Changed files with diffs (using file cutting logic to cap total size, non-code files removed)
- **Repository Context:** Summary and key information from Node 2 (if available)

**LLM calls:**

- **Model:** `anthropic/claude-haiku-4.5` (or configurable via `model_name` input)
- **Frequency:** 0-7+ calls per repository (based on token volume and splitting tier)
- **Purpose:** Analyze each repository's activity independently to extract technical insights, categorize changes, and convert code/commits to structured summaries
- **Output:** Per-repository analysis with categorized changes

**Stored data:**

- `repository_analyses` (list): List of per-repo analysis results. Each entry contains:
  ```python
  {
      "repository": "owner/repo",
      "changes": [
          {
              "summary": "Added Redis-based caching for user profile API",
              "category": "improvement"  # Options: "feature", "improvement", "fix", "refactor", etc.
              "contributing_commits": ["sha1", "sha2", "sha3"]
          },
          {
              "summary": "Fixed authentication bug causing login failures",
              "category": "fix"
              "contributing_commits": ["sha1", "sha2", "sha3"]
          },
          # ... more changes
      ]
  }
  ```

**Note:** Each change dictionary contains only two fields: `summary` (string) and `category` (string) and a list of commits which contributed to the change.

---

### Node 5: `generate_technical_report`

**What does it do:** Takes all per-repository analyses and synthesizes them into a technical report focused on repository-specific details. Creates a repository-by-repository deep dive with status indicators and technical changes. Works with already-processed summaries, so requires only a single LLM call. Uses business report context to avoid duplication and focus on technical details. **Audience:** CTO / Head of Engineering seeking architecture alignment, drift detection, and refactor/feature balance—grounded in the actual diff. **Cross-Repo Intelligence:** groups related work across repos to reflect full-stack features (e.g., backend + frontend + infra) in one project-centric view.

**Inputs:**

- `repository_analyses` (list): Per-repository analysis results from Node 4
- `project_name` (string): Project name for report headers
- `business_report` (dict): Business report from Node 6 (for context, to avoid duplication)
- `repository_contexts` (dict): Repository context summaries from Node 2

**Report Format:**

A repository-focused technical deep dive designed for tech leads, engineering managers, and developers who need technical details.

| Section                  | Description                                                                      |
| ------------------------ | -------------------------------------------------------------------------------- |
| **Repository Deep Dive** | Per-repository breakdown with status and technical changes (2-3 points per repo) |
| **Poem**                 | A 4-line tech-focused poem summarizing the week's activity                       |

**Context Usage:**

- **Reads:** `business_report` (if available) - to understand what features were already covered and focus on technical details
- **Uses:** `repository_contexts` - to provide context about each repository's purpose and stack

**LLM calls:**

- **Model:** `anthropic/claude-haiku-4.5` (or configurable via `model_name` input)
- **Frequency:** Single call (works with processed summaries from Node 4)
- **Purpose:** Synthesize all per-repo analyses into a repository-focused technical report, avoiding duplication with business report
- **Output:** Complete technical report with repository deep dive and poem

**Stored data:**

- `technical_report` (dict): Complete formatted technical report content. Structure:
  ```python
  {
      "repository_deep_dive": [
          {
              "repo_name": "owner/repo1",
              "status": "Heavy Refactor",  # 1-2 words describing repo status
              "technical_changes": [
                  "Added Redis-based caching for user profile API",
                  "Fixed authentication bug causing login failures"
              ]
          },
          # ... more repositories
      ],
      "poem": [
          "Line 1 of the poem",
          "Line 2 of the poem",
          "Line 3 of the poem",
          "Line 4 of the poem"
      ]
  }
  ```

---

### Node 6: `generate_business_report`

**What does it do:** Takes all per-repository analyses and synthesizes them into a business report focused on headline features and user-facing wins. Extracts the 2-3 biggest/significant features and creates a concise executive summary. Works with already-processed summaries, so requires only a single LLM call. References historical business report summaries (last 1 week) for context and continuity, then saves the current report summary to history. **Audience:** CEO / Head of Product looking for ROI and momentum, translated directly from shipped code (not Jira/PR narratives). **Project Narrative:** combines multi-repo workstreams into a unified product update (front-end + back-end + infra).

**Inputs:**

- `repository_analyses` (list): Per-repository analysis results from Node 4
- `project_name` (string): Project name for report headers
- `business_report_history` (list, optional): Historical business report summaries from last 1 week
- `repository_contexts` (dict): Repository context summaries from Node 2

**Report Format:**

A concise executive summary for product managers, founders, and non-technical stakeholders who need to stay informed without the code-level detail.

| Section               | Description                                                     |
| --------------------- | --------------------------------------------------------------- |
| **Executive Summary** | Exactly 2 sentences on the week's biggest impact.               |
| **Shipped Features**  | Top 1-3 user-facing capabilities completed and ready for users. |

**History Management:**

- **Reads:** `business_report_history` (if available) - contains final summaries from the last 1 week for context
- **Saves:** Current report summary to `business_report_history` (maintains rolling window of last 1 week, then appends current week for total of 2 weeks)

**LLM calls:**

- **Model:** `anthropic/claude-haiku-4.5` (or configurable via `model_name` input)
- **Frequency:** Single call (works with processed summaries from Node 4)
- **Purpose:** Transform per-repo technical analyses into business-friendly insights and synthesize into a concise, executive-friendly report for product managers, founders, and non-technical stakeholders, with historical context for continuity
- **Output:** Complete business report with executive summary and shipped features

**Stored data:**

- `business_report` (dict): Complete formatted business report content. Structure:
  ```python
  {
      "executive_summary": "2 sentences on the week's biggest impact",
      "shipped_features": [
          "Feature 1 - user-facing benefit description",
          "Feature 2 - user-facing benefit description",
          "Feature 3 - user-facing benefit description"
      ]
  }
  ```
- `business_report_history` (list): Updated with current week's business report summary, maintains last 1 week. Structure:
  ```python
  [
      {
          "week": "2024-01-08",
          "report": {
              "executive_summary": "...",
              "shipped_features": [...]
          }
      },
      {
          "week": "2024-01-15",
          "report": {
              "executive_summary": "...",
              "shipped_features": [...]
          }
      }
  ]
  ```

---

## Delivery Nodes

### Node 7: `send_emails`

**What does it do:** Renders both the technical and business reports as a single combined styled HTML email and sends it to the user. Includes proper formatting, headers, project branding, activity statistics, and a PDF attachment. Uses `waveassist.send_email()` to send the email with PDF attachment. If no activity is detected, sends a simple "no activity" email. **Positioning:** leadership-ready “Ground Truth Report” for CEO, CTO, Product, and Marketing, derived from code diffs, presenting a unified product narrative across all repositories.

**Inputs:**

- `technical_report` (dict): Complete technical report content from Node 5
- `business_report` (dict): Complete business report content from Node 6
- `project_name` (string): Project name for email headers
- `github_activity_data` (dict): Per-repository commits and PRs from past 7 days
- `repository_contexts` (dict): Repository context summaries from Node 2 (for tags)
- `report_date_range` (dict): Date range information from Node 3
- `github_selected_resources` (list): List of selected repositories

**Email Structure:**

A single combined email with the following sections:

| Section                     | Description                                                                 |
| --------------------------- | --------------------------------------------------------------------------- |
| **Header**                  | Project name and report date range                                          |
| **Stats Bar**               | Activity statistics: commits, contributors, total repos, active repos       |
| **SUMMARY**                 | Executive summary from business report                                      |
| **🚀 PRIMARY UPDATES**      | Shipped features from business report                                       |
| **🛠️ REPOSITORY DEEP DIVE** | Repository-by-repository technical breakdown with status, tags, and changes |
| **Poem**                    | 4-line tech-focused poem from technical report                              |
| **Footer**                  | GitFlow branding and PDF attachment notice                                  |

**PDF Attachment:**

- Generates a PDF version of the email using WeasyPrint
- Attaches PDF to the email for easy sharing, printing, and offline viewing
- PDF filename format: `GitFlow_Report_{project_name}_{timestamp}.pdf`

**LLM calls:** None

**WaveAssist library**: `send_email(subject, html_content, attachment_file=pdf_file)`

**Stored data:**

- `display_output` (dict): Run-based output for WaveAssist UI, summarizing what was sent. Structure:
  ```python
  {
      "title": "Weekly Update: {project_name}",
      "html_content": "...",
      "status": "success",
      "summary": {
          "commits": 42,
          "contributors": 5
      },
      "pdf_attachment": {
          "enabled": True,
          "file_name": "GitFlow_Report_...",
          "generated": True,
          "error": None
      }
  }
  ```

---

## Node Dependencies

```
check_credits_and_init (starting node)
  └─> fetch_repository_context
       └─> fetch_github_activity
            └─> analyze_repository_activity (processes each repo separately, then each commit)
                 └─> generate_business_report (synthesizes all repo analyses)
                      └─> generate_technical_report (synthesizes all repo analyses, uses business report context)
                           └─> send_emails (runs after both reports are ready, sends single combined email)
```

---

## Key Stored Data Keys

**Inputs:**

- `project_name` (string, required): Project/team name, stored in WaveAssist
- `github_access_token` (string): GitHub access token from GitHub integration
- `github_selected_resources` (list of strings): List of repository paths from GitHub integration

**Collection:**

- `repository_contexts` (dict): Per-repository context summaries, stack information, and tags
- `github_activity_data` (dict): Per-repository commits and PRs from past 7 days
- `report_date_range` (dict): Date range information for email display

**Intelligence:**

- `repository_analyses` (list): Per-repository analysis results, each containing a `changes` list with dictionaries having `summary` (string), `category` (string), and `contributing_commits` (list of SHAs)
- `technical_report` (dict): Complete formatted technical report with `repository_deep_dive` and `poem`
- `business_report` (dict): Complete formatted business report with `executive_summary` and `shipped_features`
- `business_report_history` (list): Rolling history of business report summaries from last 1 week, used for context in Node 6

**Delivery:**

- `display_output` (dict): Run-based output for WaveAssist UI with email details and PDF attachment info
