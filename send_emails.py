import html
import io
import waveassist
from datetime import datetime
from typing import Any, Dict, List, Optional

# WeasyPrint is used to generate a PDF attachment containing the full report.
# (WaveAssist email supports attachments via `attachment_file`.)
from weasyprint import HTML  # type: ignore

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting email generation...")


def _esc(value: Any) -> str:
    """Escape HTML entities."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _ul(items: List[str]) -> str:
    """Generate HTML unordered list."""
    if not items:
        return "<p class='muted'>None this week.</p>"
    return "<ul>" + "".join(f"<li>{_esc(item)}</li>" for item in items) + "</ul>"


def get_activity_summary(github_activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate activity summary statistics."""
    total_commits = 0
    contributors = set()
    if not isinstance(github_activity_data, dict):
        return {"total_commits": 0, "contributor_count": 0}
    for repo_path, data in github_activity_data.items():
        commits = data.get("commits", [])
        
        total_commits += len(commits)
        
        for commit in commits:
            author = commit.get("author")
            if author:
                contributors.add(author)
    
    return {
        "total_commits": total_commits,
        "contributor_count": len(contributors),
    }


def generate_pdf_attachment(html_content: str, project_name: str) -> tuple[Optional[io.BytesIO], str, Optional[str]]:
    """
    Generate a PDF attachment from HTML content.
    
    Returns:
        tuple: (pdf_file, pdf_filename, pdf_error)
        - pdf_file: BytesIO object with PDF content, or None if generation failed
        - pdf_filename: Name of the PDF file
        - pdf_error: Error message if generation failed, or None
    """
    pdf_filename = f"GitFlow_Report_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf_file = None
    pdf_error: Optional[str] = None
    
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
        pdf_file = io.BytesIO(pdf_bytes)
        setattr(pdf_file, "name", pdf_filename)
        pdf_file.seek(0)
    except Exception as e:
        pdf_error = f"WeasyPrint PDF generation failed: {e}"
        pdf_file = None
    
    return pdf_file, pdf_filename, pdf_error


# Note: get_repo_tags function removed - no longer needed for combined email


def build_combined_email(
    business_report: Dict[str, Any],
    technical_report: Dict[str, Any],
    project_name: str,
    activity_summary: Dict[str, Any],
    timestamp: str,
    repository_contexts: Dict[str, Dict[str, Any]],
    github_selected_resources: List[str],
    report_date_range: Optional[Dict[str, str]] = None
) -> str:
    """Build single combined HTML email with business summary at top and technical deep dive below."""
    
    # Business Report data
    executive_summary = business_report.get("executive_summary", "No summary available.")
    shipped_features = business_report.get("shipped_features", [])
    
    # Technical Report data
    repository_deep_dive = technical_report.get("repository_deep_dive", [])
    poem = technical_report.get("poem", [])
    
    # Count total repos and active repos (repos with changes)
    total_repos = len(github_selected_resources) if github_selected_resources else 0
    active_repos = 0
    if repository_deep_dive:
        for repo_update in repository_deep_dive:
            if isinstance(repo_update, dict):
                technical_changes = repo_update.get("technical_changes", [])
                if technical_changes:
                    active_repos += 1
    
    # Build SUMMARY section
    summary_html = f"<div class='summary-box'><p>{_esc(executive_summary)}</p></div>"
    
    # Build SHIPPED FEATURES section
    shipped_features_html = _ul(shipped_features) if shipped_features else "<p class='muted'>No features shipped this week.</p>"
    
    # Build REPOSITORY DEEP DIVE section
    repo_dive_html = ""
    if repository_deep_dive:
        for repo_update in repository_deep_dive:
            if isinstance(repo_update, dict):
                repo_name = repo_update.get("repo_name", "Unknown")
                status = repo_update.get("status", "")
                technical_changes = repo_update.get("technical_changes", [])
                
                # Get tags from repository_contexts
                repo_context = repository_contexts.get(repo_name, {})
                tags = repo_context.get("tags", [])
                tags_html = ""
                if tags:
                    tags_html = f"<div class='repo-tags'>{' '.join(f'<span class=\"tag\">{_esc(tag)}</span>' for tag in tags)}</div>"
                
                changes_list = _ul(technical_changes) if technical_changes else "<p class='muted'>No technical changes listed.</p>"
                
                repo_dive_html += f"""
                <div class="repo-card">
                    <h4>{_esc(repo_name)} <span class="repo-status">({_esc(status)})</span></h4>
                    {tags_html}
                    {changes_list}
                </div>
                """
    else:
        repo_dive_html = "<p class='muted'>No repository updates this week.</p>"
    
    # Build POEM section
    poem_html = ""
    if poem and isinstance(poem, list):
        poem_lines = [line for line in poem if line]
        if poem_lines:
            poem_html = (
                "<div class='poem'>"
                + "<h3 class='poem-heading'>Here is a small poem for this week's updates:</h3>"
                + "<div class='poem-content'>"
                + "<em>\""
                + "".join(f"<p class='poem-line'>{_esc(line)}</p>" for line in poem_lines)
                + "\"</em>"
                + "</div>"
                + "</div>"
            )
    
    report_period_html = ""
    try:
        if report_date_range and report_date_range.get("start_date_formatted"):
            report_period_html = f"<div class='subtitle'>Report Period: {_esc(report_date_range.get('start_date_formatted', ''))} - {_esc(report_date_range.get('end_date_formatted', ''))}</div>"
    except Exception:
        report_period_html = ""

    html_body = f"""
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            /* Email styles - original sizing */
            body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #0f172a; margin: 18px; }}
            .container {{ max-width: 700px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; border-top: 4px solid #1ED66C; overflow: hidden; }}
            .header {{ padding: 14px; border-bottom: 1px solid #e5e7eb; background: #ffffff; }}
            .header h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #0f1116; }}
            .header .subtitle {{ color: #6b7280; font-size: 12px; margin-top: 6px; }}
            .stats-bar {{ display: flex; gap: 16px; flex-wrap: wrap; background: #ffffff; padding: 16px 14px; border-bottom: 1px solid #e5e7eb; justify-content: space-between; }}
            .stat {{ text-align: center; flex: 1 1 140px; min-width: 140px; }}
            .stat-value {{ font-size: 24px; font-weight: 700; color: #1ED66C; margin-bottom: 4px; }}
            .stat-label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
            .content {{ padding: 14px; }}
            h2 {{ color: #0f1116; font-size: 20px; margin-top: 28px; padding: 10px 0 10px 12px; border-left: 4px solid #1ED66C; border-bottom: 1px solid #e5e7eb; }}
            h2:first-child {{ margin-top: 0; }}
            h3 {{ color: #0f1116; font-size: 14px; margin: 14px 0 8px 0; }}
            h4 {{ color: #0f1116; font-size: 14px; margin: 0 0 4px 0; }}
            p {{ margin: 8px 0; line-height: 1.45; color: #0f172a; }}
            ul {{ margin: 6px 0 10px 18px; padding: 0; }}
            li {{ margin: 4px 0; line-height: 1.45; color: #0f172a; }}
            .summary-box {{ background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb; border-left: 3px solid #1ED66C; margin-bottom: 20px; }}
            .summary-box p {{ margin: 0; font-size: 14px; color: #0f172a; line-height: 1.45; }}
            .section {{ margin-bottom: 24px; }}
            .repo-card {{ background: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #e5e7eb; border-left: 3px solid #1ED66C; margin: 10px 0; }}
            .repo-card h4 {{ color: #0f1116; }}
            .repo-status {{ color: #6b7280; font-weight: normal; font-size: 12px; }}
            .repo-tags {{ margin: 6px 0 8px 0; }}
            .tag {{ display: inline-block; background-color: #e1f5fe; color: #0277bd; font-size: 11px; padding: 3px 8px; margin-right: 6px; margin-bottom: 4px; border-radius: 12px; }}
            .muted {{ color: #6b7280; font-size: 12px; }}
            .success {{ color: #148F47; font-weight: 500; }}
            .poem {{ background: #f9fafb; padding: 16px; border-radius: 8px; border-left: 3px solid #1ED66C; margin: 20px 0; }}
            .poem-heading {{ color: #0f1116; font-size: 14px; margin: 0 0 12px 0; font-weight: 500; }}
            .poem-content {{ margin: 0; }}
            .poem-line {{ margin: 2px 0; color: #374151; line-height: 1.4; font-style: italic; }}
            .footer {{ text-align: center; padding: 20px; background: #ffffff; border-top: 1px solid #e5e7eb; }}
            .footer p {{ margin: 4px 0; font-size: 12px; color: #6b7280; }}
            
            /* PDF-specific adjustments - middle ground */
            @page {{
                margin: 0.75in;
                size: letter;
            }}
            @media print {{
                body {{ margin: 0; padding: 0; font-size: 12px; }}
                .container {{ max-width: 100%; width: 100%; border-radius: 8px; }}
                .header {{ padding: 12px; }}
                .header h1 {{ font-size: 21px; }}
                .header .subtitle {{ font-size: 12px; }}
                .stats-bar {{ padding: 14px 12px; gap: 14px; }}
                .stat-value {{ font-size: 23px; }}
                .stat-label {{ font-size: 11px; }}
                .content {{ padding: 12px; }}
                h2 {{ font-size: 19px; margin-top: 24px; padding: 8px 0 8px 10px; }}
                h3 {{ font-size: 14px; margin: 12px 0 7px 0; }}
                h4 {{ font-size: 14px; }}
                p {{ font-size: 12px; margin: 7px 0; }}
                li {{ font-size: 12px; }}
                .summary-box {{ padding: 11px; margin-bottom: 18px; }}
                .summary-box p {{ font-size: 12px; }}
                .repo-card {{ padding: 11px; margin: 9px 0; }}
                .repo-status {{ font-size: 12px; }}
                .tag {{ font-size: 11px; padding: 2px 7px; }}
                .poem {{ padding: 14px; margin: 18px 0; }}
                .poem-heading {{ font-size: 14px; }}
                .poem-line {{ font-size: 12px; }}
                .footer {{ padding: 18px; }}
                .footer p {{ font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Weekly Update: {_esc(project_name)}</h1>
                {report_period_html}
            </div>
            
            <div class="stats-bar">
                <div class="stat">
                    <div class="stat-value">{activity_summary.get('total_commits', 0)}</div>
                    <div class="stat-label">Commits</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{activity_summary.get('contributor_count', 0)}</div>
                    <div class="stat-label">Contributors</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{total_repos}</div>
                    <div class="stat-label">Total Repos</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{active_repos}</div>
                    <div class="stat-label">Active Repos</div>
                </div>
            </div>
            
            <div class="content">
                <h2>SUMMARY</h2>
                {summary_html}
                
                <h2>🚀 PRIMARY UPDATES</h2>
                {shipped_features_html}
                
                <h2>🛠️ REPOSITORY DEEP DIVE</h2>
                {repo_dive_html}
                
                {poem_html if poem_html else ""}
            </div>
            
            <div class="footer">
                <p>Generated by <a href="https://gitzoid.com" style="color: #1ED66C; text-decoration: none;">GitFlow</a> · Powered by <a href="https://waveassist.io" style="color: #1ED66C; text-decoration: none;">WaveAssist</a></p>
                <p>This is an automated weekly report</p>
                <p class="muted" style="margin-top: 12px; font-size: 11px;">A PDF version of this report is attached for easier sharing and printing.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_body


# Main execution
technical_report = waveassist.fetch_data("technical_report", default={})
business_report = waveassist.fetch_data("business_report", default={})
github_activity_data = waveassist.fetch_data("github_activity_data", default={})
repository_contexts = waveassist.fetch_data("repository_contexts", default={})
report_date_range = waveassist.fetch_data("report_date_range", default={})
project_name = waveassist.fetch_data("project_name", default="Project")
github_selected_resources = waveassist.fetch_data("github_selected_resources", default=[])

# Generate timestamp
timestamp = datetime.now().strftime("%B %d, %Y")

# Coerce types for upstream data
if not isinstance(technical_report, dict):
    technical_report = {}
if not isinstance(business_report, dict):
    business_report = {}
if not isinstance(github_activity_data, dict):
    github_activity_data = {}
if not isinstance(repository_contexts, dict):
    repository_contexts = {}
if not isinstance(report_date_range, dict):
    report_date_range = {}
if not isinstance(github_selected_resources, list):
    github_selected_resources = []
project_name = str(project_name) if project_name is not None else "Project"

# Get activity summary
activity_summary = get_activity_summary(github_activity_data)
total_commits_safe = activity_summary.get("total_commits", 0)
contributor_count_safe = activity_summary.get("contributor_count", 0)
try:
    total_commits_int = int(total_commits_safe) if total_commits_safe is not None else 0
except (TypeError, ValueError):
    total_commits_int = 0

# Check if there's anything to report
has_activity = total_commits_int > 0

try:
    if not has_activity:
        # Send a simple "no activity" email
        date_range_text = ""
        if report_date_range and report_date_range.get('start_date_formatted'):
            date_range_text = f"<p style='color: #6b7280; font-size: 12px; margin-top: 8px;'>Report Period: {_esc(report_date_range.get('start_date_formatted', ''))} - {_esc(report_date_range.get('end_date_formatted', ''))}</p>"

        no_activity_html = f"""
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            /* Email styles - original sizing */
            body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #0f172a; margin: 18px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 40px; text-align: center; border: 1px solid #e5e7eb; border-top: 4px solid #1ED66C; }}
            h1 {{ color: #0f1116; font-size: 22px; margin-bottom: 16px; }}
            p {{ color: #0f172a; line-height: 1.45; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #6b7280; }}
            
            /* PDF-specific adjustments - middle ground */
            @page {{
                margin: 0.75in;
                size: letter;
            }}
            @media print {{
                body {{ margin: 0; padding: 0; font-size: 12px; }}
                .container {{ max-width: 100%; width: 100%; border-radius: 8px; padding: 35px; }}
                h1 {{ font-size: 21px; margin-bottom: 14px; }}
                p {{ font-size: 12px; }}
                .footer {{ font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 {_esc(project_name)} - Weekly Report</h1>
            <p>No development activity was recorded across your tracked repositories this week.</p>
            {date_range_text}
            <p class="footer">Generated by <a href="https://gitzoid.com" style="color: #1ED66C; text-decoration: none;">GitFlow</a></p>
        </div>
    </body>
    </html>
        """

        subject = f"GitFlow: {project_name} - No Activity This Week"

        # Generate PDF attachment
        pdf_file, pdf_filename, pdf_error = generate_pdf_attachment(no_activity_html, project_name)

        email_sent = waveassist.send_email(
            subject=subject, html_content=no_activity_html, attachment_file=pdf_file, raise_on_failure=False
        )
        display_output = {
            "title": subject,
            "html_content": no_activity_html,
            "status": "email_failed" if not email_sent else "success",
            "pdf_attachment": {
                "enabled": True,
                "file_name": pdf_filename,
                "generated": pdf_file is not None,
                "error": pdf_error,
            },
        }
        waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
        print("GitFlow: No activity email sent." if email_sent else "GitFlow: No activity email send failed.")

    else:
        # Validate reports before sending
        business_report_valid = (
            isinstance(business_report, dict) and
            business_report.get("executive_summary") and
            isinstance(business_report.get("shipped_features"), list)
        )
        
        technical_report_valid = (
            isinstance(technical_report, dict) and
            isinstance(technical_report.get("repository_deep_dive"), list) and
            isinstance(technical_report.get("poem"), list)
        )
        
        if not business_report_valid or not technical_report_valid:
            error_msg = "Reports were not generated successfully. "
            if not business_report_valid:
                error_msg += "Business report is missing or invalid. "
            if not technical_report_valid:
                error_msg += "Technical report is missing or invalid."
            
            fallback_html = f"<p>{_esc(error_msg)}</p><p>Please check the workflow logs for details.</p>"
            display_output = {
                "html_content": fallback_html,
                "status": "report_validation_failed",
                "error": error_msg,
            }
            waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
            print(f"GitFlow: Report validation failed - {error_msg}. Email not sent.")
        else:
            # Build and send combined email
            print("Generating combined weekly update email...")
            combined_html = build_combined_email(
                business_report,
                technical_report,
                project_name,
                activity_summary,
                timestamp,
                repository_contexts,
                github_selected_resources,
                report_date_range
            )

            subject = f"Weekly Update: {project_name}"

            # Generate PDF attachment
            pdf_file, pdf_filename, pdf_error = generate_pdf_attachment(combined_html, project_name)

            print("GitFlow: Sending email with PDF attachment...")
            email_sent = waveassist.send_email(
                subject=subject, html_content=combined_html, attachment_file=pdf_file, raise_on_failure=False
            )
            print("Weekly update email sent." if email_sent else "Weekly update email send failed.")

            display_output = {
                "title": subject,
                "html_content": combined_html,
                "status": "email_failed" if not email_sent else "success",
                "summary": {
                    "commits": activity_summary.get("total_commits", 0),
                    "contributors": activity_summary.get("contributor_count", 0),
                },
                "pdf_attachment": {
                    "enabled": True,
                    "file_name": pdf_filename,
                    "generated": pdf_file is not None,
                    "error": pdf_error,
                },
            }
            waveassist.store_data("display_output", display_output, run_based=True, data_type="json")

except Exception as e:
    fallback_html = f"<p>Report generation failed: {_esc(str(e))}</p>"
    display_output = {
        "html_content": fallback_html,
        "status": "email_build_failed",
        "error": str(e),
    }
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    print(f"GitFlow: Email build failed: {e}. Email not sent.")

print("GitFlow: Email generation completed.")

