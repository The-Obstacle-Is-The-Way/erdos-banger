"""PDF conversion utilities.

This package provides PDF-to-text conversion with math preservation:
- converter.py: PDF conversion backends (Marker, pdfplumber)
"""

from erdos.core.pdf.converter import (
    LLMService,
    PDFConversionConfig,
    PDFConversionResult,
    PDFConverter,
    convert_pdf,
    convert_with_marker,
    convert_with_pdfplumber,
    get_available_converters,
    is_marker_available,
    is_pdfplumber_available,
    select_converter,
)


__all__ = [
    "LLMService",
    "PDFConversionConfig",
    "PDFConversionResult",
    "PDFConverter",
    "convert_pdf",
    "convert_with_marker",
    "convert_with_pdfplumber",
    "get_available_converters",
    "is_marker_available",
    "is_pdfplumber_available",
    "select_converter",
]
