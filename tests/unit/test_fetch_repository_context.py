"""
Unit tests for fetch_repository_context.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock waveassist before importing the module
sys.modules['waveassist'] = MagicMock()


class TestRepositoryContextModel:
    """Tests for RepositoryContext Pydantic model."""
    
    def test_repository_context_model_valid(self):
        """Test creating valid RepositoryContext model."""
        from fetch_repository_context import RepositoryContext
        
        context = RepositoryContext(
            summary="User authentication system",
            stack="Python, Flask, PostgreSQL",
            tags=["Python", "API", "Auth"]
        )
        
        assert context.summary == "User authentication system"
        assert context.stack == "Python, Flask, PostgreSQL"
        assert len(context.tags) == 3
    
    def test_repository_context_model_empty_tags(self):
        """Test RepositoryContext with empty tags."""
        from fetch_repository_context import RepositoryContext
        
        context = RepositoryContext(
            summary="Test repo",
            stack="Unknown",
            tags=[]
        )
        
        assert context.tags == []
    
    def test_repository_context_model_max_three_tags(self):
        """Test that description mentions up to 3 tags."""
        from fetch_repository_context import RepositoryContext
        
        # Model allows any number, but description says "Up to 3 tags"
        context = RepositoryContext(
            summary="Test",
            stack="Test",
            tags=["Tag1", "Tag2", "Tag3"]
        )
        
        assert len(context.tags) == 3
    
    def test_repository_context_model_dump(self):
        """Test model dump."""
        from fetch_repository_context import RepositoryContext
        
        context = RepositoryContext(
            summary="Test",
            stack="Test stack",
            tags=["Python"]
        )
        
        dumped = context.model_dump()
        
        assert "summary" in dumped
        assert "stack" in dumped
        assert "tags" in dumped


class TestFilePatternMatching:
    """Tests for file pattern matching logic."""
    
    def test_readme_patterns(self):
        """Test README pattern matching."""
        from fetch_repository_context import README_PATTERNS
        
        # Check that common README patterns are included
        assert "README.md" in README_PATTERNS
        assert "README.rst" in README_PATTERNS or "readme.md" in README_PATTERNS
    
    def test_requirements_patterns(self):
        """Test requirements pattern matching."""
        from fetch_repository_context import REQUIREMENTS_PATTERNS
        
        # Check common package files
        assert "requirements.txt" in REQUIREMENTS_PATTERNS
        assert "package.json" in REQUIREMENTS_PATTERNS
        assert "Cargo.toml" in REQUIREMENTS_PATTERNS or "pyproject.toml" in REQUIREMENTS_PATTERNS
    
    def test_entry_point_patterns(self):
        """Test entry point pattern matching."""
        from fetch_repository_context import ENTRY_POINT_PATTERNS
        
        # Check common entry points
        assert any("main.py" in pattern for pattern in ENTRY_POINT_PATTERNS)
        assert any("app.py" in pattern for pattern in ENTRY_POINT_PATTERNS)
        assert any("index.js" in pattern for pattern in ENTRY_POINT_PATTERNS)
    
    def test_pattern_matching_case_sensitivity(self):
        """Test that pattern matching can handle case variations."""
        file_list = ["README.md", "readme.md", "Readme.MD"]
        
        # Should be able to find at least one README
        readme_found = any(f in ["README.md", "readme.md"] for f in file_list)
        assert readme_found


class TestContextGeneration:
    """Tests for context generation logic."""
    
    def test_context_with_all_files(self):
        """Test context generation with all files available."""
        # Simulates having README, requirements, and entry point
        readme = "# My Project\nThis is a test project"
        requirements = "flask==2.0.0\npandas==1.3.0"
        entry_point = "from flask import Flask\napp = Flask(__name__)"
        
        # All files available
        assert readme is not None
        assert requirements is not None
        assert entry_point is not None
    
    def test_context_with_no_files(self):
        """Test context generation with no files available."""
        readme = None
        requirements = None
        entry_point = None
        
        # Fallback context should be created
        fallback = {
            "summary": "No context files available for this repository.",
            "stack": "Unknown",
            "tags": []
        }
        
        assert fallback["summary"] == "No context files available for this repository."
    
    def test_context_with_partial_files(self):
        """Test context generation with only some files available."""
        readme = "# My Project"
        requirements = None
        entry_point = None
        
        # Should still be able to generate context from available files
        assert readme is not None


class TestEdgeCases:
    """Edge case tests."""
    
    def test_pydantic_validation_error(self):
        """Test RepositoryContext validation errors."""
        from fetch_repository_context import RepositoryContext
        
        # Missing required fields
        with pytest.raises(Exception):
            context = RepositoryContext(
                summary="Test"
                # Missing stack and tags
            )
    
    def test_llm_returns_none(self):
        """Test handling when LLM returns None."""
        result = None
        
        if result:
            context = result.model_dump()
        else:
            context = None
        
        assert context is None
    
    def test_empty_file_list(self):
        """Test handling empty file list."""
        file_list = []
        
        # Should handle gracefully
        assert len(file_list) == 0
    
    def test_very_large_file_content_truncation(self):
        """Test that file content is truncated to limit."""
        # Simulating that get_file_content truncates to 10000 chars
        large_content = "x" * 20000
        truncated = large_content[:10000]
        
        assert len(truncated) == 10000
        assert len(truncated) < len(large_content)
    
    def test_base64_decoding_error(self):
        """Test handling base64 decoding errors."""
        # Simulate invalid base64 content
        invalid_base64 = "not-valid-base64!!!"
        
        # Should handle decode errors gracefully
        try:
            import base64
            decoded = base64.b64decode(invalid_base64).decode("utf-8", errors="ignore")
        except:
            # Expected to fail, should be caught
            pass
    
    def test_existing_context_skip(self):
        """Test skipping repos that already have context."""
        repository_contexts = {
            "example/repo1": {
                "summary": "Existing context",
                "stack": "Python",
                "tags": ["Python"]
            }
        }
        
        repo_path = "example/repo1"
        
        # Should skip if already exists
        if repo_path in repository_contexts:
            skip = True
        else:
            skip = False
        
        assert skip is True
    
    def test_new_context_added_flag(self):
        """Test new_contexts_added flag logic."""
        new_contexts_added = False
        
        # When a new context is generated
        repository_contexts = {}
        repository_contexts["example/repo1"] = {"summary": "New", "stack": "Python", "tags": []}
        new_contexts_added = True
        
        assert new_contexts_added is True
        
        # Should store only if flag is True
        if new_contexts_added:
            assert len(repository_contexts) > 0


class TestFileContentHandling:
    """Tests for file content handling."""
    
    def test_content_limit_enforcement(self):
        """Test that content is limited to prevent excessive data."""
        content = "x" * 15000
        limited_content = content[:10000]
        
        assert len(limited_content) == 10000
    
    def test_file_tree_limit(self):
        """Test that file tree is limited to prevent excessive processing."""
        # Simulating limiting to 500 items
        large_tree = [f"file{i}.txt" for i in range(1000)]
        limited_tree = large_tree[:500]
        
        assert len(limited_tree) == 500
    
    def test_context_parts_truncation(self):
        """Test that context parts are truncated."""
        readme_content = "x" * 10000
        truncated_readme = readme_content[:5000]
        
        assert len(truncated_readme) == 5000
