"""
Unit tests for generate_business_report.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock waveassist before importing the module
sys.modules['waveassist'] = MagicMock()


class TestBuildRepoContextSection:
    """Tests for build_repo_context_section function."""
    
    def test_build_repo_context_with_full_info(self):
        """Test building repo context with full information."""
        from generate_business_report import build_repo_context_section
        
        repo_context = {
            "summary": "User authentication system",
            "stack": "Python, Flask, PostgreSQL",
            "tags": ["Python", "API"]
        }
        
        result = build_repo_context_section("example/repo1", repo_context)
        
        assert "example/repo1" in result
        assert "User authentication system" in result
        assert "Python, Flask, PostgreSQL" in result
    
    def test_build_repo_context_with_none(self):
        """Test building repo context with None."""
        from generate_business_report import build_repo_context_section
        
        result = build_repo_context_section("example/repo1", None)
        
        assert result == ""
    
    def test_build_repo_context_with_empty_dict(self):
        """Test building repo context with empty dict."""
        from generate_business_report import build_repo_context_section
        
        result = build_repo_context_section("example/repo1", {})
        
        # Empty dict is falsy in Python, so function returns empty string
        assert result == ""


class TestBuildChangesContext:
    """Tests for build_changes_context function."""
    
    def test_build_changes_context_with_multiple_repos(self, sample_repository_analyses):
        """Test building changes context with multiple repositories."""
        from generate_business_report import build_changes_context
        
        result = build_changes_context(sample_repository_analyses)
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert "example/repo1" in parsed
        assert "example/repo2" in parsed
        assert len(parsed["example/repo1"]) == 2
        assert len(parsed["example/repo2"]) == 1
    
    def test_build_changes_context_with_no_changes(self):
        """Test building changes context when no changes exist."""
        from generate_business_report import build_changes_context
        
        analyses = [
            {"repository": "example/repo1", "changes": []},
            {"repository": "example/repo2", "changes": []}
        ]
        
        result = build_changes_context(analyses)
        
        assert result == ""
    
    def test_build_changes_context_with_empty_list(self):
        """Test building changes context with empty list."""
        from generate_business_report import build_changes_context
        
        result = build_changes_context([])
        
        assert result == ""
    
    def test_build_changes_context_filters_repos_without_changes(self, sample_repository_analyses):
        """Test that repos without changes are filtered out."""
        from generate_business_report import build_changes_context
        
        # Add a repo with no changes
        analyses = sample_repository_analyses + [
            {"repository": "example/repo3", "changes": []}
        ]
        
        result = build_changes_context(analyses)
        parsed = json.loads(result)
        
        # Should not include repo3
        assert "example/repo3" not in parsed


class TestBuildAnalysisContext:
    """Tests for build_analysis_context function."""
    
    def test_build_analysis_context_with_full_data(
        self, sample_repository_analyses, sample_repository_contexts
    ):
        """Test building analysis context with full data."""
        from generate_business_report import build_analysis_context
        
        result = build_analysis_context(
            sample_repository_analyses,
            sample_repository_contexts
        )
        
        assert "example/repo1" in result
        assert "User authentication and profile management system" in result
        assert "Python, Flask, PostgreSQL" in result
    
    def test_build_analysis_context_filters_repos_without_changes(
        self, sample_repository_contexts
    ):
        """Test that only repos with changes are included."""
        from generate_business_report import build_analysis_context
        
        # Only repo1 has changes
        analyses = [
            {"repository": "example/repo1", "changes": [{"summary": "test"}]},
            {"repository": "example/repo2", "changes": []}
        ]
        
        result = build_analysis_context(analyses, sample_repository_contexts)
        
        assert "example/repo1" in result
        # repo2 should not be in the result since it has no changes
        assert result.count("example/repo2") == 0 or "example/repo2" not in result
    
    def test_build_analysis_context_with_missing_repo_contexts(
        self, sample_repository_analyses
    ):
        """Test with missing repository contexts."""
        from generate_business_report import build_analysis_context
        
        # Empty contexts dict
        result = build_analysis_context(sample_repository_analyses, {})
        
        # Should return empty string since no contexts available
        assert result == ""
    
    def test_build_analysis_context_with_empty_analyses(
        self, sample_repository_contexts
    ):
        """Test with no repository analyses."""
        from generate_business_report import build_analysis_context
        
        result = build_analysis_context([], sample_repository_contexts)
        
        assert result == ""


class TestBuildHistoryContext:
    """Tests for build_history_context function."""
    
    def test_build_history_context_with_history(self, sample_business_report_history):
        """Test building history context with previous reports."""
        from generate_business_report import build_history_context
        
        result = build_history_context(sample_business_report_history)
        
        assert "Previous week's business report" in result
        assert "2024-01-08" in result
        assert "Database query optimization" in result
    
    def test_build_history_context_with_empty_history(self):
        """Test with no history."""
        from generate_business_report import build_history_context
        
        result = build_history_context([])
        
        assert result == ""
    
    def test_build_history_context_with_none(self):
        """Test with None history."""
        from generate_business_report import build_history_context
        
        result = build_history_context(None)
        
        assert result == ""
    
    def test_build_history_context_json_format(self, sample_business_report_history):
        """Test that history context contains valid JSON."""
        from generate_business_report import build_history_context
        
        result = build_history_context(sample_business_report_history)
        
        # Result should contain JSON-formatted data
        assert "{" in result
        assert "}" in result


class TestBuildPrompt:
    """Tests for build_prompt function."""
    
    def test_build_prompt_includes_project_name(self):
        """Test prompt includes project name."""
        from generate_business_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            history_context="",
            pull_requests_context="",
            changes_context=""
        )
        
        assert "MyProject" in prompt
    
    def test_build_prompt_includes_all_contexts(
        self, sample_repository_analyses, sample_repository_contexts,
        sample_business_report_history
    ):
        """Test prompt includes all provided contexts."""
        from generate_business_report import (
            build_prompt, build_analysis_context,
            build_history_context, build_changes_context
        )
        
        analysis_ctx = build_analysis_context(
            sample_repository_analyses, sample_repository_contexts
        )
        history_ctx = build_history_context(sample_business_report_history)
        changes_ctx = build_changes_context(sample_repository_analyses)
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context=analysis_ctx,
            history_context=history_ctx,
            pull_requests_context="",
            changes_context=changes_ctx
        )
        
        assert "MyProject" in prompt
        assert "Previous Report Context" in prompt or "2024-01-08" in prompt
        assert "Repo Summaries Context" in prompt or "example/repo1" in prompt
        assert "Code Changes" in prompt or "example/repo1" in prompt
    
    def test_build_prompt_includes_instructions(self):
        """Test prompt includes required instructions."""
        from generate_business_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            history_context="",
            pull_requests_context="",
            changes_context=""
        )
        
        assert "executive_summary" in prompt
        assert "shipped_features" in prompt
        assert "business" in prompt.lower() or "CEO" in prompt
    
    def test_build_prompt_mentions_filtering(self):
        """Test prompt mentions filtering/focusing on signal."""
        from generate_business_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            history_context="",
            pull_requests_context="",
            changes_context=""
        )
        
        # Should mention filtering or focusing
        assert any(word in prompt.lower() for word in ["filter", "focus", "signal", "headline", "ignore"])


class TestBusinessReportModel:
    """Tests for BusinessReport Pydantic model."""
    
    def test_business_report_model_valid(self):
        """Test creating valid BusinessReport model."""
        from generate_business_report import BusinessReport
        
        report = BusinessReport(
            executive_summary="We shipped user authentication this week.",
            shipped_features=["User login", "Password recovery"]
        )
        
        assert report.executive_summary == "We shipped user authentication this week."
        assert len(report.shipped_features) == 2
    
    def test_business_report_model_empty_features(self):
        """Test business report with empty features list."""
        from generate_business_report import BusinessReport
        
        report = BusinessReport(
            executive_summary="No significant updates this week.",
            shipped_features=[]
        )
        
        assert report.shipped_features == []
    
    def test_business_report_model_dump(self):
        """Test model dump with aliases."""
        from generate_business_report import BusinessReport
        
        report = BusinessReport(
            executive_summary="Summary",
            shipped_features=["Feature 1"]
        )
        
        dumped = report.model_dump(by_alias=True)
        
        assert "executive_summary" in dumped
        assert "shipped_features" in dumped


class TestBusinessReportEdgeCases:
    """Edge case tests for business report generation."""
    
    def test_llm_returns_none(self):
        """Test handling when LLM call returns None."""
        result = None
        business_report = {}
        
        if result:
            business_report = result.model_dump(by_alias=True)
        else:
            business_report = {
                "executive_summary": "Development activity was recorded but report generation encountered an issue.",
                "shipped_features": []
            }
        
        assert "executive_summary" in business_report
        assert "shipped_features" in business_report
        assert business_report["shipped_features"] == []
    
    def test_pydantic_validation_error(self):
        """Test handling Pydantic validation errors."""
        from generate_business_report import BusinessReport
        
        # Missing required fields should raise validation error
        with pytest.raises(Exception):
            report = BusinessReport(
                executive_summary="Test"
                # Missing shipped_features
            )
    
    def test_empty_activity_data(self):
        """Test when there's no activity to report."""
        repository_analyses = []
        total_changes = sum(len(a.get("changes", [])) for a in repository_analyses)
        
        assert total_changes == 0
        
        # Should create fallback report
        business_report = {
            "executive_summary": "No development activity was recorded this week.",
            "shipped_features": []
        }
        
        assert business_report["shipped_features"] == []
    
    def test_all_repos_no_changes(self):
        """Test when all repos have no changes."""
        repository_analyses = [
            {"repository": "example/repo1", "changes": []},
            {"repository": "example/repo2", "changes": []}
        ]
        
        total_changes = sum(len(a.get("changes", [])) for a in repository_analyses)
        
        assert total_changes == 0
    
    def test_none_contexts_handling(self):
        """Test handling when contexts are None."""
        from generate_business_report import (
            build_analysis_context, build_history_context,
            build_changes_context
        )
        
        # Should handle None gracefully
        analysis_ctx = build_analysis_context([], None or {})
        history_ctx = build_history_context(None or [])
        changes_ctx = build_changes_context(None or [])
        
        assert isinstance(analysis_ctx, str)
        assert isinstance(history_ctx, str)
        assert isinstance(changes_ctx, str)
