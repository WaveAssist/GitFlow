import requests
import time
import waveassist
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting GitHub activity fetch...")

# Time range: past 7 days
DAYS_TO_FETCH = 7


def is_bot_user(user: Dict[str, Any]) -> bool:
    """Check if a user is a bot."""
    if not user:
        return False
    
    # Check type field
    if user.get("type") == "Bot":
        return True
    
    login = (user.get("login") or "").lower()
    
    # Check for [bot] suffix
    if login.endswith("[bot]"):
        return True
    
    # Common bot names
    common_bots = [
        "dependabot", "renovate", "github-actions", "codecov",
        "greenkeeper", "snyk-bot", "mergify", "stale",
        "allcontributors", "imgbot", "semantic-release-bot",
        "renovate-bot", "dependabot-preview"
    ]
    
    return login in common_bots


def fetch_branches_with_dates(repo_path: str, headers: dict) -> List[Dict[str, str]]:
    """Fetch all branches with their latest commit dates using GraphQL with pagination."""
    # Parse owner and repo name from repo_path
    parts = repo_path.split("/")
    if len(parts) != 2:
        print(f"⚠️ Invalid repo path format: {repo_path}")
        return []
    
    owner, name = parts
    
    # GraphQL query to fetch branches with latest commit dates (with pagination)
    graphql_query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        refs(refPrefix: "refs/heads/", first: 100, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            target {
              ... on Commit {
                committedDate
              }
            }
          }
        }
      }
    }
    """
    
    graphql_url = "https://api.github.com/graphql"
    all_branches = []
    cursor = None
    page = 1
    
    try:
        while True:
            payload = {
                "query": graphql_query,
                "variables": {
                    "owner": owner,
                    "name": name,
                    "cursor": cursor
                }
            }
            
            response = requests.post(graphql_url, headers=headers, json=payload)
            
            # Rate limiting: sleep between API calls
            time.sleep(0.5)
            
            if response.status_code != 200:
                print(f"⚠️ Failed to fetch branches via GraphQL: {response.status_code}")
                break
            
            data = response.json()
            
            if "errors" in data:
                print(f"⚠️ GraphQL errors: {data['errors']}")
                break
            
            refs_data = data.get("data", {}).get("repository", {}).get("refs", {})
            branches_data = refs_data.get("nodes", [])
            page_info = refs_data.get("pageInfo", {})
            
            # Process branches from this page
            for branch in branches_data:
                branch_name = branch.get("name", "")
                committed_date = branch.get("target", {}).get("committedDate", "")
                if branch_name and committed_date:
                    all_branches.append({
                        "name": branch_name,
                        "committedDate": committed_date
                    })
            
            # Check if there are more pages
            has_next_page = page_info.get("hasNextPage", False)
            if not has_next_page:
                break
            
            cursor = page_info.get("endCursor")
            page += 1
            
            # Safety limit: prevent infinite loops
            if page > 50:  # Max 50 pages = 5,000 branches
                print(f"   ⚠️ Reached pagination limit (50 pages)")
                break
        
        return all_branches
        
    except Exception as e:
        print(f"❌ Error fetching branches via GraphQL: {e}")
        return all_branches  # Return what we've collected so far


def filter_active_branches(branches: List[Dict[str, str]], since: datetime) -> List[str]:
    """Filter branches that have commits after the 'since' date."""
    if not branches:
        return []
    
    since_iso = since.isoformat()
    active_branches = []
    
    for branch in branches:
        committed_date = branch.get("committedDate", "")
        if committed_date and committed_date > since_iso:
            active_branches.append(branch["name"])
    
    return active_branches


def fetch_commits(repo_path: str, headers: dict, branch_name: str, since: datetime) -> List[Dict[str, Any]]:
    """Fetch commits from a single branch using REST API with pagination."""
    commits_url = f"https://api.github.com/repos/{repo_path}/commits"
    
    commit_list = []
    page = 1
    per_page = 100
    
    try:
        while True:
            params = {
                "sha": branch_name,
                "since": since.isoformat(),
                "per_page": per_page,
                "page": page,
            }
            
            response = requests.get(commits_url, headers=headers, params=params)
            
            # Rate limiting: sleep between API calls
            time.sleep(0.5)
            
            if response.status_code != 200:
                print(f"   ⚠️ Failed to fetch commits from branch '{branch_name}' page {page}: {response.status_code}")
                break
            
            commits = response.json()
            if not commits:
                break
            
            for commit in commits:
                sha = commit.get("sha", "")
                
                # Skip commits with empty SHA
                if not sha:
                    continue
                
                # Filter out bot commits
                author = commit.get("author") or {}
                committer = commit.get("committer") or {}
                commit_data = commit.get("commit", {})
                
                if is_bot_user(author) or is_bot_user(committer):
                    continue
                
                # Extract commit info
                commit_info = {
                    "sha": sha,
                    "message": commit_data.get("message", ""),
                    "author": author.get("login") if author else commit_data.get("author", {}).get("name", "Unknown"),
                    "timestamp": commit_data.get("author", {}).get("date", ""),
                    "url": commit.get("html_url", ""),
                }
                commit_list.append(commit_info)
            
            # Check if there are more pages (if we got fewer than per_page, we're done)
            if len(commits) < per_page:
                break
            
            page += 1
            
            # Safety limit: prevent excessive pagination
            if page > 10:  # Max 10 pages = 1,000 commits per branch
                print(f"   ⚠️ Reached commit pagination limit (10 pages) for branch '{branch_name}'")
                break
        
        return commit_list
        
    except Exception as e:
        print(f"   ⚠️ Error fetching commits from branch '{branch_name}': {e}")
        return commit_list  # Return what we've collected so far


def fetch_pull_requests(repo_path: str, headers: dict, since: datetime) -> List[Dict[str, Any]]:
    """Fetch open and recently merged PRs."""
    all_prs = []
    states = ["open", "closed"]
    
    pr_url = f"https://api.github.com/repos/{repo_path}/pulls"
    
    for state in states:
        params = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": 100,
        }
        
        response = requests.get(pr_url, headers=headers, params=params)
        
        # Rate limiting: sleep between API calls
        time.sleep(0.5)
        
        if response.status_code != 200:
            continue
        
        try:
            prs = response.json()
            for pr in prs:
                # Filter out bot PRs
                user = pr.get("user") or {}
                if is_bot_user(user):
                    continue
                
                # Check created_at, merged_at, and updated_at
                created_at = pr.get("created_at", "")
                merged_at = pr.get("merged_at") or ""
                updated_at = pr.get("updated_at", "")
                
                # Include PR if created, merged, or updated within the time window
                should_include = False
                
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if created_dt >= since:
                            should_include = True
                    except:
                        pass
                
                if not should_include and merged_at:
                    try:
                        merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
                        if merged_dt >= since:
                            should_include = True
                    except:
                        pass
                
                if not should_include and updated_at:
                    try:
                        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        if updated_dt >= since:
                            should_include = True
                    except:
                        pass
                
                if not should_include:
                    continue
                
                pr_info = {
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "description": pr.get("body", "") or "",
                    "status": state,
                    "author": user.get("login", "Unknown"),
                    "timestamp": pr.get("created_at", ""),
                    "created_at": created_at,
                    "merged_at": merged_at,
                    "updated_at": updated_at,
                    "url": pr.get("html_url", ""),
                    "head_sha": pr.get("head", {}).get("sha", ""),
                    "base_branch": pr.get("base", {}).get("ref", ""),
                }
                all_prs.append(pr_info)  
        except Exception as e:
            print(f"⚠️ Error parsing {state} PRs for {repo_path}: {e}")
    
    return all_prs


# Main execution
github_selected_resources = waveassist.fetch_data("github_selected_resources", default=[])
github_access_token = waveassist.fetch_data("github_access_token", default="")

headers = {
    "Authorization": f"token {github_access_token}",
    "Accept": "application/vnd.github+json",
}

# Calculate time range
end_date = datetime.now(timezone.utc)
since = end_date - timedelta(days=DAYS_TO_FETCH)
start_date = since

github_activity_data = {}
if not isinstance(github_selected_resources, list):
    github_selected_resources = []

for repo in github_selected_resources:
    repo_path = repo.get("id") if isinstance(repo, dict) else repo
    
    if not repo_path:
        continue
    
    print(f"📊 Fetching activity for {repo_path}...")
    
    try:
        # Fetch branches and filter for active ones
        print(f"   Fetching branches for {repo_path}...")
        branches = fetch_branches_with_dates(repo_path, headers)
        
        if not branches:
            print(f"   No branches found or error fetching branches")
            active_branches = []
        else:
            print(f"   Found {len(branches)} branches")
            active_branches = filter_active_branches(branches, since)
            
            if not active_branches:
                print(f"   No branches with recent activity (after {since.isoformat()})")
            else:
                print(f"   Found {len(active_branches)} branches with recent activity")
        
        # Fetch commits from active branches
        all_commits = []
        seen_shas = set()
        
        for branch_name in active_branches:
            branch_commits = fetch_commits(repo_path, headers, branch_name, since)
            
            for commit in branch_commits:
                sha = commit.get("sha", "")
                # Skip if we've already seen this commit (deduplication)
                if sha and sha not in seen_shas:
                    all_commits.append(commit)
                    seen_shas.add(sha)
        
        commits = all_commits
        print(f"   Commits: {len(commits)}")
        
        # Fetch PRs
        pull_requests = fetch_pull_requests(repo_path, headers, since)
        print(f"   Pull Requests: {len(pull_requests)}")
        
        github_activity_data[repo_path] = {
            "commits": commits,
            "pull_requests": pull_requests,
        }
        
        print(f"✅ Fetched activity for {repo_path}")

    except Exception as e:
        print(f"❌ Error fetching activity for {repo_path}: {e}")
        github_activity_data[repo_path] = {
            "commits": [],
            "pull_requests": [],
        }

    waveassist.store_data("github_activity_data", github_activity_data, data_type="json")

# Store report date range for email display
report_date_range = {
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "start_date_formatted": start_date.strftime("%B %d, %Y"),
    "end_date_formatted": end_date.strftime("%B %d, %Y"),
}
waveassist.store_data("report_date_range", report_date_range, data_type="json")

# Calculate totals for logging
total_commits = sum(len(data["commits"]) for data in github_activity_data.values())
total_prs = sum(len(data["pull_requests"]) for data in github_activity_data.values())

print(f"✅ Fetched GitHub activity: {total_commits} commits, {total_prs} PRs across {len(github_activity_data)} repositories")
print(f"📅 Report period: {report_date_range['start_date_formatted']} - {report_date_range['end_date_formatted']}")
print("GitFlow: GitHub activity fetch completed.")

