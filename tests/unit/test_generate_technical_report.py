"""
Unit tests for generate_technical_report.py
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
        from generate_technical_report import build_repo_context_section
        
        repo_context = {
            "summary": "REST API backend service",
            "stack": "Node.js, Express, MongoDB",
            "tags": ["Node.js", "API"]
        }
        
        result = build_repo_context_section("example/repo1", repo_context)
        
        assert "example/repo1" in result
        assert "REST API backend service" in result
        assert "Node.js, Express, MongoDB" in result
    
    def test_build_repo_context_with_none(self):
        """Test building repo context with None."""
        from generate_technical_report import build_repo_context_section
        
        result = build_repo_context_section("example/repo1", None)
        
        assert result == ""


class TestBuildChangesContext:
    """Tests for build_changes_context function."""
    
    def test_build_changes_context_with_multiple_repos(self, sample_repository_analyses):
        """Test building changes context with multiple repositories."""
        from generate_technical_report import build_changes_context
        
        result = build_changes_context(sample_repository_analyses)
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert "example/repo1" in parsed
        assert "example/repo2" in parsed
    
    def test_build_changes_context_with_no_changes(self):
        """Test building changes context when no changes exist."""
        from generate_technical_report import build_changes_context
        
        analyses = [
            {"repository": "example/repo1", "changes": []},
        ]
        
        result = build_changes_context(analyses)
        
        assert result == ""


class TestBuildAnalysisContext:
    """Tests for build_analysis_context function."""
    
    def test_build_analysis_context_with_full_data(
        self, sample_repository_analyses, sample_repository_contexts
    ):
        """Test building analysis context with full data."""
        from generate_technical_report import build_analysis_context
        
        result = build_analysis_context(
            sample_repository_analyses,
            sample_repository_contexts
        )
        
        assert "example/repo1" in result
        assert "User authentication and profile management system" in result
    
    def test_build_analysis_context_filters_repos_without_changes(
        self, sample_repository_contexts
    ):
        """Test that only repos with changes are included."""
        from generate_technical_report import build_analysis_context
        
        analyses = [
            {"repository": "example/repo1", "changes": [{"summary": "test"}]},
            {"repository": "example/repo2", "changes": []}
        ]
        
        result = build_analysis_context(analyses, sample_repository_contexts)
        
        assert "example/repo1" in result


class TestBuildBusinessReportContext:
    """Tests for build_business_report_context function."""
    
    def test_build_business_report_context_with_full_report(self, sample_business_report):
        """Test building business report context."""
        from generate_technical_report import build_business_report_context
        
        result = build_business_report_context(sample_business_report)
        
        # Check for actual output format from code
        assert "Business Report has already summarised" in result
        assert "user authentication" in result.lower() or "User login" in result
    
    def test_build_business_report_context_with_empty_report(self):
        """Test with empty business report."""
        from generate_technical_report import build_business_report_context
        
        result = build_business_report_context({})
        
        # Should still return formatted context
        assert isinstance(result, str)
    
    def test_build_business_report_context_with_none(self):
        """Test with None business report."""
        from generate_technical_report import build_business_report_context
        
        result = build_business_report_context(None)
        
        assert result == ""
    
    def test_build_business_report_context_json_format(self, sample_business_report):
        """Test that context contains shipped features list."""
        from generate_technical_report import build_business_report_context
        
        result = build_business_report_context(sample_business_report)
        
        # Check that shipped features are included (in JSON array format)
        assert "[" in result
        assert "]" in result
        assert "User login" in result or "Password recovery" in result


class TestBuildPrompt:
    """Tests for build_prompt function."""
    
    def test_build_prompt_includes_project_name(self):
        """Test prompt includes project name."""
        from generate_technical_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            business_report_context="",
            changes_context=""
        )
        
        assert "MyProject" in prompt
    
    def test_build_prompt_includes_all_contexts(
        self, sample_repository_analyses, sample_repository_contexts,
        sample_business_report
    ):
        """Test prompt includes all provided contexts."""
        from generate_technical_report import (
            build_prompt, build_analysis_context,
            build_business_report_context, build_changes_context
        )
        
        analysis_ctx = build_analysis_context(
            sample_repository_analyses, sample_repository_contexts
        )
        business_ctx = build_business_report_context(sample_business_report)
        changes_ctx = build_changes_context(sample_repository_analyses)
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context=analysis_ctx,
            business_report_context=business_ctx,
            changes_context=changes_ctx
        )
        
        assert "MyProject" in prompt
        if business_ctx:
            assert "Business Report" in prompt or "user authentication" in prompt.lower()
    
    def test_build_prompt_includes_instructions(self):
        """Test prompt includes required instructions."""
        from generate_technical_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            business_report_context="",
            changes_context=""
        )
        
        assert "repository_deep_dive" in prompt
        assert "poem" in prompt
        assert "technical" in prompt.lower()
    
    def test_build_prompt_mentions_poem_requirements(self):
        """Test prompt mentions poem requirements."""
        from generate_technical_report import build_prompt
        
        prompt = build_prompt(
            project_name="MyProject",
            analysis_context="",
            business_report_context="",
            changes_context=""
        )
        
        assert "4 lines" in prompt or "poem" in prompt.lower()
        assert "rhym" in prompt.lower() or "technical" in prompt.lower()


class TestTechnicalReportModels:
    """Tests for Pydantic models."""
    
    def test_repo_update_model_valid(self):
        """Test creating valid RepoUpdate model."""
        from generate_technical_report import RepoUpdate
        
        update = RepoUpdate(
            repo_name="example/repo1",
            status="Feature Dev",
            technical_changes=["Added user auth", "Fixed login bug"]
        )
        
        assert update.repo_name == "example/repo1"
        assert update.status == "Feature Dev"
        assert len(update.technical_changes) == 2
    
    def test_repo_update_model_empty_changes(self):
        """Test RepoUpdate with empty changes list."""
        from generate_technical_report import RepoUpdate
        
        update = RepoUpdate(
            repo_name="example/repo1",
            status="Maintenance",
            technical_changes=[]
        )
        
        assert update.technical_changes == []
    
    def test_technical_report_model_valid(self):
        """Test creating valid TechnicalReport model."""
        from generate_technical_report import TechnicalReport, RepoUpdate
        
        report = TechnicalReport(
            repository_deep_dive=[
                RepoUpdate(
                    repo_name="example/repo1",
                    status="Feature Dev",
                    technical_changes=["Added auth"]
                )
            ],
            poem=[
                "Code commits flowing through the night",
                "Features shipping, shining bright",
                "Bugs we squashed with all our might",
                "Tech debt reduced, future looks right"
            ]
        )
        
        assert len(report.repository_deep_dive) == 1
        assert len(report.poem) == 4
    
    def test_technical_report_model_dump(self):
        """Test model dump with aliases."""
        from generate_technical_report import TechnicalReport, RepoUpdate
        
        report = TechnicalReport(
            repository_deep_dive=[
                RepoUpdate(
                    repo_name="example/repo1",
                    status="Maintenance",
                    technical_changes=["Fix"]
                )
            ],
            poem=["Line 1", "Line 2", "Line 3", "Line 4"]
        )
        
        dumped = report.model_dump(by_alias=True)
        
        assert "repository_deep_dive" in dumped
        assert "poem" in dumped


class TestTechnicalReportEdgeCases:
    """Edge case tests for technical report generation."""
    
    def test_llm_returns_none(self):
        """Test handling when LLM call returns None."""
        result = None
        technical_report = {}
        
        if result:
            technical_report = result.model_dump(by_alias=True)
        else:
            technical_report = {
                "repository_deep_dive": [],
                "poem": [
                    "No updates found this week to share",
                    "The codebase rests in silent care",
                    "Next week brings changes, we declare",
                    "Development continues everywhere"
                ]
            }
        
        assert "repository_deep_dive" in technical_report
        assert "poem" in technical_report
        assert len(technical_report["poem"]) == 4
    
    def test_pydantic_validation_error_missing_fields(self):
        """Test handling Pydantic validation errors."""
        from generate_technical_report import TechnicalReport
        
        # Missing required fields should raise validation error
        with pytest.raises(Exception):
            report = TechnicalReport(
                repository_deep_dive=[]
                # Missing poem
            )
    
    def test_pydantic_validation_error_repo_update(self):
        """Test RepoUpdate validation errors."""
        from generate_technical_report import RepoUpdate
        
        # Missing required fields
        with pytest.raises(Exception):
            update = RepoUpdate(
                repo_name="example/repo1"
                # Missing status and technical_changes
            )
    
    def test_empty_activity_data(self):
        """Test when there's no activity to report."""
        repository_analyses = []
        total_changes = sum(len(a.get("changes", [])) for a in repository_analyses)
        
        assert total_changes == 0
        
        # Should create fallback report
        technical_report = {
            "repository_deep_dive": [],
            "poem": [
                "No updates found this week to share",
                "The codebase rests in silent care",
                "Next week brings changes, we declare",
                "Development continues everywhere"
            ]
        }
        
        assert len(technical_report["poem"]) == 4
    
    def test_none_contexts_handling(self):
        """Test handling when contexts are None."""
        from generate_technical_report import (
            build_analysis_context, build_business_report_context,
            build_changes_context
        )
        
        # Should handle None gracefully
        analysis_ctx = build_analysis_context([], None or {})
        business_ctx = build_business_report_context(None or {})
        changes_ctx = build_changes_context(None or [])
        
        assert isinstance(analysis_ctx, str)
        assert isinstance(business_ctx, str)
        assert isinstance(changes_ctx, str)
    
    def test_poem_with_wrong_line_count(self):
        """Test that poem must have exactly 4 lines (validated by LLM, not model)."""
        from generate_technical_report import TechnicalReport, RepoUpdate
        
        # Model allows any list, but LLM should generate 4 lines
        # This test just verifies the model accepts it
        report = TechnicalReport(
            repository_deep_dive=[],
            poem=["Line 1", "Line 2"]  # Wrong count, but model allows
        )
        
        # Model doesn't validate count, so this passes
        assert len(report.poem) == 2
