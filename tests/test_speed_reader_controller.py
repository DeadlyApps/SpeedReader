"""Unit tests for SpeedReaderController."""
import pytest
from Controllers.SpeedReaderController import SpeedReaderController
from Frames.MainFrame import MainFrame


class TestSpeedReaderController:
    """Tests for the SpeedReaderController class."""

    def test_controller_title_is_speed_reader(self, app):
        """Controller window should have 'Speed Reader' as title."""
        # Act
        title = app.title()

        # Assert
        assert title == "Speed Reader"

    def test_controller_contains_main_frame(self, app):
        """Controller should contain a MainFrame as its child."""
        # Act
        children = app.winfo_children()

        # Assert
        assert len(children) == 1
        assert isinstance(children[0], MainFrame)

    def test_controller_grid_column_is_configured(self, app):
        """Controller should have column 0 configured with weight 1."""
        # Act
        column_info = app.grid_columnconfigure(0)

        # Assert
        assert column_info['weight'] == 1

    def test_controller_grid_row_is_configured(self, app):
        """Controller should have row 0 configured with weight 1."""
        # Act
        row_info = app.grid_rowconfigure(0)

        # Assert
        assert row_info['weight'] == 1
