"""Unit tests for arXiv source extraction."""

import io
import tarfile

import pytest

from erdos.core.clients.arxiv import extract_arxiv_text


def test_extract_arxiv_text_largest_tex_wins():
    """Test that the largest .tex file is selected for extraction."""
    # Create a synthetic tar.gz with multiple .tex files
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add smaller .tex file
        small_tex = (
            b"\\documentclass{article}\n\\begin{document}\nSmall.\n\\end{document}"
        )
        small_info = tarfile.TarInfo(name="small.tex")
        small_info.size = len(small_tex)
        tar.addfile(small_info, io.BytesIO(small_tex))

        # Add larger .tex file
        large_tex = (
            b"\\documentclass{article}\n"
            b"\\begin{document}\n"
            b"This is the main content with more text. " * 20 + b"\n\\end{document}"
        )
        large_info = tarfile.TarInfo(name="main.tex")
        large_info.size = len(large_tex)
        tar.addfile(large_info, io.BytesIO(large_tex))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should extract the larger file (main.tex)
    assert b"main content" in result
    assert b"Small." not in result


def test_extract_arxiv_text_nested_tex_files():
    """Test extraction works with .tex files in subdirectories."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add .tex file in subdirectory
        tex_content = b"\\documentclass{article}\n\\begin{document}\nNested content.\n\\end{document}"
        tex_info = tarfile.TarInfo(name="src/main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    assert b"Nested content" in result


def test_extract_arxiv_text_caps_at_2mb():
    """Test that extracted text is capped at 2 MiB."""
    # Create a very large .tex file (3 MiB)
    large_content = b"x" * (3 * 1024 * 1024)  # 3 MiB
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_info = tarfile.TarInfo(name="huge.tex")
        tex_info.size = len(large_content)
        tar.addfile(tex_info, io.BytesIO(large_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should be capped at 2 MiB
    assert len(result) == 2 * 1024 * 1024


def test_extract_arxiv_text_no_tex_files():
    """Test extraction fails gracefully when no .tex files present."""
    # Create tar with only non-.tex files
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        readme_content = b"This is a README file"
        readme_info = tarfile.TarInfo(name="README.md")
        readme_info.size = len(readme_content)
        tar.addfile(readme_info, io.BytesIO(readme_content))

    tar_buffer.seek(0)

    with pytest.raises(ValueError, match=r"No \.tex files found"):
        extract_arxiv_text(tar_buffer.read())


def test_extract_arxiv_text_utf8_decode_with_errors_replace():
    """Test that invalid UTF-8 sequences are replaced, not crashed."""
    # Create .tex file with invalid UTF-8
    tex_content = b"Valid text \xff\xfe invalid bytes more text"
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_info = tarfile.TarInfo(name="mixed.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should decode successfully with replacement characters
    assert b"Valid text" in result
    assert b"more text" in result
    # The invalid bytes should be replaced (exact replacement depends on implementation)


def test_extract_arxiv_text_empty_tarball():
    """Test extraction with empty tarball."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz"):
        pass  # Empty tarball

    tar_buffer.seek(0)

    with pytest.raises(ValueError, match=r"No \.tex files found"):
        extract_arxiv_text(tar_buffer.read())
