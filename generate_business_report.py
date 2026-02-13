import waveassist
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting business report generation...")

# LLM settings
max_tokens = 2500
temperature = 0.4


class BusinessReport(BaseModel):
    """Model for the business report - identifies headline features (The Signal)"""
    executive_summary: str = Field(description="2 sentences on the week's biggest impact")
    shipped_features: List[str] = Field(description="Top 1-3 user-facing capabilities completed")


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

# Note: Business report no longer uses PR context - focuses on code changes only


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


def build_history_context(business_report_history: List[Dict[str, Any]]) -> str:
    """Build context from historical business reports."""
    if not business_report_history:
        return ""
    
    parts = ["Previous week's business report, provided only for context:"]
    
    # Get previous week(s) (history contains at most 1 previous week)
    for entry in business_report_history:
        week = entry.get("week", "Unknown")
        report = entry.get("report", {})
        parts.append(f"Week of {week}:\n{json.dumps(report, default=str, ensure_ascii=False, separators=(',', ':'))}")
    
    return "\n---\n".join(parts)

def build_prompt(
        project_name: str,
        analysis_context: str,
        history_context: str = "",
        pull_requests_context: str = "",
        changes_context: str = ""
) -> str:
    # Note: pull_requests_context parameter kept for compatibility but not used

    prompt_parts = [
        (
            "You are a business-focused advisor reporting to a busy CEO. "
            f"Review the development activity for {project_name}. "
            "Your goal is to extract the 2-3 biggest/significant features/user-facing wins. Ignore the plumbing. "
            "If a section has no significant updates, strictly return an empty list."
        )
    ]

    if history_context:
        prompt_parts.append("\n<Previous Report Context>\n" + history_context)

    if analysis_context:
        prompt_parts.append("\n<Repo Summaries Context>\n" + analysis_context)

    if changes_context:
        prompt_parts.append("\n*** PRIMARY SOURCE: Code Changes Summarized: ***\n" + changes_context)

    prompt_parts.append("""
Create a concise business report identifying the headline features (The Signal).

**CRITICAL INSTRUCTIONS:**
- **Extract Headlines Only:** Focus on the 2-3 biggest/significant features/user-facing. Ignore internal refactors, bug fixes, and technical improvements unless they directly enable major new capabilities.
- **Translate to Business Value:** Convert technical changes into user-facing benefits and business outcomes.
- **Filter Noise:** Skip plumbing, maintenance, and minor improvements.
- **Tone:** Professional, clear, and outcome-focused.

1. **executive_summary**: 
   - Exactly 2 sentences on the week's biggest impact.
   - Focus on outcomes and impact, not technical details.

2. **shipped_features**: 
   - **MAXIMUM 3 POINTS** (ideally 1-3).
   - Top user-facing capabilities that are completed and ready for users.
   - Translate technical work into user-facing benefits using simple language.

Guidelines:
- Write for a busy CEO
- Avoid jargon and technical terms
- Focus on business impact and user value
- Be honest but positive
- Keep each list item to 1-2 sentence
- Use plain language a CEO would understand
""")

    return "".join(prompt_parts)


# Main execution
repository_analyses = waveassist.fetch_data("repository_analyses", default=[])
github_activity_data = waveassist.fetch_data("github_activity_data", default={})
repository_contexts = waveassist.fetch_data("repository_contexts", default={})
project_name = waveassist.fetch_data("project_name", default="Project")
business_report_history = waveassist.fetch_data("business_report_history", default=[])
model_name = waveassist.fetch_data("model_name", default="anthropic/claude-haiku-4.5")

# Check if there's any activity to report
total_changes = sum(len(a.get("changes", [])) for a in repository_analyses)

if total_changes == 0:
    print("No activity to report this week.")
    business_report = {
        "executive_summary": f"No development activity was recorded for {project_name} this week.",
        "shipped_features": []
    }
    waveassist.store_data("business_report", business_report, data_type="json")
    print("GitFlow: Business report generation completed (no activity).")
else:
    # Build context
    analysis_context = build_analysis_context(repository_analyses, repository_contexts)
    history_context = build_history_context(business_report_history)
    changes_context = build_changes_context(repository_analyses)
    
    
    # Generate prompt
    prompt = build_prompt(project_name, analysis_context, history_context, "", changes_context)

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=BusinessReport,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    if result:
        business_report = result.model_dump(by_alias=True)
        
        waveassist.store_data("business_report", business_report, data_type="json")
        print(f"✅ Business report generated")

        # Update business report history
        current_week = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Keep only last 1 week, then append current week (total: 2 weeks)
        history_list = business_report_history if isinstance(business_report_history, list) else []
        history_list = history_list[-1:]
        history_list.append({
            "week": current_week,
            "report": business_report
        })
        waveassist.store_data("business_report_history", history_list, data_type="json")

    else:
        print("⚠️ Failed to generate business report, using fallback")
        business_report = {
            "executive_summary": f"Development activity was recorded for {project_name} this week but report generation encountered an issue.",
            "shipped_features": []
        }
        waveassist.store_data("business_report", business_report, data_type="json")

print("GitFlow: Business report generation completed.")

