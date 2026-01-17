"""
Pytest configuration and shared fixtures for GitFlow tests.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from typing import Dict, Any, List


@pytest.fixture
def sample_repository_analyses() -> List[Dict[str, Any]]:
    """Sample repository analyses data for testing."""
    return [
        {
            "repository": "example/repo1",
            "changes": [
                {
                    "summary": "Added user authentication feature",
                    "category": "feature",
                    "contributing_commits": ["abc123", "def456"]
                },
                {
                    "summary": "Fixed login bug",
                    "category": "fix",
                    "contributing_commits": ["ghi789"]
                }
            ]
        },
        {
            "repository": "example/repo2",
            "changes": [
                {
                    "summary": "Refactored API endpoints",
                    "category": "refactor",
                    "contributing_commits": ["jkl012"]
                }
            ]
        }
    ]


@pytest.fixture
def sample_repository_contexts() -> Dict[str, Dict[str, Any]]:
    """Sample repository context data for testing."""
    return {
        "example/repo1": {
            "summary": "User authentication and profile management system",
            "stack": "Python, Flask, PostgreSQL",
            "tags": ["Python", "Flask", "API"]
        },
        "example/repo2": {
            "summary": "REST API backend service",
            "stack": "Node.js, Express, MongoDB",
            "tags": ["Node.js", "API", "MongoDB"]
        }
    }


@pytest.fixture
def sample_github_activity_data() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Sample GitHub activity data for testing."""
    return {
        "example/repo1": {
            "commits": [
                {
                    "sha": "abc123",
                    "message": "Add user authentication",
                    "author": "developer1",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "url": "https://github.com/example/repo1/commit/abc123"
                },
                {
                    "sha": "def456",
                    "message": "Add password hashing",
                    "author": "developer1",
                    "timestamp": "2024-01-15T11:00:00Z",
                    "url": "https://github.com/example/repo1/commit/def456"
                }
            ],
            "pull_requests": [
                {
                    "number": 42,
                    "title": "Feature: User Authentication",
                    "description": "Implements user login and registration",
                    "status": "open",
                    "author": "developer1",
                    "timestamp": "2024-01-15T09:00:00Z",
                    "created_at": "2024-01-15T09:00:00Z",
                    "url": "https://github.com/example/repo1/pull/42",
                    "head_sha": "abc123",
                    "base_branch": "main"
                }
            ]
        },
        "example/repo2": {
            "commits": [
                {
                    "sha": "jkl012",
                    "message": "Refactor API routes",
                    "author": "developer2",
                    "timestamp": "2024-01-16T14:00:00Z",
                    "url": "https://github.com/example/repo2/commit/jkl012"
                }
            ],
            "pull_requests": []
        }
    }


@pytest.fixture
def sample_business_report() -> Dict[str, Any]:
    """Sample business report for testing."""
    return {
        "executive_summary": "This week we shipped user authentication and improved API performance.",
        "shipped_features": [
            "User login and registration system",
            "Password recovery workflow"
        ]
    }


@pytest.fixture
def sample_business_report_history() -> List[Dict[str, Any]]:
    """Sample business report history for testing."""
    return [
        {
            "week": "2024-01-08",
            "report": {
                "executive_summary": "Previous week focused on database optimization.",
                "shipped_features": [
                    "Database query optimization"
                ]
            }
        }
    ]


@pytest.fixture
def sample_commit_diffs() -> Dict[str, List[Dict[str, Any]]]:
    """Sample commit diffs for testing."""
    return {
        "abc123": [
            {
                "filename": "auth/login.py",
                "status": "added",
                "additions": 50,
                "deletions": 0,
                "patch": "@@ -0,0 +1,50 @@\n+def login(username, password):\n+    # Login logic\n+    pass"
            }
        ],
        "def456": [
            {
                "filename": "auth/password.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "patch": "@@ -10,5 +10,10 @@\n-    return password\n+    return hash_password(password)"
            }
        ]
    }


@pytest.fixture
def sample_branches_data() -> List[Dict[str, str]]:
    """Sample branches data with commit dates."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    return [
        {
            "name": "main",
            "committedDate": now.isoformat()
        },
        {
            "name": "feature/auth",
            "committedDate": week_ago.isoformat()
        },
        {
            "name": "old-feature",
            "committedDate": two_weeks_ago.isoformat()
        }
    ]


@pytest.fixture
def mock_waveassist():
    """Mock waveassist module."""
    mock = MagicMock()
    mock.fetch_data.return_value = None
    mock.store_data.return_value = None
    mock.init.return_value = None
    mock.check_credits_and_notify.return_value = True
    mock.call_llm.return_value = None
    return mock


@pytest.fixture
def sample_bot_users() -> List[Dict[str, Any]]:
    """Sample bot users for testing."""
    return [
        {"login": "dependabot[bot]", "type": "Bot"},
        {"login": "dependabot", "type": "User"},
        {"login": "github-actions[bot]", "type": "Bot"},
        {"login": "renovate", "type": "User"},
    ]


@pytest.fixture
def sample_regular_users() -> List[Dict[str, Any]]:
    """Sample regular users for testing."""
    return [
        {"login": "developer1", "type": "User"},
        {"login": "developer2", "type": "User"},
    ]
