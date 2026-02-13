import waveassist
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting technical report generation...")

# LLM settings
max_tokens = 6000
temperature = 0.4


class RepoUpdate(BaseModel):
    """Technical update for a single repository"""
    repo_name: str = Field(description="Repository name (owner/repo)")
    status: str = Field(description="1-2 words describing the repo's status (e.g., 'Heavy Refactor', 'Maintenance', 'Feature Dev')")
    technical_changes: List[str] = Field(description="List of specific fixes/improvements in this repo. MAXIMUM 2-3 points per repo.")


class TechnicalReport(BaseModel):
    """Model for the technical report - repository deep dive"""
    repository_deep_dive: List[RepoUpdate] = Field(description="Updates grouped by repository")
    poem: List[str] = Field(description="4 lines, tech-focused, rhyming, each 6-10 words")


def build_repo_context_section(repo: str, repo_context: Optional[Dict[str, Any]]) -> str:
    """Build repository context section (summary and stack)."""
    if not repo_context:
        return ""
    
    return f"""
---
Repository Context for: {repo}    
- Summary: {repo_context.get('summary', 'N/A')}
- Stack: {repo_context.get('stack', 'N/A')}
---
"""


def build_changes_context(repository_analyses: List[Dict[str, Any]]) -> str:
    """Build changes context across all repositories."""
    result = {}
    
    for analysis in repository_analyses:
        repo = analysis.get("repository", "Unknown")
        changes = analysis.get("changes", [])
        if not changes:
            continue
        result[repo] = changes
    return json.dumps(
        result,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
    ) if result else ""


def build_analysis_context(
    repository_analyses: List[Dict[str, Any]],
    repository_contexts: Dict[str, Dict[str, Any]]
) -> str:
    """Build repository context section (summary and stack) for all repositories."""
    parts = []
    
    # Only include repositories that have changes
    repos_with_activity = {
        analysis.get("repository") 
        for analysis in repository_analyses 
        if analysis.get("changes", [])
    }
    
    for repo in repos_with_activity:
        repo_context = repository_contexts.get(repo)
        if not repo_context:
            continue
        
        repo_section = build_repo_context_section(repo, repo_context)
        parts.append(repo_section)
    
    return "\n---\n".join(parts) if parts else ""


# Note: History context removed - technical report now focuses on current week with business report context

def build_business_report_context(business_report: Dict[str, Any]) -> str:
    """Build context from business report to inform technical report."""
    if not business_report:
        return ""
    
    parts = ["The Business Report has already summarised the headline features. Focus on repository-specific technical details: "]
    
    executive_summary = business_report.get("executive_summary", "")
    shipped_features = business_report.get("shipped_features", [])
    
    if executive_summary:
        parts.append(f"Executive Summary: {executive_summary}")
    
    if shipped_features:
        parts.append(f"Shipped Features: {json.dumps(shipped_features, ensure_ascii=False)}")
    
    return "\n".join(parts)


def build_prompt(
        project_name: str,
        analysis_context: str,
        business_report_context: str = "",
        changes_context: str = ""
) -> str:

    prompt_parts = [
        (
            "You are a technical advisor reporting to a busy CTO. "
            f"Review the development activity for {project_name}. "
            "The Business Report already covered the big features. "
            "Now, go Repository by Repository. List the technical improvements, bug fixes, and refactors that matter. "
            "If a section has no significant updates, strictly return an empty list."
        )
    ]

    if business_report_context:
        prompt_parts.append("\n<Business Report Context>\n" + business_report_context)

    if analysis_context:
        prompt_parts.append("\n<Repo Summaries Context>\n" + analysis_context)

    if changes_context:
        prompt_parts.append("\n*** PRIMARY SOURCE: Code Changes Summarized: ***\n" + changes_context)

    prompt_parts.append("""
Create a repository-by-repository technical deep dive with the following structure.

**CRITICAL INSTRUCTIONS:**
- **Repository Focus:** Go through each repository that had activity and list what happened there.
- **Aggressively Consolidate:** Do not list individual commits. Group related changes.
- **Filter Noise:** Ignore trivial changes like typos, minor formatting, or dependency bumps unless they cause a major version shift.
- **Tone:** Professional, telegraphic, and direct.
- **Business Report Context:** Use the Business Report context to inform the technical report.
- **Limit Points:** MAXIMUM 2-3 technical changes per repository to ensure readability.

1. **repository_deep_dive**: 
   - List of RepoUpdate objects, one per repository with activity.
   - Each RepoUpdate contains:
     - **repo_name**: Repository identifier (owner/repo)
     - **status**: 1-2 words describing the repo's status (e.g., "Heavy Refactor", "Maintenance", "Feature Dev", "Bug Fixes", "Architecture" etc..)
     - **technical_changes**: List of MAXIMUM 2-3 specific technical improvements, bug fixes, or refactors in this repo

2. **poem**:
   - Exactly 4 lines, each 6-10 words, written for this week's activity. 
   - Tech-focused, rhyming, and abstract. No need to cover everything that happened, but as a nice touch. 
   - Keep all 4 lines connected to each other. Its one poem. Refer to business report context as well. 
   - Technical-flavored but abstract. 
""")

    return "".join(prompt_parts)


# Main execution
repository_analyses = waveassist.fetch_data("repository_analyses", default=[])
repository_contexts = waveassist.fetch_data("repository_contexts", default={})
project_name = waveassist.fetch_data("project_name", default="Project")
business_report = waveassist.fetch_data("business_report", default={})
model_name = waveassist.fetch_data("model_name", default="anthropic/claude-haiku-4.5")

# Check if there's any activity to report
total_changes = sum(len(a.get("changes", [])) for a in repository_analyses)

if total_changes == 0:
    print("No activity to report this week.")
    technical_report = {
        "repository_deep_dive": [],
        "poem": [
            "Quiet repos rest, untouched branches dreaming of merge lights",
            "Product sleeps softly, backlog whispers promises for next sprint",
            "Engineers sip coffee, plotting fresh commits for Monday",
            "Calm before velocity, waiting for ideas to spark"
        ]
    }
    waveassist.store_data("technical_report", technical_report, data_type="json")
    print("GitFlow: Technical report generation completed (no activity).")
else:
    # Build context
    analysis_context = build_analysis_context(repository_analyses, repository_contexts)
    business_report_context = build_business_report_context(business_report)
    changes_context = build_changes_context(repository_analyses)
    
    
    # Generate prompt
    prompt = build_prompt(project_name, analysis_context, business_report_context, changes_context)

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=TechnicalReport,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    if result:
        technical_report = result.model_dump(by_alias=True)
        
        waveassist.store_data("technical_report", technical_report, data_type="json")
        print(f"✅ Technical report generated")

    else:
        print("⚠️ Failed to generate technical report, using fallback")
        technical_report = {
            "repository_deep_dive": [],
            "poem": [
                "Code stirred alive, but our report missed the landing",
                "Pull requests humming, summaries stuck in the drafts",
                "Signals await, dashboards quiet until errors fade",
                "We will retry soon, momentum stays in motion"
            ]
        }
        waveassist.store_data("technical_report", technical_report, data_type="json")

print("GitFlow: Technical report generation completed.")

