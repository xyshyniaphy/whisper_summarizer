"""
PPTX Service Font Exception Tests

Tests for pptx_service.py font exception handlers:
- Lines 41-42: set_chinese_font exception handler (continues to next font)
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from app.services.pptx_service import set_chinese_font, CHINESE_FONTS


@pytest.mark.unit
class TestPPTXFontExceptions:
    """Test PPTX font exception handlers."""

    def test_font_exception_continues_to_next_font_hits_lines_41_42(
        self
    ) -> None:
        """
        Test that font setting exceptions are caught and continues to next font.

        This targets pptx_service.py lines 41-42:
        ```python
        except Exception:
            continue
        ```

        Scenario:
        1. Mock text_frame with runs
        2. Make first few font.name assignments raise exceptions
        3. Should catch exception and try next font (lines 41-42)
        4. Eventually succeed with a working font
        """
        # Mock text frame with paragraph and run
        mock_text_frame = MagicMock()
        mock_paragraph = MagicMock()
        mock_run = MagicMock()
        mock_font = MagicMock()

        # Set up the chain: text_frame.paragraphs -> [paragraph] -> paragraph.runs -> [run]
        mock_text_frame.paragraphs = [mock_paragraph]
        mock_paragraph.runs = [mock_run]

        # Make run.font return our mock font
        mock_run.font = mock_font

        # Track font name assignments
        font_names_set = []

        def side_effect_set_font_name(value):
            font_names_set.append(value)
            # Raise exception for first 3 fonts
            if len(font_names_set) < 4:
                raise Exception(f"Font {value} not available")
            # Success on 4th font
            return None

        # Use PropertyMock for the name property
        type(mock_font).name = PropertyMock(side_effect=side_effect_set_font_name)

        # Call the function - should catch exceptions and continue
        set_chinese_font(mock_text_frame)

        # Verify that multiple fonts were tried (exceptions were caught)
        assert len(font_names_set) >= 4, f"Expected at least 4 font attempts, got {len(font_names_set)}: {font_names_set}"

        # Verify the final font that succeeded
        assert font_names_set[-1] == CHINESE_FONTS[3]  # 4th font should succeed

    def test_all_fonts_fail_still_continues_hits_lines_41_42(
        self
    ) -> None:
        """
        Test that even when all fonts fail, function continues gracefully.

        This targets pptx_service.py lines 41-42:
        ```python
        except Exception:
            continue
        ```

        Scenario:
        1. All font assignments raise exceptions
        2. Should continue through all fonts without crashing
        """
        # Mock text frame with paragraph and run
        mock_text_frame = MagicMock()
        mock_paragraph = MagicMock()
        mock_run = MagicMock()
        mock_font = MagicMock()

        mock_text_frame.paragraphs = [mock_paragraph]
        mock_paragraph.runs = [mock_run]
        mock_run.font = mock_font

        # Track font attempts
        font_attempts = []

        def side_effect_set_font_name(value):
            font_attempts.append(value)
            # All fonts fail
            raise Exception(f"Font {value} not available")

        # Use PropertyMock for the name property
        type(mock_font).name = PropertyMock(side_effect=side_effect_set_font_name)

        # Call the function - should handle all exceptions gracefully
        set_chinese_font(mock_text_frame)

        # Verify all fonts were tried
        assert len(font_attempts) == len(CHINESE_FONTS), f"Expected {len(CHINESE_FONTS)} font attempts, got {len(font_attempts)}"

        # Verify no exception was raised (function completed successfully)
        assert True  # If we got here, the function handled all exceptions

    def test_font_exception_per_run_multiple_runs(
        self
    ) -> None:
        """
        Test that exception handling works per run, not per text_frame.

        This targets pptx_service.py lines 41-42 in the context of multiple runs.

        Scenario:
        1. Text frame with multiple runs (paragraphs)
        2. Each run has different font availability
        3. Should handle exceptions independently for each run
        """
        # Mock text frame with 2 paragraphs, each with different font behavior
        mock_text_frame = MagicMock()

        mock_paragraph1 = MagicMock()
        mock_run1 = MagicMock()
        mock_font1 = MagicMock()

        mock_paragraph2 = MagicMock()
        mock_run2 = MagicMock()
        mock_font2 = MagicMock()

        mock_text_frame.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_paragraph1.runs = [mock_run1]
        mock_paragraph2.runs = [mock_run2]

        mock_run1.font = mock_font1
        mock_run2.font = mock_font2

        # Run 1: First 2 fonts fail, 3rd succeeds
        run1_attempts = []

        def side_effect_run1(value):
            run1_attempts.append(value)
            if len(run1_attempts) < 3:
                raise Exception(f"Font {value} not available for run1")
            return None

        type(mock_font1).name = PropertyMock(side_effect=side_effect_run1)

        # Run 2: First font succeeds
        run2_attempts = []

        def side_effect_run2(value):
            run2_attempts.append(value)
            return None  # Success on first try

        type(mock_font2).name = PropertyMock(side_effect=side_effect_run2)

        # Call the function
        set_chinese_font(mock_text_frame)

        # Verify run 1 tried 3 fonts
        assert len(run1_attempts) == 3, f"Run 1: Expected 3 font attempts, got {len(run1_attempts)}"

        # Verify run 2 tried 1 font
        assert len(run2_attempts) == 1, f"Run 2: Expected 1 font attempt, got {len(run2_attempts)}"
