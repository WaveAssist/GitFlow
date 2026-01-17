import requests
import waveassist
from pydantic import BaseModel, Field
from typing import List, Optional
import base64

# Initialize WaveAssist SDK for downstream node
waveassist.init(check_credits=True)

print("GitFlow: Starting repository context fetch...")

# LLM settings
max_tokens = 1500
temperature = 0.3

# File patterns to look for
README_PATTERNS = ["README.md", "README.rst", "README.txt", "README", "readme.md"]
REQUIREMENTS_PATTERNS = [
    "requirements.txt", "package.json", "Pipfile", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Gemfile"
]
ENTRY_POINT_PATTERNS = [
    "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs",
    "src/main.py", "src/index.js", "src/index.ts", "src/main.go"
]


class RepositoryContext(BaseModel):
    """Model for repository context summary"""
    summary: str = Field(description="Brief description of repository purpose and structure")
    stack: str = Field(description="Summary of the stack of technologies used")
    tags: List[str] = Field(description="Up to 3 tags for the repository (language, framework, etc.)")


def get_file_content(repo_path: str, file_path: str, headers: dict) -> Optional[str]:
    """Fetch a single file's content from GitHub."""
    url = f"https://api.github.com/repos/{repo_path}/contents/{file_path}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None
    
    try:
        data = response.json()
        if data.get("encoding") == "base64" and data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return content[:10000]  # Limit content size
    except Exception as e:
        print(f"⚠️ Error decoding {file_path}: {e}")
    
    return None


def get_repo_tree(repo_path: str, headers: dict) -> List[str]:
    """Get list of all files in repository (top-level tree)."""
    url = f"https://api.github.com/repos/{repo_path}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    try:
        data = response.json()
        files = []
        for item in data.get("tree", [])[:500]:  # Limit to 500 items
            if item.get("type") == "blob":
                files.append(item.get("path", ""))
        return files
    except Exception:
        return []


def find_and_fetch_file(repo_path: str, patterns: List[str], headers: dict, file_list: List[str]) -> Optional[str]:
    """Find first matching file from patterns and fetch its content."""
    for pattern in patterns:
        # Check direct match
        if pattern in file_list:
            content = get_file_content(repo_path, pattern, headers)
            if content:
                return content
        # Check case-insensitive match
        for file in file_list:
            if file.lower() == pattern.lower():
                content = get_file_content(repo_path, file, headers)
                if content:
                    return content
    return None


def generate_context_summary(
    repo_path: str,
    readme_content: Optional[str],
    requirements_content: Optional[str],
    entry_point_content: Optional[str],
    file_list: List[str],
    model_name: str
) -> Optional[dict]:
    """Generate repository context summary using LLM."""
    
    # Build context for LLM
    context_parts = []
    
    if readme_content:
        context_parts.append(f"README:\n{readme_content[:5000]}")
    
    if requirements_content:
        context_parts.append(f"Dependencies/Requirements:\n{requirements_content[:5000]}")
    
    if entry_point_content:
        context_parts.append(f"Main Entry Point:\n{entry_point_content[:5000]}")
    
    # Add file structure overview
    if file_list:
        structure = "\n".join(file_list[:200])
        context_parts.append(f"File Structure (partial):\n{structure}")
    
    if not context_parts:
        return {
            "summary": "No context files available for this repository.",
            "stack": "Unknown",
            "tags": []
        }
    
    context = "\n\n---\n\n".join(context_parts)
    
    prompt = f"""Analyze this repository and provide a brief context summary.

Repository: {repo_path}

{context}

Provide:
1. summary: A 1-2 sentence description of what this repository does and its purpose
2. stack: A brief summary of the main technologies/stack used (languages, frameworks, databases, etc.)
3. tags: Up to 3 short tags that best describe this repo (e.g., "Python", "React", "API", "CLI")

Be concise and focus on the most important aspects."""

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=RepositoryContext,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    if result:
        return result.model_dump(by_alias=True)
    
    return None


# Main execution
github_selected_resources = waveassist.fetch_data("github_selected_resources") or []
github_access_token = waveassist.fetch_data("github_access_token") or ""
model_name = waveassist.fetch_data("model_name") or "anthropic/claude-haiku-4.5"

# Fetch existing repository contexts
repository_contexts = waveassist.fetch_data("repository_contexts") or {}

headers = {
    "Authorization": f"token {github_access_token}",
    "Accept": "application/vnd.github+json",
}

new_contexts_added = False

for repo in github_selected_resources:
    repo_path = repo.get("id") if isinstance(repo, dict) else repo
    
    if not repo_path:
        continue
    
    # Skip if context already exists
    if repo_path in repository_contexts:
        print(f"✓ Context already exists for {repo_path}, skipping...")
        continue
    
    print(f"📦 Fetching context for {repo_path}...")
    
    try:
        # Get file tree
        file_list = get_repo_tree(repo_path, headers)
        
        # Fetch key files
        readme_content = find_and_fetch_file(repo_path, README_PATTERNS, headers, file_list)
        requirements_content = find_and_fetch_file(repo_path, REQUIREMENTS_PATTERNS, headers, file_list)
        entry_point_content = find_and_fetch_file(repo_path, ENTRY_POINT_PATTERNS, headers, file_list)
        
        # Generate context summary
        context = generate_context_summary(
            repo_path,
            readme_content,
            requirements_content,
            entry_point_content,
            file_list,
            model_name
        )
        
        if context:
            repository_contexts[repo_path] = context
            new_contexts_added = True
            print(f"✅ Generated context for {repo_path}")
            print(f"   Summary: {context.get('summary', 'N/A')[:100]}...")
            print(f"   Tags: {context.get('tags', [])}")

            
    except Exception as e:
        print(f"❌ Error fetching context for {repo_path}: {e}")


# Store updated contexts
if new_contexts_added:
    waveassist.store_data("repository_contexts", repository_contexts)
    print(f"✅ Stored repository contexts for {len(repository_contexts)} repositories")
else:
    print("✓ All repository contexts already up to date")

print("GitFlow: Repository context fetch completed.")

