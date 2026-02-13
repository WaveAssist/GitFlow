import requests
import time
import waveassist
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting repository activity analysis...")

# LLM settings
max_tokens = 2500
temperature = 0.4

# Token thresholds for splitting strategy
TIER_1_THRESHOLD = 100000  # < 100K tokens: single call
TIER_2_THRESHOLD = 700000  # 100K - 700K tokens: split by day
# > 700K tokens: Tier 3 hybrid approach

# Token estimation: ~3 chars per token
CHARS_PER_TOKEN = 3

# Maximum file diff size (characters) before truncation
MAX_FILE_DIFF_SIZE = 90000 ##Appx 30K tokens

# Non-code file extensions to filter out
NON_CODE_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    # Videos
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    # Audio
    ".mp3", ".wav", ".ogg", ".flac",
    # Binary/Archives
    ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll", ".so", ".dylib",
    # Other non-code
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Lock files (often very large)
    ".lock",
}


class Change(BaseModel):
    """Model for a single change/update"""
    summary: str = Field(description="Brief summary of what changed")
    category: str = Field(description="Category: feature, improvement, fix, refactor, docs, test, chore")
    contributing_commits: List[str] = Field(description="List of commit SHAs that contributed to this change")


class RepositoryAnalysis(BaseModel):
    """Model for repository analysis result"""
    changes: List[Change] = Field(description="List of changes identified in this batch")


def is_non_code_file(filename: str) -> bool:
    """Check if a file is non-code based on extension."""
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    return ext in NON_CODE_EXTENSIONS


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    return len(text) // CHARS_PER_TOKEN


def fetch_commit_diff(repo_path: str, sha: str, headers: dict) -> List[Dict[str, Any]]:
    """Fetch file diffs for a specific commit."""
    url = f"https://api.github.com/repos/{repo_path}/commits/{sha}"
    response = requests.get(url, headers=headers)
    
    # Rate limiting: sleep between API calls
    time.sleep(0.5)
    
    if response.status_code != 200:
        return []
    
    try:
        data = response.json()
        files = data.get("files", [])
        processed_files = []
        
        for f in files:
            filename = f.get("filename", "")
            
            # Skip non-code files
            if is_non_code_file(filename):
                continue
            
            patch = f.get("patch", "")
            
            # Truncate large diffs
            if len(patch) > MAX_FILE_DIFF_SIZE:
                patch = patch[:MAX_FILE_DIFF_SIZE] + "\n\n[TRUNCATED: File diff exceeds size limit. The content above represents only the beginning of the changes. Analyze based on the visible portion.]"
            
            processed_files.append({
                "filename": filename,
                "patch": patch,
                "status": f.get("status", "modified"),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
            })
        
        return processed_files
    except Exception as e:
        print(f"⚠️ Error fetching diff for {sha}: {e}")
        return []


def group_commits_by_day(commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group commits by day (YYYY-MM-DD)."""
    by_day = defaultdict(list)
    
    for commit in commits:
        timestamp = commit.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                day_key = dt.strftime("%Y-%m-%d")
                by_day[day_key].append(commit)
            except:
                by_day["unknown"].append(commit)
        else:
            by_day["unknown"].append(commit)
    
    return dict(by_day)


def build_commit_context(
    commits: List[Dict[str, Any]],
    commit_diffs: Dict[str, List[Dict[str, Any]]],
    token_budget: Optional[int] = None
) -> str:
    """Build context string from commits and their diffs."""
    parts = []
    total_tokens = 0
    
    for commit in commits:
        sha = commit.get("sha", "")
        message = commit.get("message", "")
        author = commit.get("author", "Unknown")
        timestamp = commit.get("timestamp", "")
        
        commit_text = f"Commit: {sha[:7]}\nAuthor: {author}\nDate: {timestamp}\nMessage: {message}\n"
        
        # Add files if we have diffs
        if sha in commit_diffs:
            files = commit_diffs[sha]
            
            # If token_budget is present, sort files by size (smallest first)
            if token_budget:
                def get_file_size(f):
                    """Estimate size based on patch length."""
                    patch = f.get("patch", "")
                    return len(patch) if patch else 0
                
                files = sorted(files, key=get_file_size)
            
            for f in files:
                file_text = f"File: {f['filename']} ({f['status']})\n"
                if f.get("patch"):
                    file_text += f"```\n{f['patch']}\n```\n"
                
                # Check budget
                file_tokens = estimate_tokens(file_text)
                if token_budget and (total_tokens + file_tokens > token_budget):
                    file_text = f"File: {f['filename']} ({f['status']})\n[TRUNCATED: File diff omitted due to token budget constraints. This file was modified, but the full diff is not included. Analyze based on existing context.]\n"
                
                commit_text += file_text
        
        commit_tokens = estimate_tokens(commit_text)
        
        # Check budget
        if token_budget and (total_tokens + commit_tokens > token_budget):
            break
        
        parts.append(commit_text)
        total_tokens += commit_tokens
    
    return "\n---\n".join(parts)


def analyze_batch(
    repo_path: str,
    context: str,
    repo_context: Optional[Dict[str, Any]],
    model_name: str
) -> Optional[RepositoryAnalysis]:
    """Run LLM analysis on a batch of commits."""
    
    repo_context_section = ""
    if repo_context:
        repo_context_section = f"""
Repository Context:
- Summary: {repo_context.get('summary', 'N/A')}
- Stack: {repo_context.get('stack', 'N/A')}
---
"""
    
    prompt = f"""Analyze the following Git commits and code changes from repository {repo_path}.

{repo_context_section}

Commits and Changes:
{context}

---

Your task:
1. Identify distinct changes/updates from these commits
2. Group related commits that contribute to the same logical change
3. Categorize each change as: feature, improvement, fix, refactor, docs, test, or chore
4. Write a clear, concise summary for each change (1-2 sentences)

Guidelines:
- Focus on WHAT changed
- Combine small related commits into single logical changes
- Skip trivial changes (typo fixes, formatting) unless they're part of a larger change
- Include the commit SHAs that contributed to each change"""

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=RepositoryAnalysis,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    return result


def process_batch_and_extend(
    commits: List[Dict[str, Any]],
    commit_diffs: Dict[str, List[Dict[str, Any]]],
    all_changes: List[Dict[str, Any]],
    repo_path: str,
    repo_context: Optional[Dict[str, Any]],
    model_name: str,
    token_budget: Optional[int] = None
) -> None:
    """Process a batch of commits and extend all_changes with results."""
    batch_context = build_commit_context(commits, commit_diffs, token_budget)
    result = analyze_batch(repo_path, batch_context, repo_context, model_name)
    if result:
        all_changes.extend([c.model_dump(by_alias=True) for c in result.changes])


def process_small_days_batch(
    small_days: List[tuple],
    commit_diffs: Dict[str, List[Dict[str, Any]]],
    all_changes: List[Dict[str, Any]],
    repo_path: str,
    repo_context: Optional[Dict[str, Any]],
    model_name: str,
    batch_threshold: int = 90000
) -> None:
    """Process small days in batches, grouping them until threshold is reached."""
    current_batch = []
    current_tokens = 0
    
    for day, day_commits, day_tokens in small_days:
        # If adding this day exceeds threshold, process current batch first
        if current_batch and (current_tokens + day_tokens > batch_threshold):
            process_batch_and_extend(
                current_batch, commit_diffs, all_changes,
                repo_path, repo_context, model_name
            )
            current_batch = []
            current_tokens = 0
        
        current_batch.extend(day_commits)
        current_tokens += day_tokens
    
    # Process remaining batch
    if current_batch:
        process_batch_and_extend(
            current_batch, commit_diffs, all_changes,
            repo_path, repo_context, model_name
        )


def process_repository(
    repo_path: str,
    activity_data: Dict[str, Any],
    repo_context: Optional[Dict[str, Any]],
    headers: dict,
    model_name: str
) -> Dict[str, Any]:
    """Process a single repository's activity with tiered splitting strategy."""
    
    commits = activity_data.get("commits", [])
    
    if not commits:
        print(f"   No commits for {repo_path}")
        return {
            "repository": repo_path,
            "changes": []
        }
    
    # Fetch all diffs first
    print(f"   Fetching diffs for {len(commits)} commits...")
    commit_diffs = {}
    for commit in commits:
        sha = commit.get("sha", "")
        if sha:
            diffs = fetch_commit_diff(repo_path, sha, headers)
            if diffs:
                commit_diffs[sha] = diffs
    
    # Calculate total tokens
    full_context = build_commit_context(commits, commit_diffs)
    total_tokens = estimate_tokens(full_context)
    print(f"   Total estimated tokens: {total_tokens}")
    
    all_changes = []
    
    # Tier 1: Single call (< 100K tokens)
    if total_tokens < TIER_1_THRESHOLD:
        print(f"   Using Tier 1 (single call)")
        process_batch_and_extend(
            commits, commit_diffs, all_changes,
            repo_path, repo_context, model_name
        )
    
    # Tier 2: Split by day (100K - 700K tokens)
    elif total_tokens < TIER_2_THRESHOLD:
        print(f"   Using Tier 2 (split by day)")
        commits_by_day = group_commits_by_day(commits)
        sorted_days = sorted(commits_by_day.keys())
        
        # Build list of (day, day_commits, day_tokens) tuples
        day_data = []
        for day in sorted_days:
            day_commits = commits_by_day[day]
            day_context = build_commit_context(day_commits, commit_diffs)
            day_tokens = estimate_tokens(day_context)
            day_data.append((day, day_commits, day_tokens))
        
        # Process small days in batches
        process_small_days_batch(
            day_data, commit_diffs, all_changes,
            repo_path, repo_context, model_name
        )
    
    # Tier 3: Hybrid approach (> 700K tokens)
    else:
        print(f"   Using Tier 3 (hybrid approach)")
        commits_by_day = group_commits_by_day(commits)
        sorted_days = sorted(commits_by_day.keys())
        
        # First, calculate tokens for each day and separate into large and small days
        large_days = []  # Days > TIER_1_THRESHOLD
        small_days = []  # Days <= TIER_1_THRESHOLD
        
        for day in sorted_days:
            day_commits = commits_by_day[day]
            day_context = build_commit_context(day_commits, commit_diffs)
            day_tokens = estimate_tokens(day_context)
            
            if day_tokens > TIER_1_THRESHOLD:
                large_days.append((day, day_commits, day_tokens))
            else:
                small_days.append((day, day_commits, day_tokens))
        
        # Process large days individually (with compression if needed)
        for day, day_commits, day_tokens in large_days:
            if day_tokens > TIER_1_THRESHOLD:
                # Compress day to fit within budget
                budget_per_commit = TIER_1_THRESHOLD // len(day_commits)
                process_batch_and_extend(
                    day_commits, commit_diffs, all_changes,
                    repo_path, repo_context, model_name,
                    token_budget=budget_per_commit
                )
        
        # Process small days in batches (like Tier 2)
        process_small_days_batch(
            small_days, commit_diffs, all_changes,
            repo_path, repo_context, model_name
        )
    
    return {
        "repository": repo_path,
        "changes": all_changes
    }


# Main execution
github_activity_data = waveassist.fetch_data("github_activity_data", default={})
repository_contexts = waveassist.fetch_data("repository_contexts", default={})
github_access_token = waveassist.fetch_data("github_access_token", default="")
model_name = waveassist.fetch_data("model_name", default="anthropic/claude-haiku-4.5")

headers = {
    "Authorization": f"token {github_access_token}",
    "Accept": "application/vnd.github+json",
}

repository_analyses = []
if not isinstance(github_activity_data, dict):
    github_activity_data = {}
if not isinstance(repository_contexts, dict):
    repository_contexts = {}

for repo_path, activity_data in github_activity_data.items():
    print(f"🔍 Analyzing {repo_path}...")
    
    try:
        repo_context = repository_contexts.get(repo_path)
        
        analysis = process_repository(
            repo_path,
            activity_data,
            repo_context,
            headers,
            model_name
        )
        
        repository_analyses.append(analysis)
        print(f"✅ Analysis complete for {repo_path}: {len(analysis['changes'])} changes identified")

    except Exception as e:
        print(f"❌ Error analyzing {repo_path}: {e}")
        repository_analyses.append({
            "repository": repo_path,
            "changes": []
        })

    waveassist.store_data("repository_analyses", repository_analyses, data_type="json")

# Store analyses (final store already done per-repo)

total_changes = sum(len(a["changes"]) for a in repository_analyses)
print(f"✅ Analysis complete: {total_changes} total changes across {len(repository_analyses)} repositories")
print("GitFlow: Repository activity analysis completed.")

