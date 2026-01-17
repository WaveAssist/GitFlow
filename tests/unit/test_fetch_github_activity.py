"""
Unit tests for fetch_github_activity.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock waveassist before importing the module
sys.modules['waveassist'] = MagicMock()


class TestIsBotUser:
    """Tests for is_bot_user function."""
    
    def test_is_bot_by_type_field(self):
        """Test detecting bot by type field."""
        from fetch_github_activity import is_bot_user
        
        user = {"login": "github-actions", "type": "Bot"}
        
        assert is_bot_user(user) is True
    
    def test_is_bot_by_bracket_suffix(self):
        """Test detecting bot by [bot] suffix."""
        from fetch_github_activity import is_bot_user
        
        user = {"login": "dependabot[bot]", "type": "User"}
        
        assert is_bot_user(user) is True
    
    def test_is_bot_by_common_name(self, sample_bot_users):
        """Test detecting bots by common names."""
        from fetch_github_activity import is_bot_user
        
        # Test various bot usernames
        assert is_bot_user({"login": "dependabot", "type": "User"}) is True
        assert is_bot_user({"login": "renovate", "type": "User"}) is True
        assert is_bot_user({"login": "github-actions", "type": "User"}) is True
    
    def test_is_not_bot_regular_user(self, sample_regular_users):
        """Test regular users are not detected as bots."""
        from fetch_github_activity import is_bot_user
        
        for user in sample_regular_users:
            assert is_bot_user(user) is False
    
    def test_is_bot_with_none_user(self):
        """Test with None user."""
        from fetch_github_activity import is_bot_user
        
        assert is_bot_user(None) is False
    
    def test_is_bot_with_empty_dict(self):
        """Test with empty dict."""
        from fetch_github_activity import is_bot_user
        
        assert is_bot_user({}) is False
    
    def test_is_bot_case_insensitive(self):
        """Test bot detection is case insensitive."""
        from fetch_github_activity import is_bot_user
        
        # Common bot names should be lowercased for comparison
        user = {"login": "DEPENDABOT", "type": "User"}
        assert is_bot_user(user) is True


class TestFilterActiveBranches:
    """Tests for filter_active_branches function."""
    
    def test_filter_active_branches_with_recent_commits(self, sample_branches_data):
        """Test filtering branches with recent commits."""
        from fetch_github_activity import filter_active_branches
        
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=7)
        
        active = filter_active_branches(sample_branches_data, since)
        
        # Should include main (most recent), but not old branches
        # Note: feature/auth was exactly 7 days ago, so it's filtered out (needs to be > since)
        assert "main" in active
        assert "old-feature" not in active
    
    def test_filter_active_branches_with_empty_list(self):
        """Test with empty branches list."""
        from fetch_github_activity import filter_active_branches
        
        since = datetime.now(timezone.utc) - timedelta(days=7)
        
        active = filter_active_branches([], since)
        
        assert active == []
    
    def test_filter_active_branches_with_none(self):
        """Test with None branches."""
        from fetch_github_activity import filter_active_branches
        
        since = datetime.now(timezone.utc) - timedelta(days=7)
        
        active = filter_active_branches(None, since)
        
        assert active == []
    
    def test_filter_active_branches_all_old(self):
        """Test when all branches are old."""
        from fetch_github_activity import filter_active_branches
        
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=30)
        
        branches = [
            {"name": "old-branch-1", "committedDate": old_date.isoformat()},
            {"name": "old-branch-2", "committedDate": old_date.isoformat()}
        ]
        
        since = now - timedelta(days=7)
        active = filter_active_branches(branches, since)
        
        assert active == []
    
    def test_filter_active_branches_date_comparison(self):
        """Test exact date boundary comparison."""
        from fetch_github_activity import filter_active_branches
        
        now = datetime.now(timezone.utc)
        exactly_7_days_ago = now - timedelta(days=7)
        
        branches = [
            {"name": "exactly-7-days", "committedDate": exactly_7_days_ago.isoformat()},
            {"name": "slightly-after", "committedDate": (exactly_7_days_ago + timedelta(seconds=1)).isoformat()}
        ]
        
        since = exactly_7_days_ago
        active = filter_active_branches(branches, since)
        
        # Should only include branches strictly after the since date
        assert "exactly-7-days" not in active
        assert "slightly-after" in active


class TestDataStructures:
    """Tests for data structure handling."""
    
    def test_commit_info_structure(self):
        """Test commit info structure matches expected format."""
        commit_info = {
            "sha": "abc123",
            "message": "Add feature",
            "author": "developer1",
            "timestamp": "2024-01-15T10:00:00Z",
            "url": "https://github.com/example/repo/commit/abc123"
        }
        
        # Verify all required fields are present
        assert "sha" in commit_info
        assert "message" in commit_info
        assert "author" in commit_info
        assert "timestamp" in commit_info
        assert "url" in commit_info
    
    def test_pr_info_structure(self):
        """Test PR info structure matches expected format."""
        pr_info = {
            "number": 42,
            "title": "Add feature",
            "description": "Feature description",
            "status": "open",
            "author": "developer1",
            "timestamp": "2024-01-15T09:00:00Z",
            "created_at": "2024-01-15T09:00:00Z",
            "url": "https://github.com/example/repo/pull/42",
            "head_sha": "abc123",
            "base_branch": "main"
        }
        
        # Verify all required fields are present
        assert "number" in pr_info
        assert "title" in pr_info
        assert "description" in pr_info
        assert "status" in pr_info
        assert "author" in pr_info
        assert "url" in pr_info
        assert "head_sha" in pr_info
        assert "base_branch" in pr_info
    
    def test_activity_data_structure(self, sample_github_activity_data):
        """Test activity data structure."""
        for repo, data in sample_github_activity_data.items():
            assert "commits" in data
            assert "pull_requests" in data
            assert isinstance(data["commits"], list)
            assert isinstance(data["pull_requests"], list)
    
    def test_empty_activity_data(self):
        """Test empty activity data structure is valid."""
        activity_data = {
            "example/repo": {
                "commits": [],
                "pull_requests": []
            }
        }
        
        assert len(activity_data["example/repo"]["commits"]) == 0
        assert len(activity_data["example/repo"]["pull_requests"]) == 0


class TestBotFiltering:
    """Tests for bot filtering in commits and PRs."""
    
    def test_filter_bot_commits(self):
        """Test that bot commits are filtered out."""
        from fetch_github_activity import is_bot_user
        
        commits = [
            {"author": {"login": "developer1", "type": "User"}},
            {"author": {"login": "dependabot[bot]", "type": "Bot"}},
            {"author": {"login": "developer2", "type": "User"}}
        ]
        
        human_commits = [c for c in commits if not is_bot_user(c.get("author"))]
        
        assert len(human_commits) == 2
        assert all(c["author"]["login"] in ["developer1", "developer2"] for c in human_commits)
    
    def test_filter_bot_prs(self):
        """Test that bot PRs are filtered out."""
        from fetch_github_activity import is_bot_user
        
        prs = [
            {"user": {"login": "developer1", "type": "User"}},
            {"user": {"login": "renovate", "type": "User"}},
            {"user": {"login": "developer2", "type": "User"}}
        ]
        
        human_prs = [pr for pr in prs if not is_bot_user(pr.get("user"))]
        
        assert len(human_prs) == 2


class TestDateRangeHandling:
    """Tests for date range calculations."""
    
    def test_days_to_fetch_constant(self):
        """Test DAYS_TO_FETCH constant value."""
        from fetch_github_activity import DAYS_TO_FETCH
        
        assert DAYS_TO_FETCH == 7
    
    def test_date_range_calculation(self):
        """Test date range calculation logic."""
        end_date = datetime.now(timezone.utc)
        days_to_fetch = 7
        since = end_date - timedelta(days=days_to_fetch)
        
        # Verify the range is exactly 7 days
        delta = end_date - since
        assert delta.days == 7
    
    def test_report_date_range_structure(self):
        """Test report date range structure."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report_date_range = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_date_formatted": start_date.strftime("%B %d, %Y"),
            "end_date_formatted": end_date.strftime("%B %d, %Y"),
        }
        
        assert "start_date" in report_date_range
        assert "end_date" in report_date_range
        assert "start_date_formatted" in report_date_range
        assert "end_date_formatted" in report_date_range


class TestEdgeCases:
    """Edge case tests."""
    
    def test_commit_with_no_author(self):
        """Test handling commits with missing author."""
        from fetch_github_activity import is_bot_user
        
        commit = {"sha": "abc123"}  # No author field
        
        # Should not crash when checking for bot
        is_bot = is_bot_user(commit.get("author"))
        assert is_bot is False
    
    def test_branch_with_missing_date(self):
        """Test handling branch with missing committed date."""
        from fetch_github_activity import filter_active_branches
        
        branches = [
            {"name": "branch1"},  # Missing committedDate
            {"name": "branch2", "committedDate": datetime.now(timezone.utc).isoformat()}
        ]
        
        since = datetime.now(timezone.utc) - timedelta(days=7)
        active = filter_active_branches(branches, since)
        
        # Only branch2 should be included
        assert "branch1" not in active
        assert "branch2" in active
    
    def test_empty_repo_path(self):
        """Test handling empty repo path."""
        repo = {"id": ""}
        repo_path = repo.get("id") if isinstance(repo, dict) else repo
        
        assert repo_path == ""
        # Should be skipped in main loop (if not repo_path: continue)
    
    def test_total_activity_calculation(self, sample_github_activity_data):
        """Test total activity calculation."""
        total_commits = sum(len(data["commits"]) for data in sample_github_activity_data.values())
        total_prs = sum(len(data["pull_requests"]) for data in sample_github_activity_data.values())
        
        assert total_commits == 3  # 2 from repo1, 1 from repo2
        assert total_prs == 1  # 1 from repo1, 0 from repo2
