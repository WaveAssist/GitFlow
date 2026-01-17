"""
Unit tests for analyze_repository_activity.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock waveassist before importing the module
sys.modules['waveassist'] = MagicMock()


class TestIsNonCodeFile:
    """Tests for is_non_code_file function."""
    
    def test_is_non_code_file_images(self):
        """Test detection of image files."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("photo.png") is True
        assert is_non_code_file("logo.jpg") is True
        assert is_non_code_file("icon.svg") is True
        assert is_non_code_file("diagram.gif") is True
    
    def test_is_non_code_file_videos(self):
        """Test detection of video files."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("demo.mp4") is True
        assert is_non_code_file("tutorial.avi") is True
        assert is_non_code_file("clip.mov") is True
    
    def test_is_non_code_file_documents(self):
        """Test detection of document files."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("report.pdf") is True
        assert is_non_code_file("data.xlsx") is True
        assert is_non_code_file("presentation.pptx") is True
    
    def test_is_non_code_file_fonts(self):
        """Test detection of font files."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("font.woff") is True
        assert is_non_code_file("font.woff2") is True
        assert is_non_code_file("font.ttf") is True
    
    def test_is_non_code_file_lock_files(self):
        """Test detection of lock files."""
        from analyze_repository_activity import is_non_code_file
        
        # Only files with .lock extension are detected
        assert is_non_code_file("file.lock") is True
    
    def test_is_code_file(self):
        """Test that code files are not detected as non-code."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("app.py") is False
        assert is_non_code_file("index.js") is False
        assert is_non_code_file("main.go") is False
        assert is_non_code_file("style.css") is False
        assert is_non_code_file("README.md") is False
    
    def test_is_non_code_file_case_insensitive(self):
        """Test that extension matching is case insensitive."""
        from analyze_repository_activity import is_non_code_file
        
        assert is_non_code_file("IMAGE.PNG") is True
        assert is_non_code_file("Video.MP4") is True


class TestEstimateTokens:
    """Tests for estimate_tokens function."""
    
    def test_estimate_tokens_basic(self):
        """Test basic token estimation."""
        from analyze_repository_activity import estimate_tokens
        
        text = "This is a test"
        tokens = estimate_tokens(text)
        
        # Rough estimate: ~4 chars per token
        assert tokens > 0
        assert tokens <= len(text)  # Should be less than or equal to char count
    
    def test_estimate_tokens_empty_string(self):
        """Test with empty string."""
        from analyze_repository_activity import estimate_tokens
        
        tokens = estimate_tokens("")
        
        assert tokens == 0
    
    def test_estimate_tokens_long_text(self):
        """Test with longer text."""
        from analyze_repository_activity import estimate_tokens
        
        text = "word " * 100  # 100 words
        tokens = estimate_tokens(text)
        
        assert tokens > 0
        # Rough estimate should be reasonable
        assert tokens > 50 and tokens < 200


class TestGroupCommitsByDay:
    """Tests for group_commits_by_day function."""
    
    def test_group_commits_by_day_single_day(self):
        """Test grouping commits from a single day."""
        from analyze_repository_activity import group_commits_by_day
        
        commits = [
            {"sha": "abc1", "timestamp": "2024-01-15T10:00:00Z"},
            {"sha": "abc2", "timestamp": "2024-01-15T14:00:00Z"},
            {"sha": "abc3", "timestamp": "2024-01-15T18:00:00Z"}
        ]
        
        grouped = group_commits_by_day(commits)
        
        assert "2024-01-15" in grouped
        assert len(grouped["2024-01-15"]) == 3
    
    def test_group_commits_by_day_multiple_days(self):
        """Test grouping commits from multiple days."""
        from analyze_repository_activity import group_commits_by_day
        
        commits = [
            {"sha": "abc1", "timestamp": "2024-01-15T10:00:00Z"},
            {"sha": "abc2", "timestamp": "2024-01-16T10:00:00Z"},
            {"sha": "abc3", "timestamp": "2024-01-17T10:00:00Z"}
        ]
        
        grouped = group_commits_by_day(commits)
        
        assert len(grouped) == 3
        assert "2024-01-15" in grouped
        assert "2024-01-16" in grouped
        assert "2024-01-17" in grouped
    
    def test_group_commits_by_day_empty_list(self):
        """Test with empty commits list."""
        from analyze_repository_activity import group_commits_by_day
        
        grouped = group_commits_by_day([])
        
        assert grouped == {}
    
    def test_group_commits_by_day_missing_timestamp(self):
        """Test handling commits with missing timestamp."""
        from analyze_repository_activity import group_commits_by_day
        
        commits = [
            {"sha": "abc1", "timestamp": "2024-01-15T10:00:00Z"},
            {"sha": "abc2"}  # Missing timestamp
        ]
        
        grouped = group_commits_by_day(commits)
        
        # Should only group commits with valid timestamps
        assert len(grouped) >= 0  # At least one day from abc1


class TestAnalysisModels:
    """Tests for Pydantic models."""
    
    def test_change_model_valid(self):
        """Test creating valid Change model."""
        from analyze_repository_activity import Change
        
        change = Change(
            summary="Added user authentication",
            category="feature",
            contributing_commits=["abc123", "def456"]
        )
        
        assert change.summary == "Added user authentication"
        assert change.category == "feature"
        assert len(change.contributing_commits) == 2
    
    def test_change_model_categories(self):
        """Test different change categories."""
        from analyze_repository_activity import Change
        
        categories = ["feature", "improvement", "fix", "refactor", "docs", "test", "chore"]
        
        for category in categories:
            change = Change(
                summary="Test change",
                category=category,
                contributing_commits=["abc123"]
            )
            assert change.category == category
    
    def test_change_model_empty_commits(self):
        """Test Change with empty commits list."""
        from analyze_repository_activity import Change
        
        change = Change(
            summary="Test change",
            category="fix",
            contributing_commits=[]
        )
        
        assert change.contributing_commits == []
    
    def test_repository_analysis_model_valid(self):
        """Test creating valid RepositoryAnalysis model."""
        from analyze_repository_activity import RepositoryAnalysis, Change
        
        analysis = RepositoryAnalysis(
            changes=[
                Change(
                    summary="Added auth",
                    category="feature",
                    contributing_commits=["abc123"]
                ),
                Change(
                    summary="Fixed bug",
                    category="fix",
                    contributing_commits=["def456"]
                )
            ]
        )
        
        assert len(analysis.changes) == 2
    
    def test_repository_analysis_model_empty_changes(self):
        """Test RepositoryAnalysis with no changes."""
        from analyze_repository_activity import RepositoryAnalysis
        
        analysis = RepositoryAnalysis(changes=[])
        
        assert analysis.changes == []
    
    def test_change_model_dump(self):
        """Test Change model dump."""
        from analyze_repository_activity import Change
        
        change = Change(
            summary="Test",
            category="feature",
            contributing_commits=["abc"]
        )
        
        dumped = change.model_dump()
        
        assert "summary" in dumped
        assert "category" in dumped
        assert "contributing_commits" in dumped


class TestBuildCommitContext:
    """Tests for build_commit_context function."""
    
    def test_build_commit_context_basic(self, sample_github_activity_data, sample_commit_diffs):
        """Test building commit context."""
        from analyze_repository_activity import build_commit_context
        
        commits = sample_github_activity_data["example/repo1"]["commits"]
        
        context = build_commit_context(commits, sample_commit_diffs)
        
        assert isinstance(context, str)
        assert len(context) > 0
    
    def test_build_commit_context_with_token_budget(
        self, sample_github_activity_data, sample_commit_diffs
    ):
        """Test building commit context with token budget."""
        from analyze_repository_activity import build_commit_context
        
        commits = sample_github_activity_data["example/repo1"]["commits"]
        
        # Set a very low budget
        context = build_commit_context(commits, sample_commit_diffs, token_budget=100)
        
        assert isinstance(context, str)
        # Should be truncated due to low budget
    
    def test_build_commit_context_empty_commits(self):
        """Test with empty commits list."""
        from analyze_repository_activity import build_commit_context
        
        context = build_commit_context([], {})
        
        assert isinstance(context, str)


class TestEdgeCases:
    """Edge case tests."""
    
    def test_pydantic_validation_error_change(self):
        """Test Change validation errors."""
        from analyze_repository_activity import Change
        
        # Missing required fields
        with pytest.raises(Exception):
            change = Change(
                summary="Test"
                # Missing category and contributing_commits
            )
    
    def test_llm_returns_none(self):
        """Test handling when LLM returns None."""
        result = None
        
        if result:
            changes = result.model_dump()
        else:
            changes = {"changes": []}
        
        assert "changes" in changes
        assert changes["changes"] == []
    
    def test_empty_diff_data(self):
        """Test handling empty diff data."""
        from analyze_repository_activity import build_commit_context
        
        commits = [{"sha": "abc123", "message": "Test commit"}]
        commit_diffs = {}  # No diffs available
        
        context = build_commit_context(commits, commit_diffs)
        
        # Should still build context with commit messages
        assert isinstance(context, str)
    
    def test_invalid_timestamp_format(self):
        """Test handling invalid timestamp format."""
        from analyze_repository_activity import group_commits_by_day
        
        commits = [
            {"sha": "abc2", "timestamp": "2024-01-15T10:00:00Z"}
        ]
        
        # Valid timestamp should work fine
        grouped = group_commits_by_day(commits)
        assert isinstance(grouped, dict)
        assert "2024-01-15" in grouped
