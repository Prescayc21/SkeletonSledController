import os
import json
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QDoubleSpinBox, QCheckBox, QMessageBox, QScrollArea,
    QGridLayout, QGroupBox, QFrame, QSizePolicy, QComboBox, QProgressBar,
    QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont


class TrayVisualization(QWidget):
    """Widget for visualizing the weight tray layouts"""

    def __init__(self, front_tray=None, back_tray=None, effect_map=None,
                 sensor_positions=None, actual_com=None, ideal_com=None,
                 show_effect_map=False):
        super().__init__()

        # Tray data
        self.front_tray = front_tray or []
        self.back_tray = back_tray or []
        self.effect_map = effect_map or {"front": [], "back": []}

        # COM data
        self.sensor_positions = sensor_positions or []
        self.actual_com = actual_com or (0.0, 0.0)
        self.ideal_com = ideal_com or (0.0, 0.0)

        # Display settings
        self.show_effect_map = show_effect_map
        self.layout_generation_complete = False

        # Set minimum size
        self.setMinimumSize(400, 300)

        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(240, 240, 240))
        self.setPalette(palette)

    def paintEvent(self, event):
        """Paint the tray visualization only when data is ready"""
        print("\n\n*** PAINT EVENT CALLED ***\n\n")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get available size
        width = self.width()
        height = self.height()

        # Draw background for entire area
        painter.fillRect(0, 0, width, height, QColor(240, 240, 240))

        # Calculate scaling and layout
        tray_height = height * 0.65  # Trays take 65% of height
        com_height = height * 0.35  # COM viz takes 35% of height

        # Check if layout generation is complete
        if not hasattr(self, 'layout_generation_complete') or not self.layout_generation_complete:
            # If data isn't ready, show a placeholder message
            print("DEBUG: Layout generation not complete, showing placeholder")
            painter.setPen(QPen(Qt.black))
            painter.drawText(0, 0, width, tray_height, Qt.AlignCenter, "Generating tray layout...")

            # Still try to draw COM visualization if possible
            if self.sensor_positions and len(self.sensor_positions) > 0:
                self._draw_com_visualization(painter, 0, height - com_height, width, com_height)
            else:
                painter.setPen(QPen(Qt.black))
                painter.drawText(0, height - com_height, width, com_height, Qt.AlignCenter,
                                 "Sensor data not available")
        else:
            # Data is ready, proceed with normal drawing
            print("DEBUG: Layout generation complete, drawing trays and COM")
            self._draw_com_visualization(painter, 0, height - com_height, width, com_height)
            self._draw_trays(painter, 0, 0, width, tray_height)

    def set_tray_data(self, front_tray, back_tray, effect_map=None):
        """Update tray layout data with completion tracking"""
        try:
            print("DEBUG: set_tray_data called")

            # Initialize with empty arrays if None is provided
            self.front_tray = front_tray if front_tray is not None else []
            self.back_tray = back_tray if back_tray is not None else []

            # Ensure effect_map is properly initialized
            if effect_map is None:
                effect_map = {"front": [], "back": []}

            # Ensure both front and back keys exist
            if "front" not in effect_map:
                effect_map["front"] = []
            if "back" not in effect_map:
                effect_map["back"] = []

            self.effect_map = effect_map

            # Validate the data completeness
            front_valid = self.front_tray and len(self.front_tray) > 0 and len(self.front_tray[0]) > 0
            back_valid = self.back_tray and len(self.back_tray) > 0 and len(self.back_tray[0]) > 0

            # Set the completion flag if we have at least one valid tray
            self.layout_generation_complete = front_valid or back_valid
            print(f"DEBUG: Layout generation complete: {self.layout_generation_complete}")

            # Force immediate repaint
            print("DEBUG: Calling self.update() in set_tray_data")
            self.update()
            print("DEBUG: set_tray_data completed")
        except Exception as e:
            import traceback
            print(f"ERROR in set_tray_data: {str(e)}")
            traceback.print_exc()

    def set_com_data(self, sensor_positions, actual_com, ideal_com):
        """Update COM data"""
        try:
            print("DEBUG: set_com_data called")
            print(f"DEBUG: sensor_positions: {sensor_positions}")
            print(f"DEBUG: actual_com: {actual_com}")
            print(f"DEBUG: ideal_com: {ideal_com}")

            self.sensor_positions = sensor_positions
            self.actual_com = actual_com
            self.ideal_com = ideal_com

            # Force immediate repaint
            print("DEBUG: Calling self.update() in set_com_data")
            self.update()
            print("DEBUG: set_com_data completed")
        except Exception as e:
            import traceback
            print(f"ERROR in set_com_data: {str(e)}")
            traceback.print_exc()

    def set_show_effect_map(self, show):
        """Toggle effect map display safely"""
        self.show_effect_map = show
        print(f"Effect map display set to: {show}")

        # Update the display
        self.update()

    def _draw_tray_cell(self, painter, x, y, width, height, value, effect_value):
        """Draw a single cell in the tray with its state and effect"""
        try:
            print(f"DEBUG: Drawing cell at ({x}, {y}), size: {width}x{height}, value: {value}, effect: {effect_value}")

            # Draw cell border
            print("DEBUG: Drawing cell border")
            painter.setPen(QPen(Qt.black, 1))
            painter.drawRect(x, y, width, height)

            if value > 0:
                print("DEBUG: Cell has weight (value > 0)")
                # Cell has a weight - fill with dark grey
                if self.show_effect_map and effect_value > 0:
                    print(f"DEBUG: Applying effect map gradient, effect_value: {effect_value}")
                    # Use gradient based on effect value when effect map is on
                    # Effect from 0-1 maps to color from green to red (red = more important)
                    red = int(255 * effect_value)
                    green = int(255 * (1 - effect_value))
                    cell_color = QColor(red, green, 0)  # Red to green gradient
                    print(f"DEBUG: Created gradient color: RGB({red}, {green}, 0)")
                else:
                    print("DEBUG: Using standard dark grey for weighted cell")
                    # Standard weight color - dark grey
                    cell_color = QColor(80, 80, 80)  # Dark grey

                # Use same drawing approach as original
                print("DEBUG: Setting brush and pen for weighted cell")
                painter.setBrush(QBrush(cell_color))
                painter.setPen(Qt.NoPen)

                print("DEBUG: Drawing filled rectangle for weighted cell")
                painter.drawRect(x + 1, y + 1, width - 2, height - 2)
                print("DEBUG: Weighted cell drawing complete")
            else:
                print("DEBUG: Cell is empty (value = 0)")
                # Empty cell - fill with light grey
                cell_color = QColor(220, 220, 220)  # Light grey

                print("DEBUG: Setting brush and pen for empty cell")
                painter.setBrush(QBrush(cell_color))
                painter.setPen(Qt.NoPen)

                print("DEBUG: Drawing filled rectangle for empty cell")
                painter.drawRect(x + 1, y + 1, width - 2, height - 2)
                print("DEBUG: Empty cell drawing complete")

            print("DEBUG: Finished drawing cell")
        except Exception as e:
            import traceback
            print(f"ERROR in _draw_tray_cell: {e}")
            traceback.print_exc()

    def _draw_com_visualization(self, painter, x, y, width, height):
        """Draw the COM visualization similar to LiveFeed"""
        # Background
        painter.fillRect(x, y, width, height, QColor(230, 230, 230))

        # Add border
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawRect(x, y, width, height)

        # Only draw if we have sensor positions
        if not self.sensor_positions:
            # Draw placeholder text
            painter.setPen(QPen(Qt.gray))
            painter.drawText(x, y, width, height, Qt.AlignCenter, "No sensor data available")
            return

        # Calculate scaling to fit sensor positions and COM
        all_points = list(self.sensor_positions)
        if self.actual_com != (0.0, 0.0):
            all_points.append(self.actual_com)
        if self.ideal_com != (0.0, 0.0):
            all_points.append(self.ideal_com)

        if not all_points:
            return

        # Calculate bounds
        x_values = [p[0] for p in all_points]
        y_values = [p[1] for p in all_points]
        min_x, max_x = min(x_values), max(x_values)
        min_y, max_y = min(y_values), max(y_values)

        # Add margins
        margin = 0.1  # 10% margin
        range_x = max_x - min_x
        range_y = max_y - min_y

        if range_x == 0:
            range_x = 1.0
        if range_y == 0:
            range_y = 1.0

        min_x -= range_x * margin
        max_x += range_x * margin
        min_y -= range_y * margin
        max_y += range_y * margin

        # Calculate scale to fit the view
        scale_x = width / (max_x - min_x)
        scale_y = height / (max_y - min_y)
        scale = min(scale_x, scale_y)

        # Calculate offset to center
        offset_x = x + (width - scale * (max_x - min_x)) / 2
        offset_y = y + (height - scale * (max_y - min_y)) / 2

        # Draw coordinate axes
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))

        # Origin is at ideal COM or actual COM or first sensor
        origin = self.ideal_com if self.ideal_com != (0.0, 0.0) else (
            self.actual_com if self.actual_com != (0.0, 0.0) else self.sensor_positions[0]
        )

        # Transform to view coordinates
        origin_x = offset_x + (origin[0] - min_x) * scale
        origin_y = offset_y + (max_y - origin[1]) * scale

        # Draw axes
        painter.drawLine(offset_x, origin_y, offset_x + (max_x - min_x) * scale, origin_y)  # X-axis
        painter.drawLine(origin_x, offset_y, origin_x, offset_y + (max_y - min_y) * scale)  # Y-axis

        # Draw sensor positions
        for i, pos in enumerate(self.sensor_positions):
            # Transform to view coordinates
            pos_x = offset_x + (pos[0] - min_x) * scale
            pos_y = offset_y + (max_y - pos[1]) * scale

            # Draw sensor
            painter.setPen(QPen(Qt.blue, 2))
            painter.setBrush(QBrush(QColor(100, 100, 255)))
            painter.drawEllipse(pos_x - 5, pos_y - 5, 10, 10)

            # Draw sensor label
            painter.setPen(QPen(Qt.white))
            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
            painter.drawRect(pos_x - 15, pos_y - 15, 30, 20)
            painter.drawText(pos_x - 15, pos_y - 15, 30, 20, Qt.AlignCenter, f"S{i + 1}")

        # Draw ideal COM
        if self.ideal_com != (0.0, 0.0):
            # Transform to view coordinates
            ideal_x = offset_x + (self.ideal_com[0] - min_x) * scale
            ideal_y = offset_y + (max_y - self.ideal_com[1]) * scale

            # Draw ideal COM
            painter.setPen(QPen(Qt.green, 2))
            painter.setBrush(QBrush(QColor(0, 200, 0)))
            painter.drawEllipse(ideal_x - 7, ideal_y - 7, 14, 14)

            # Draw label
            painter.setPen(QPen(Qt.white))
            painter.setBrush(QBrush(QColor(0, 100, 0, 160)))
            painter.drawRect(ideal_x - 25, ideal_y - 25, 50, 20)
            painter.drawText(ideal_x - 25, ideal_y - 25, 50, 20, Qt.AlignCenter, "Ideal")

        # Draw actual COM
        if self.actual_com != (0.0, 0.0):
            # Transform to view coordinates
            actual_x = offset_x + (self.actual_com[0] - min_x) * scale
            actual_y = offset_y + (max_y - self.actual_com[1]) * scale

            # Draw actual COM
            painter.setPen(QPen(Qt.red, 2))
            painter.setBrush(QBrush(QColor(255, 50, 50)))
            painter.drawEllipse(actual_x - 7, actual_y - 7, 14, 14)

            # Draw label
            painter.setPen(QPen(Qt.white))
            painter.setBrush(QBrush(QColor(150, 0, 0, 160)))
            painter.drawRect(actual_x - 25, actual_y - 25, 50, 20)
            painter.drawText(actual_x - 25, actual_y - 25, 50, 20, Qt.AlignCenter, "Actual")

            # Draw displacement vector if both COMs exist
            if self.ideal_com != (0.0, 0.0):
                painter.setPen(QPen(QColor(255, 150, 0), 2))
                painter.drawLine(ideal_x, ideal_y, actual_x, actual_y)

    def _draw_trays(self, painter, x, y, width, height):
        """Draw the weight tray layouts with improved empty tray handling"""
        try:
            print(f"DEBUG: _draw_trays called with x={x}, y={y}, width={width}, height={height}")

            # Background
            print("DEBUG: Drawing tray background")
            painter.fillRect(x, y, width, height, QColor(245, 245, 245))

            # Add border
            print("DEBUG: Drawing tray border")
            painter.setPen(QPen(Qt.gray, 1))
            painter.drawRect(x, y, width, height)

            # Carefully check if we have tray data with proper null checking
            has_front_tray = self.front_tray is not None and len(self.front_tray) > 0
            has_back_tray = self.back_tray is not None and len(self.back_tray) > 0

            if not has_front_tray and not has_back_tray:
                print("DEBUG: No tray data available, drawing placeholder text")
                # Draw placeholder text
                painter.setPen(QPen(Qt.gray))
                painter.drawText(x, y, width, height, Qt.AlignCenter, "No tray layout available")
                return

            # Additional safeguard: Check if trays have valid columns
            if has_front_tray and (not self.front_tray[0] or len(self.front_tray[0]) == 0):
                has_front_tray = False
                print("WARNING: Front tray has rows but no columns")

            if has_back_tray and (not self.back_tray[0] or len(self.back_tray[0]) == 0):
                has_back_tray = False
                print("WARNING: Back tray has rows but no columns")

            # If we still have no valid trays after checks, show placeholder
            if not has_front_tray and not has_back_tray:
                painter.setPen(QPen(Qt.gray))
                painter.drawText(x, y, width, height, Qt.AlignCenter, "Invalid tray dimensions")
                return

            print(f"DEBUG: front_tray valid: {has_front_tray}")
            if has_front_tray:
                print(f"DEBUG: front_tray dimensions: {len(self.front_tray)}x{len(self.front_tray[0])}")

            print(f"DEBUG: back_tray valid: {has_back_tray}")
            if has_back_tray:
                print(f"DEBUG: back_tray dimensions: {len(self.back_tray)}x{len(self.back_tray[0])}")

            # Calculate tray sizes and positions
            if has_front_tray and has_back_tray:
                # Both trays - split horizontally
                tray_width = width / 2 - 10  # 10px margin between
                front_x = x + 5
                back_x = x + width / 2 + 5
                print(f"DEBUG: Drawing both trays: front_x={front_x}, back_x={back_x}, tray_width={tray_width}")
            else:
                # Only one tray - center it
                tray_width = width * 0.7
                front_x = back_x = x + (width - tray_width) / 2
                print(f"DEBUG: Drawing single tray at x={front_x}, width={tray_width}")

            # Safely draw front tray if available
            if has_front_tray:
                print("DEBUG: Drawing front tray")
                self._draw_single_tray_safely(painter, front_x, y + 30, tray_width, height - 60,
                                              self.front_tray, self.effect_map.get("front", []), "Front Tray")
                print("DEBUG: Front tray drawing completed")

            # Safely draw back tray if available
            if has_back_tray:
                print("DEBUG: Drawing back tray")
                self._draw_single_tray_safely(painter, back_x, y + 30, tray_width, height - 60,
                                              self.back_tray, self.effect_map.get("back", []), "Back Tray")
                print("DEBUG: Back tray drawing completed")

            print("DEBUG: _draw_trays completed")
        except Exception as e:
            import traceback
            print(f"ERROR in _draw_trays: {e}")
            traceback.print_exc()

            # Provide fallback rendering in case of error
            painter.setPen(QPen(Qt.red))
            painter.drawText(x, y, width, height, Qt.AlignCenter, "Error rendering trays")

    def _draw_single_tray_safely(self, painter, x, y, width, height, tray_layout, effect_map, title):
        """Draw a single tray with more robust error handling"""
        try:
            print(f"DEBUG: _draw_single_tray_safely called for {title}")

            # Draw title
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(x, y - 25, width, 20, Qt.AlignCenter, title)

            # Validate layout data
            if not tray_layout or len(tray_layout) == 0:
                print(f"DEBUG: No layout data for {title}, drawing placeholder")
                painter.setPen(QPen(QColor(180, 180, 180)))
                painter.drawText(x, y, width, height, Qt.AlignCenter, "No layout data")
                return

            # Validate dimensions
            rows = len(tray_layout)
            if rows == 0:
                print(f"DEBUG: {title} has 0 rows, returning")
                return

            # Validate columns safely
            if not tray_layout[0]:
                print(f"DEBUG: {title} has no columns in first row, returning")
                return

            cols = len(tray_layout[0])
            if cols == 0:
                print(f"DEBUG: {title} has 0 columns, returning")
                return

            print(f"DEBUG: {title} dimensions: {rows}x{cols}")

            # Calculate cell size
            cell_width = width / cols
            cell_height = height / rows
            cell_size = min(cell_width, cell_height)
            print(f"DEBUG: Cell size: {cell_size}x{cell_size}")

            # Re-center the tray
            tray_width = cell_size * cols
            tray_height = cell_size * rows
            tray_x = x + (width - tray_width) / 2
            tray_y = y + (height - tray_height) / 2
            print(f"DEBUG: Tray position: x={tray_x}, y={tray_y}, size={tray_width}x{tray_height}")

            # Safely prepare effect map
            if not effect_map or len(effect_map) < rows:
                print(f"DEBUG: Creating empty effect map for {title}")
                effect_map = [[0.0 for _ in range(cols)] for _ in range(rows)]

            # Draw the tray cells with additional validation
            for row in range(rows):
                # Skip invalid rows
                if row >= len(tray_layout):
                    continue

                for col in range(cols):
                    # Skip invalid columns
                    if col >= len(tray_layout[row]):
                        continue

                    try:
                        cell_x = tray_x + col * cell_size
                        cell_y = tray_y + row * cell_size

                        # Get cell state safely
                        cell_value = 0
                        if row < len(tray_layout) and col < len(tray_layout[row]):
                            # Additional null check
                            if tray_layout[row][col] is not None:
                                cell_value = tray_layout[row][col]

                        # Get effect value safely
                        effect_value = 0
                        if row < len(effect_map) and col < len(effect_map[row]):
                            # Additional null check
                            if effect_map[row][col] is not None:
                                effect_value = effect_map[row][col]

                        # Draw cell with safer method
                        self._draw_tray_cell_safely(painter, cell_x, cell_y, cell_size, cell_size,
                                                    cell_value, effect_value)
                    except Exception as e:
                        # Log but continue with other cells
                        print(f"ERROR in cell drawing (row={row}, col={col}): {e}")

            print(f"DEBUG: Finished drawing {title}")
        except Exception as e:
            import traceback
            print(f"ERROR in _draw_single_tray_safely: {e}")
            traceback.print_exc()

    def _draw_tray_cell_safely(self, painter, x, y, width, height, value, effect_value):
        """Draw a single cell in the tray with improved effect map handling"""
        try:
            # Default value if None
            if value is None:
                value = 0
            if effect_value is None:
                effect_value = 0

            # Draw cell border
            painter.setPen(QPen(Qt.black, 1))
            painter.drawRect(x, y, width, height)

            # Determine if this is a weighted cell
            is_weighted = False
            try:
                is_weighted = float(value) > 0
            except (ValueError, TypeError):
                is_weighted = False

            if is_weighted:
                # Cell has a weight - determine color
                cell_color = QColor(80, 80, 80)  # Default dark grey

                # Safely check if effect map is enabled
                show_effect = False
                effect_value_f = 0.0
                try:
                    # Explicitly cast effect_value to float to avoid comparison issues
                    effect_value_f = float(effect_value)
                    show_effect = (hasattr(self, 'show_effect_map') and
                                   self.show_effect_map and
                                   effect_value_f > 0)

                    # Additional debug for this specific cell
                    if effect_value_f > 0:
                        print(f"DEBUG: Cell with effect_value={effect_value_f}, show_effect={show_effect}")
                except (ValueError, TypeError):
                    show_effect = False

                if show_effect:
                    # Apply effect map gradient with debug info
                    try:
                        # Ensure effect value is between 0-1
                        effect_value_f = max(0.0, min(1.0, effect_value_f))

                        # Calculate color gradient - RED = important (high effect), GREEN = less important
                        red = int(255 * effect_value_f)
                        green = int(255 * (1 - effect_value_f))
                        cell_color = QColor(red, green, 0)  # Red to green gradient

                        print(f"DEBUG: Effect map cell: value={effect_value_f}, " +
                              f"color=RGB({red},{green},0)")

                        # Draw filled rectangle for weighted cell
                        painter.setBrush(QBrush(cell_color))
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(x + 1, y + 1, width - 2, height - 2)

                        # Add percentage text for larger cells
                        if width > 20 and height > 15:
                            percentage = int(effect_value_f * 100)
                            painter.setPen(QPen(Qt.white))
                            painter.drawText(x, y, width, height, Qt.AlignCenter, f"{percentage}%")

                    except (ValueError, TypeError) as e:
                        # Fallback to default color on error
                        print(f"ERROR applying effect gradient: {e}")
                        cell_color = QColor(80, 80, 80)  # Dark grey
                        painter.setBrush(QBrush(cell_color))
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(x + 1, y + 1, width - 2, height - 2)
                else:
                    # Standard weight color - dark grey
                    painter.setBrush(QBrush(cell_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(x + 1, y + 1, width - 2, height - 2)
            else:
                # Empty cell - light grey
                cell_color = QColor(220, 220, 220)
                painter.setBrush(QBrush(cell_color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(x + 1, y + 1, width - 2, height - 2)

        except Exception as e:
            # Silent failure - just draw a red cell to indicate error
            painter.setBrush(QBrush(QColor(255, 0, 0, 128)))  # Semi-transparent red
            painter.setPen(Qt.NoPen)
            painter.drawRect(x, y, width, height)

    def debug_effect_map(self):
        """Print effect map values for debugging"""
        print("\n=== EFFECT MAP DEBUG ===")
        print(f"show_effect_map flag: {self.show_effect_map}")

        # Check front tray effect map
        if "front" in self.effect_map and self.effect_map["front"]:
            print("Front tray effect map:")
            for row_idx, row in enumerate(self.effect_map["front"]):
                if row:  # Check if row is not empty
                    # Print a sample of values (first, last, min, max)
                    if len(row) > 0:
                        first = row[0]
                        last = row[-1]
                        min_val = min(row)
                        max_val = max(row)
                        print(f"  Row {row_idx}: first={first}, last={last}, min={min_val}, max={max_val}")

                        # If show_effect_map is True, check for any values > 0
                        if self.show_effect_map:
                            nonzero = [v for v in row if v > 0]
                            if nonzero:
                                print(
                                    f"  Non-zero values: {len(nonzero)}/{len(row)}, avg={sum(nonzero) / len(nonzero)}")
                            else:
                                print("  No non-zero values found")
        else:
            print("Front tray effect map is empty or missing")

        # Check back tray effect map
        if "back" in self.effect_map and self.effect_map["back"]:
            print("Back tray effect map:")
            for row_idx, row in enumerate(self.effect_map["back"]):
                if row:  # Check if row is not empty
                    # Print a sample of values (first, last, min, max)
                    if len(row) > 0:
                        first = row[0]
                        last = row[-1]
                        min_val = min(row)
                        max_val = max(row)
                        print(f"  Row {row_idx}: first={first}, last={last}, min={min_val}, max={max_val}")

                        # If show_effect_map is True, check for any values > 0
                        if self.show_effect_map:
                            nonzero = [v for v in row if v > 0]
                            if nonzero:
                                print(
                                    f"  Non-zero values: {len(nonzero)}/{len(row)}, avg={sum(nonzero) / len(nonzero)}")
                            else:
                                print("  No non-zero values found")
        else:
            print("Back tray effect map is empty or missing")

        print("=== END EFFECT MAP DEBUG ===\n")




class ProfileEditView(QWidget):
    """
    Widget for editing athlete profiles, including name, settings, and tray layouts.
    """

    # Signals
    back_pressed = pyqtSignal()
    save_profile = pyqtSignal(dict)

    def __init__(self, calibration_data=None, bt_manager=None, weight_distribution=None):
        super().__init__()

        # Enable debug logging
        self.debug = True

        self.calibration_data = calibration_data
        self.bt_manager = bt_manager
        if self.bt_manager:
            self.bt_manager.data_signal.connect(self.handle_data)
            print("Connected data_signal to handle_data")

        self.weight_distribution = weight_distribution

        # Log initialization state
        if self.debug:
            print("[ProfileEditView DEBUG] __init__ called")
            print(f"[ProfileEditView DEBUG] calibration_data: {calibration_data}")
            if calibration_data and hasattr(calibration_data, 'filename'):
                print(f"[ProfileEditView DEBUG] calibration filename: {calibration_data.filename}")
            if calibration_data and hasattr(calibration_data, 'calibrations'):
                for i, cal in enumerate(calibration_data.calibrations):
                    print(f"[ProfileEditView DEBUG] Initial calibration for sensor {i}: {cal}")
            print(f"[ProfileEditView DEBUG] bt_manager: {bt_manager}")
            print(f"[ProfileEditView DEBUG] weight_distribution: {weight_distribution}")

        # Current profile data
        self.profile = None
        self.has_generated = False
        self.original_layout = None

        # Data collection state
        self._collecting = False
        self._raw_buffer = []
        self.sensor_averages = None

        # Constants
        self._REQUIRED_SAMPLES = 20
        self._MAX_BUFFER_SIZE = 100
        self._TIMEOUT_MS = 10000  # 10 seconds

        # Data for visualization
        self.sensor_positions = []
        self.actual_com = (0.0, 0.0)
        self.ideal_com = (0.0, 0.0)
        self.displacement = (0.0, 0.0)

        # Set up the UI
        self._setup_ui()

        # Connect to BluetoothManager if available
        if self.bt_manager:
            if self.debug:
                print("[ProfileEditView DEBUG] Connecting to BluetoothManager data_signal")
            self.bt_manager.data_signal.connect(self.handle_data)
        else:
            if self.debug:
                print("[ProfileEditView DEBUG] WARNING: No BluetoothManager available")

    def debug_log(self, message):
        """Log debug messages with consistent formatting"""
        if hasattr(self, 'debug') and self.debug:
            print(f"[ProfileEditView DEBUG] {message}")

    def get_general_settings(self):
        """
        Get general settings from main window or create defaults if not available
        """
        if hasattr(self, 'get_main_window_settings'):
            settings = self.get_main_window_settings()
            if settings:
                print("Retrieved latest settings from main window")
                return settings

        # Try to find general settings through various paths
        try:
            # First attempt: Try to access through main_window directly
            if hasattr(self, 'main_window') and self.main_window:
                if hasattr(self.main_window, 'general_settings_tab'):
                    if hasattr(self.main_window.general_settings_tab, 'get_settings'):
                        settings = self.main_window.general_settings_tab.get_settings()
                        if settings:
                            print("Found general settings from main_window")
                            return settings

            # Second attempt: Try to access through weight_distribution
            if self.weight_distribution:
                if hasattr(self.weight_distribution, 'main_window'):
                    if hasattr(self.weight_distribution.main_window, 'general_settings_tab'):
                        if hasattr(self.weight_distribution.main_window.general_settings_tab, 'get_settings'):
                            settings = self.weight_distribution.main_window.general_settings_tab.get_settings()
                            if settings:
                                print("Found general settings from weight_distribution.main_window")
                                return settings
        except Exception as e:
            print(f"Error retrieving general settings: {e}")

        # If all attempts fail, create default settings
        print("Using default general settings")
        default_settings = {
            "sensor_positions": [
                (-19.0, 0.0),  # Sensor 1
                (19.0, 0.0),  # Sensor 2
                (19.0, 26.5),  # Sensor 3
                (-19.0, 26.5)  # Sensor 4
            ],
            "ideal_com": (0.0, 13.25),
            "weight_tray1": {
                "rows": 8,
                "columns": 6,
                "y_position": 2.0,
                "cell_width": 3.5,
                "cell_height": 2.2,
                "wall_thickness": 0.3
            },
            "weight_tray2": {
                "rows": 8,
                "columns": 5,
                "y_position": 24.5,
                "cell_width": 3.5,
                "cell_height": 2.2,
                "wall_thickness": 0.3
            }
        }
        return default_settings


    def _setup_ui(self):
        """Set up the user interface"""
        # Create a scroll area for the entire view
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        # Main container widget
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)

        # Create header section
        header_layout = QHBoxLayout()

        # Back button
        self.back_button = QPushButton("Back to Profile List")
        self.back_button.clicked.connect(self._on_back_pressed)
        header_layout.addWidget(self.back_button)

        # Add save button
        self.save_button = QPushButton("Save Profile")
        self.save_button.clicked.connect(self._on_save_pressed)
        header_layout.addWidget(self.save_button)

        # Spacer
        header_layout.addStretch()

        # Add header to main layout
        main_layout.addLayout(header_layout)

        # Profile name section
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Profile Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter profile name")
        name_layout.addWidget(self.name_edit)
        main_layout.addLayout(name_layout)

        # Tray toggles
        tray_toggle_layout = QHBoxLayout()
        tray_toggle_layout.addWidget(QLabel("Enable Trays:"))

        # Front tray toggle
        self.front_tray_check = QCheckBox("Back Tray")
        self.front_tray_check.setChecked(True)
        tray_toggle_layout.addWidget(self.front_tray_check)

        # Back tray toggle
        self.back_tray_check = QCheckBox("Front Tray")
        self.back_tray_check.setChecked(True)
        tray_toggle_layout.addWidget(self.back_tray_check)

        # Add toggles to main layout
        main_layout.addLayout(tray_toggle_layout)

        # Data generation section
        gen_layout = QHBoxLayout()

        # Generate button
        self.generate_button = QPushButton("Generate Layout")
        self.generate_button.clicked.connect(self._on_generate_pressed)
        self.generate_button.setMinimumHeight(40)
        gen_layout.addWidget(self.generate_button)

        # Add ungenerate button (initially disabled)
        self.ungenerate_button = QPushButton("Revert to Original")
        self.ungenerate_button.clicked.connect(self._on_ungenerate_pressed)
        self.ungenerate_button.setEnabled(False)
        gen_layout.addWidget(self.ungenerate_button)

        # Add generation section to main layout
        main_layout.addLayout(gen_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self._REQUIRED_SAMPLES)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Create a tab widget for different sections
        tab_widget = QTabWidget()

        # Create layout tab
        layout_tab = QWidget()
        layout_tab_layout = QVBoxLayout(layout_tab)

        # Tray visualization
        print("DEBUG: Creating TrayVisualization instance")
        self.tray_viz = TrayVisualization()
        self.tray_viz.setMinimumSize(400, 300)
        print(f"DEBUG: TrayVisualization created, size set to minimum 400x300")
        layout_tab_layout.addWidget(self.tray_viz)
        print(f"DEBUG: TrayVisualization added to layout")

        # Make sure it's visible
        self.tray_viz.setVisible(True)
        print(f"DEBUG: TrayVisualization visibility set to True")

        # Effect map toggle
        effect_layout = QHBoxLayout()
        effect_layout.addWidget(QLabel("Show Effect Map:"))
        self.effect_map_check = QCheckBox()
        self.effect_map_check.setChecked(False)
        self.effect_map_check.stateChanged.connect(self._on_effect_map_toggled)
        effect_layout.addWidget(self.effect_map_check)
        effect_layout.addStretch()
        layout_tab_layout.addLayout(effect_layout)

        # Add the layout tab
        tab_widget.addTab(layout_tab, "Tray Layout")

        # Create tuning tab
        tuning_tab = QWidget()
        tuning_tab_layout = QVBoxLayout(tuning_tab)

        # Bias tuning section
        bias_group = QGroupBox("Bias Settings")
        bias_layout = QGridLayout()

        # X-bias (left-right)
        bias_layout.addWidget(QLabel("Left-Right Bias:"), 0, 0)
        self.x_bias_slider = QSlider(Qt.Horizontal)
        self.x_bias_slider.setRange(-100, 100)
        self.x_bias_slider.setValue(0)
        self.x_bias_slider.valueChanged.connect(self._on_bias_changed)
        bias_layout.addWidget(self.x_bias_slider, 0, 1)
        self.x_bias_value = QLabel("0.0")
        bias_layout.addWidget(self.x_bias_value, 0, 2)

        # Y-bias (front-back)
        bias_layout.addWidget(QLabel("Front-Back Bias:"), 1, 0)
        self.y_bias_slider = QSlider(Qt.Horizontal)
        self.y_bias_slider.setRange(-100, 100)
        self.y_bias_slider.setValue(0)
        self.y_bias_slider.valueChanged.connect(self._on_bias_changed)
        bias_layout.addWidget(self.y_bias_slider, 1, 1)
        self.y_bias_value = QLabel("0.0")
        bias_layout.addWidget(self.y_bias_value, 1, 2)

        # Max weight
        bias_layout.addWidget(QLabel("Max Weight:"), 2, 0)
        max_weight_layout = QHBoxLayout()
        self.max_weight_spin = QDoubleSpinBox()
        self.max_weight_spin.setRange(1, 1000)
        self.max_weight_spin.setValue(350)
        self.max_weight_spin.valueChanged.connect(self._on_bias_changed)
        max_weight_layout.addWidget(self.max_weight_spin)

        # Unit selector for max weight
        self.weight_unit_combo = QComboBox()
        self.weight_unit_combo.addItems(["g", "kg", "oz", "lb"])
        self.weight_unit_combo.setCurrentText("lb")
        self.weight_unit_combo.currentTextChanged.connect(self._on_bias_changed)
        max_weight_layout.addWidget(self.weight_unit_combo)

        bias_layout.addLayout(max_weight_layout, 2, 1, 1, 2)

        # Threshold settings
        bias_layout.addWidget(QLabel("Enable Threshold:"), 3, 0)
        self.threshold_check = QCheckBox()
        self.threshold_check.setChecked(False)
        self.threshold_check.stateChanged.connect(self._on_bias_changed)
        bias_layout.addWidget(self.threshold_check, 3, 1)

        bias_layout.addWidget(QLabel("Threshold Percent:"), 4, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 50.0)
        self.threshold_spin.setValue(2.5)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.valueChanged.connect(self._on_bias_changed)
        bias_layout.addWidget(self.threshold_spin, 4, 1, 1, 2)

        # Set the bias layout
        bias_group.setLayout(bias_layout)
        tuning_tab_layout.addWidget(bias_group)

        # Initialize bias settings as disabled until generation
        self._set_bias_controls_enabled(False)

        # Add the tuning tab
        tab_widget.addTab(tuning_tab, "Tuning")

        # Add the tab widget to the main layout
        main_layout.addWidget(tab_widget)

        # Add stretch to push everything up
        main_layout.addStretch()

        # Set the container as the scroll widget
        scroll.setWidget(container)

        # Create the outer layout for this widget
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _set_bias_controls_enabled(self, enabled):
        """Enable or disable all bias controls"""
        self.x_bias_slider.setEnabled(enabled)
        self.y_bias_slider.setEnabled(enabled)
        self.max_weight_spin.setEnabled(enabled)
        self.weight_unit_combo.setEnabled(enabled)
        self.threshold_check.setEnabled(enabled)
        self.threshold_spin.setEnabled(enabled)

    def set_profile(self, profile):
        """Set the current profile for editing"""
        self.profile = profile

        if profile:
            # Clear generation state
            self.has_generated = False
            self.original_layout = None
            self.ungenerate_button.setEnabled(False)

            # Update UI with profile data
            self.name_edit.setText(profile.get("name", ""))

            # Set tray toggles
            trays_enabled = profile.get("trays_enabled", {"front": True, "back": True})
            self.front_tray_check.setChecked(trays_enabled.get("front", True))
            self.back_tray_check.setChecked(trays_enabled.get("back", True))

            # Set bias values
            bias = profile.get("bias", {})

            # X bias - scale to slider range (-100 to 100)
            x_bias = bias.get("x", 0.0)
            self.x_bias_slider.setValue(int(x_bias * 10))  # Scale by 10 for more granular control
            self.x_bias_value.setText(f"{x_bias:.1f}")

            # Y bias
            y_bias = bias.get("y", 0.0)
            self.y_bias_slider.setValue(int(y_bias * 10))
            self.y_bias_value.setText(f"{y_bias:.1f}")

            # Max weight
            max_weight = bias.get("max_weight", 350.0)
            self.max_weight_spin.setValue(max_weight)

            # Threshold
            threshold_enabled = bias.get("threshold_enabled", False)
            self.threshold_check.setChecked(threshold_enabled)

            threshold_percent = bias.get("threshold_percent", 2.5)
            self.threshold_spin.setValue(threshold_percent)

            # Check if layout exists and update UI
            layout = profile.get("layout", {})
            front_tray = layout.get("front_tray", [])
            back_tray = layout.get("back_tray", [])
            effect_map = layout.get("effect_map", {"front": [], "back": []})

            if front_tray or back_tray:
                # Layout exists, enable bias controls
                self.has_generated = True
                self._set_bias_controls_enabled(True)
                self.generate_button.setText("Re-Generate Layout")

                # Update tray visualization
                self.tray_viz.set_tray_data(front_tray, back_tray, effect_map)

                # Load sensor data and COM if available
                sensor_data = profile.get("sensor_data", [0.0, 0.0, 0.0, 0.0])
                displacement = profile.get("displacement", [0.0, 0.0])

                # Would need actual sensor positions from settings
                # For now, use placeholder
                self.sensor_positions = [(0, 0), (1, 0), (1, 1), (0, 1)]
                self.actual_com = (0.5, 0.5)
                self.ideal_com = (0.5 + displacement[0], 0.5 + displacement[1])

                self.tray_viz.set_com_data(self.sensor_positions, self.actual_com, self.ideal_com)
            else:
                # No layout, disable bias controls
                self._set_bias_controls_enabled(False)
                self.generate_button.setText("Generate Layout")

    def _update_profile_from_ui(self):
        """Update the profile data from UI controls"""
        if not self.profile:
            return

        # Update name
        self.profile["name"] = self.name_edit.text()

        # Update trays enabled
        self.profile["trays_enabled"] = {
            "front": self.front_tray_check.isChecked(),
            "back": self.back_tray_check.isChecked()
        }

        # Update bias settings
        bias = self.profile.get("bias", {})

        # X bias
        bias["x"] = self.x_bias_slider.value() / 10.0

        # Y bias
        bias["y"] = self.y_bias_slider.value() / 10.0

        # Max weight
        bias["max_weight"] = self.max_weight_spin.value()

        # Threshold settings
        bias["threshold_enabled"] = self.threshold_check.isChecked()
        bias["threshold_percent"] = self.threshold_spin.value()

        # Update the profile
        self.profile["bias"] = bias

        return self.profile

    def _on_back_pressed(self):
        """Handle back button press"""
        # Check for unsaved changes
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before going back?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                self._on_save_pressed()
                self.back_pressed.emit()
            elif reply == QMessageBox.Discard:
                self.back_pressed.emit()
            # Cancel does nothing
        else:
            # No changes, just go back
            self.back_pressed.emit()

    def _has_unsaved_changes(self):
        """Check if there are unsaved changes"""
        if not self.profile:
            return False

        # Create a copy of the profile
        current = self.profile.copy()

        # Update with current UI values
        self._update_profile_from_ui()

        # Check if there are differences
        changed = False

        # Compare name
        if current.get("name") != self.profile.get("name"):
            changed = True

        # Compare trays enabled
        current_trays = current.get("trays_enabled", {})
        new_trays = self.profile.get("trays_enabled", {})
        if (current_trays.get("front") != new_trays.get("front") or
                current_trays.get("back") != new_trays.get("back")):
            changed = True

        # Compare bias settings
        current_bias = current.get("bias", {})
        new_bias = self.profile.get("bias", {})

        bias_keys = ["x", "y", "max_weight", "threshold_enabled", "threshold_percent"]
        for key in bias_keys:
            if current_bias.get(key) != new_bias.get(key):
                changed = True

        # Restore original profile
        self.profile = current

        return changed

    def _on_save_pressed(self):
        """Handle save button press"""
        if not self.profile:
            return

        # Update profile from UI
        self._update_profile_from_ui()

        # Emit signal to save
        self.save_profile.emit(self.profile)

        # Show save confirmation
        QMessageBox.information(
            self,
            "Save Complete",
            "Profile saved successfully.",
            QMessageBox.Ok
        )

    def _on_generate_pressed(self):
        """Handle generate button press"""
        if self._collecting:
            return

        # Update profile from UI
        if self.profile:
            self._update_profile_from_ui()

        # Check if calibration is missing
        calibration_missing = not self.calibration_data or not any(
            self.calibration_data.get_calibration_params(i).get("calibration_points", [])
            for i in range(4)
        )

        if calibration_missing:
            reply = QMessageBox.question(
                self,
                "Calibration Missing",
                "Calibration is missing for one or more sensors.\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if reply != QMessageBox.Yes:
                return

        # Start data collection
        self._start_data_collection()

    def _on_ungenerate_pressed(self):
        """Handle ungenerate button press (revert to original layout)"""
        if not self.original_layout:
            return

        # Confirm revert
        reply = QMessageBox.question(
            self,
            "Revert Layout",
            "Revert to the original layout? Any tuning changes will be lost.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if reply != QMessageBox.Yes:
            return

        # Restore the original layout
        if self.profile:
            self.profile["layout"] = self.original_layout

            # Update visualization
            front_tray = self.original_layout.get("front_tray", [])
            back_tray = self.original_layout.get("back_tray", [])
            effect_map = self.original_layout.get("effect_map", {"front": [], "back": []})

            self.tray_viz.set_tray_data(front_tray, back_tray, effect_map)

        # Disable ungenerate button
        self.ungenerate_button.setEnabled(False)

    def _on_effect_map_toggled(self, state):
        """Handle effect map toggle safely"""
        is_checked = state == Qt.Checked
        print(f"Effect map toggled to {is_checked}")

        # Only proceed if tray_viz exists
        if hasattr(self, 'tray_viz'):
            # Check if method exists before calling
            if hasattr(self.tray_viz, 'set_show_effect_map'):
                self.tray_viz.set_show_effect_map(is_checked)

                # Call debug function to print effect map values
                if hasattr(self.tray_viz, 'debug_effect_map'):
                    self.tray_viz.debug_effect_map()

                # Force a repaint of the visualization
                self.tray_viz.update()
                print(f"Effect map display updated")
            else:
                print("Warning: tray_viz doesn't have set_show_effect_map method")

    def _on_bias_changed(self):
        """Handle changes to bias controls"""
        if not self.profile or not self.has_generated:
            return

        # Update bias display values
        x_bias = self.x_bias_slider.value() / 10.0
        self.x_bias_value.setText(f"{x_bias:.1f}")

        y_bias = self.y_bias_slider.value() / 10.0
        self.y_bias_value.setText(f"{y_bias:.1f}")

        # Update profile from UI
        self._update_profile_from_ui()

        # Add a small delay to avoid rapid recalculations when sliding
        if hasattr(self, '_bias_timer'):
            try:
                self._bias_timer.stop()
            except:
                pass
        else:
            from PyQt5.QtCore import QTimer
            self._bias_timer = QTimer()
            self._bias_timer.setSingleShot(True)
            self._bias_timer.timeout.connect(self._regenerate_layout)

        # Start timer to trigger layout update after 200ms of no changes
        self._bias_timer.start(200)

        # Provide immediate visual feedback that something will happen
        self.ungenerate_button.setEnabled(True)

    def _regenerate_layout(self):
        """Regenerate the tray layout using the current bias settings"""
        if not self.profile or not self.has_generated or not self.weight_distribution:
            return

        try:
            # Refresh settings to get the latest values
            general_settings = self.get_general_settings()
            print(
                f"Using latest general settings for regeneration: tray1={general_settings.get('weight_tray1')['rows']}x{general_settings.get('weight_tray1')['columns']}, tray2={general_settings.get('weight_tray2')['rows']}x{general_settings.get('weight_tray2')['columns']}")

            # Get current bias settings
            bias = self.profile.get("bias", {})

            # Get enabled trays
            trays_enabled = self.profile.get("trays_enabled", {"front": True, "back": True})

            # Get sensor data
            sensor_data = self.profile.get("sensor_data", [0.0, 0.0, 0.0, 0.0])

            # Get sensor positions from settings or default
            sensor_positions = self.sensor_positions

            # Get ideal COM
            ideal_com = self.ideal_com

            # Create bias settings dict for the optimizer
            bias_settings = {
                "x": bias.get("x", 0.0),
                "y": bias.get("y", 0.0)
            }

            # Get max weight
            max_weight = bias.get("max_weight", 350.0)
            max_weight_unit = self.weight_unit_combo.currentText()

            # Get threshold settings
            threshold = None
            if bias.get("threshold_enabled", False):
                threshold = bias.get("threshold_percent", 2.5) / 100.0  # Convert percent to decimal

            # Call the weight distribution calculator to generate layout
            self.weight_distribution.generate_layout(
                sensor_data,
                sensor_positions,
                ideal_com,
                bias_settings,
                general_settings,
                trays_enabled,
                max_weight,
                max_weight_unit,
                threshold
            )

            # The result will come back via the layout_generated signal, which should be connected in the init
            print("Layout regeneration initiated")

            # Enable ungenerate button
            self.ungenerate_button.setEnabled(True)

        except Exception as e:
            print(f"Error during layout regeneration: {str(e)}")
            import traceback
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Regeneration Error",
                f"Failed to regenerate layout: {str(e)}",
                QMessageBox.Ok
            )

    # Add this to the on_layout_generated method in profile_edit_view.py
    def on_layout_generated(self, layout_result):
        """Handle the generated layout result with improved error handling"""
        print("Layout generated received:", layout_result)

        if not self.profile:
            print("WARNING: No profile available to update with layout result")
            return

        try:
            # Store original layout if this is the first generation
            if not self.original_layout:
                self.original_layout = self.profile.get("layout", {}).copy()

            # Deep verify the layout result structure before proceeding
            if not isinstance(layout_result, dict):
                print(f"ERROR: layout_result is not a dictionary: {type(layout_result)}")
                raise ValueError("Invalid layout result format")

            # Make sure the layout has the necessary components
            required_keys = ["front_tray", "back_tray", "effect_map", "final_com", "displacement"]
            for key in required_keys:
                if key not in layout_result:
                    print(f"WARNING: Missing '{key}' in layout result")
                    layout_result[key] = [] if key in ["front_tray", "back_tray"] else {} if key == "effect_map" else (
                    0.0, 0.0)

            # Get front and back trays with proper validation
            front_tray = layout_result.get("front_tray", [])
            back_tray = layout_result.get("back_tray", [])

            # Check if trays are valid (non-empty and properly structured)
            has_front_tray = front_tray and len(front_tray) > 0 and len(front_tray[0]) > 0 if front_tray else False
            has_back_tray = back_tray and len(back_tray) > 0 and len(back_tray[0]) > 0 if back_tray else False

            print(f"DEBUG: Valid front_tray: {has_front_tray}, rows={len(front_tray) if front_tray else 0}, " +
                  f"cols={len(front_tray[0]) if has_front_tray else 0}")
            print(f"DEBUG: Valid back_tray: {has_back_tray}, rows={len(back_tray) if back_tray else 0}, " +
                  f"cols={len(back_tray[0]) if has_back_tray else 0}")

            # Get effect map with proper validation
            effect_map = layout_result.get("effect_map", {"front": [], "back": []})
            if not isinstance(effect_map, dict):
                print(f"ERROR: effect_map is not a dictionary: {type(effect_map)}")
                effect_map = {"front": [], "back": []}

            # Ensure front and back keys exist in effect map
            if "front" not in effect_map:
                effect_map["front"] = []
            if "back" not in effect_map:
                effect_map["back"] = []

            # Update the profile with the validated layout data
            layout = self.profile.get("layout", {})
            layout["front_tray"] = front_tray
            layout["back_tray"] = back_tray
            layout["effect_map"] = effect_map
            self.profile["layout"] = layout

            # Update displacement
            displacement = layout_result.get("displacement", 0.0)
            if isinstance(displacement, (int, float)):
                displacement = [0.0, displacement]  # Convert scalar to vector
            self.profile["displacement"] = displacement

            # Prepare data for visualization - CRUCIAL FIX: Clear the existing tray_viz first
            print("DEBUG: Setting empty trays to visualization before updating with real data")
            # First set empty trays to force a clean state
            self.tray_viz.set_tray_data([], [], {"front": [], "back": []})

            # MODIFIED CODE: Create a swapped effect map for visualization to match the swapped trays
            swapped_effect_map = {
                "front": effect_map.get("back", []),
                "back": effect_map.get("front", [])
            }

            # Then update with the actual data, swapping front and back as needed for correct labeling
            print("DEBUG: Updating tray visualization with validated data")
            if has_back_tray and has_front_tray:
                print(f"DEBUG: Both trays valid, updating visualization")
                self.tray_viz.set_tray_data(back_tray, front_tray, effect_map)
            elif has_back_tray:
                print(f"DEBUG: Only back tray valid, updating visualization")
                self.tray_viz.set_tray_data(back_tray, [], effect_map)
            elif has_front_tray:
                print(f"DEBUG: Only front tray valid, updating visualization")
                self.tray_viz.set_tray_data([], front_tray, effect_map)
            else:
                print(f"DEBUG: No valid trays, keeping visualization empty")
                # Already set to empty above

            # Update COM visualization if available
            final_com = layout_result.get("final_com", (0.0, 0.0))
            if not isinstance(final_com, tuple) and isinstance(final_com, (list, set)):
                final_com = tuple(final_com)  # Convert list/set to tuple if needed
            self.actual_com = final_com

            # Update COM visualization
            if self.sensor_positions:
                print("DEBUG: Updating COM visualization")
                self.tray_viz.set_com_data(
                    self.sensor_positions,
                    self.actual_com,
                    self.ideal_com
                )

            # Set has_generated flag
            self.has_generated = True

            # Enable bias controls if not already enabled
            self._set_bias_controls_enabled(True)

            # Enable ungenerate button
            self.ungenerate_button.setEnabled(True)

            # Update generate button text
            self.generate_button.setText("Re-Generate Layout")

            # Force a repaint of the visualization after a short delay
            # This allows the Qt event loop to process the data updates first
            print("DEBUG: Scheduling delayed update of tray_viz")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.tray_viz.update)

            print("Layout updated in UI successfully")

        except Exception as e:
            import traceback
            print(f"ERROR handling layout result: {str(e)}")
            traceback.print_exc()

            # Don't show error message to user, just log it
            # This prevents UI disruption while still providing debug info

            # Ensure the visualization is in a clean state
            try:
                self.tray_viz.set_tray_data([], [], {"front": [], "back": []})
                self.tray_viz.update()
            except:
                pass

    def refresh_calibration(self):
        """Get the latest calibration data from main window"""
        if hasattr(self, 'main_window') and self.main_window:
            if hasattr(self.main_window, 'current_calibration'):
                print(f"Refreshing calibration from main_window")
                self.calibration_data = self.main_window.current_calibration
                return True

        # Try through weight_distribution
        if self.weight_distribution:
            if hasattr(self.weight_distribution, 'main_window'):
                if hasattr(self.weight_distribution.main_window, 'current_calibration'):
                    print(f"Refreshing calibration from weight_distribution.main_window")
                    self.calibration_data = self.weight_distribution.main_window.current_calibration
                    return True

        print("Could not refresh calibration - no source found")
        return False

    def _start_data_collection(self):
        """Begin data collection for profile generation"""
        if self._collecting:
            return

        print("Starting data collection for profile generation...")

        # Reset collection state
        self._raw_buffer = []
        self.sensor_averages = None
        self._collecting = True

        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.refresh_calibration()
        # Check if calibration is missing using loaded flag
        calibration_missing = True

        if self.calibration_data and hasattr(self.calibration_data, 'is_loaded'):
            print(f"DEBUG: Checking calibration.is_loaded() in _start_data_collection")
            print(f"DEBUG: calibration.loaded = {getattr(self.calibration_data, 'loaded', 'Not found')}")
            print(f"DEBUG: calibration.filename = {getattr(self.calibration_data, 'filename', 'Not found')}")

            if self.calibration_data.is_loaded():
                calibration_missing = False
                print("Calibration data is loaded and marked as valid.")
            else:
                print("Calibration data exists but is not marked as loaded.")
        else:
            print("No calibration data instance or missing is_loaded method.")

        if calibration_missing:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Calibration Missing",
                "Calibration is missing for one or more sensors.\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            print(f"User reply to calibration missing: {reply}")

            if reply != QMessageBox.Yes:
                # User canceled
                print("User canceled due to missing calibration")
                self._collecting = False
                self.progress_bar.setVisible(False)
                self.generate_button.setEnabled(True)
                return

        # Disable generate button during collection
        self.generate_button.setEnabled(False)

        # Begin receiving data
        print("Sending START command to Bluetooth manager")
        try:
            if self.bt_manager:
                self.bt_manager.set_active_tab("users")
                self.bt_manager.send_command("START")
            else:
                print("WARNING: No Bluetooth manager available")
        except Exception as e:
            print(f"Error sending START command: {e}")
            self._collecting = False
            self.progress_bar.setVisible(False)
            self.generate_button.setEnabled(True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Bluetooth Error",
                f"Failed to start data collection: {str(e)}",
                QMessageBox.Ok
            )
            return

        # Start timeout timer
        print("Setting up timeout timer")
        try:
            self._setup_timeout_timer()
        except Exception as e:
            print(f"Error setting up timeout timer: {e}")
            import traceback
            traceback.print_exc()

    def _setup_timeout_timer(self):
        """Set up and start the timeout timer"""
        print(">>> _setup_timeout_timer called")
        print(f"timeout_handler at time of setup: {getattr(self, 'timeout_handler', None)}")

        # Create timer if it doesn't exist
        if not hasattr(self, "_collection_timer"):
            from PyQt5.QtCore import QTimer
            self._collection_timer = QTimer()
            self._collection_timer.setSingleShot(True)

            # Use the timeout handler from UsersTab if available
            if hasattr(self, 'timeout_handler') and self.timeout_handler:
                print("Using timeout handler from UsersTab")
                self._collection_timer.timeout.connect(self.timeout_handler)
            else:
                # Fallback for when timeout_handler isn't available
                print("No timeout handler available, using simplified version")

                # Simple inline function as fallback
                def basic_timeout():
                    if self._collecting:
                        print("Collection timeout - stopping data collection")
                        self._collecting = False
                        if self.bt_manager:
                            self.bt_manager.send_command("STOP")
                        self.progress_bar.setVisible(False)
                        self.generate_button.setEnabled(True)

                self._collection_timer.timeout.connect(basic_timeout)

        # Start the timer
        self._collection_timer.start(self._TIMEOUT_MS)
        print(f"Data collection timeout timer started: {self._TIMEOUT_MS}ms")

    def handle_data(self, line):
        """Handle incoming data lines from BluetoothManager"""
        if not self._collecting:
            return

        if "," in line:
            try:
                # Parse comma-separated values
                print(f"Parsing data line: {line}")
                parts = []
                for part in line.strip().split(","):
                    if part.strip() == "ERROR":
                        print(f"Detected ERROR value in data line")
                        # Skip this line containing an error
                        return
                    try:
                        parts.append(float(part.strip()))
                    except ValueError:
                        print(f"Invalid part '{part}' in data line")
                        # Skip this line with invalid data
                        return

                # Verify we have exactly 4 values
                if len(parts) != 4:
                    print(f"Invalid data line: expected 4 values, got {len(parts)}")
                    return

                # Add to buffer
                self._raw_buffer.append(parts)
                buffer_size = len(self._raw_buffer)

                # Update progress bar
                self.progress_bar.setValue(min(buffer_size, self._REQUIRED_SAMPLES))

                print(f"Collected sample {buffer_size}/{self._REQUIRED_SAMPLES}")

                # Check if we have enough samples
                if buffer_size >= self._REQUIRED_SAMPLES:
                    print("Reached required sample count, finishing collection")
                    self._finish_data_collection()
                    return

                # Check if we hit the maximum buffer size
                if buffer_size >= self._MAX_BUFFER_SIZE:
                    print(f"Warning: Reached maximum buffer size ({self._MAX_BUFFER_SIZE})")
                    self._finish_data_collection()
                    return

            except Exception as e:
                print(f"Unexpected error in handle_data: {e}")
                import traceback
                traceback.print_exc()

    def _finish_data_collection(self):
        """Process collected data and generate tray layout"""
        print("_finish_data_collection called")

        # Stop the timeout timer if it's running
        try:
            if hasattr(self, "_collection_timer") and self._collection_timer.isActive():
                self._collection_timer.stop()
                print("Stopped timeout timer")
        except Exception as e:
            print(f"Error stopping timer: {e}")

        self._collecting = False

        # Stop data streaming
        print("Sending STOP command to Bluetooth manager")
        try:
            if self.bt_manager:
                self.bt_manager.send_command("STOP")
            else:
                print("WARNING: No Bluetooth manager available")
        except Exception as e:
            print(f"Error sending STOP command: {e}")

        # Hide progress bar
        self.progress_bar.setVisible(False)

        # Re-enable generate button and change text to Re-Generate
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Re-Generate Layout")

        # Process the collected data
        try:
            print("Processing collected data")
            print(f"Raw buffer size: {len(self._raw_buffer)}")

            # Safeguard against empty buffer
            if not self._raw_buffer:
                print("Empty raw buffer, cannot process data")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "Data Error",
                    "No data collected. Please try again.",
                    QMessageBox.Ok
                )
                return

            # Compute averages from raw buffer (using only the first _REQUIRED_SAMPLES samples)
            import numpy as np
            samples = np.array(self._raw_buffer[:self._REQUIRED_SAMPLES])
            print(f"Sample array shape: {samples.shape}")

            avg_values = np.mean(samples, axis=0).tolist()
            print(f"Calculated raw average values: {avg_values}")

            # Apply calibration if available
            if self.calibration_data:
                print("Applying calibration to raw averages")
                try:
                    calibrated = self.calibration_data.apply(avg_values, unit="g")
                    self.sensor_averages = calibrated
                    print(f"Calibrated averages: {calibrated}")
                except Exception as e:
                    print(f"Error applying calibration: {e}")
                    import traceback
                    traceback.print_exc()

                    # Fall back to raw values
                    self.sensor_averages = avg_values
                    print("Using raw values due to calibration error")
            else:
                self.sensor_averages = avg_values
                print("No calibration applied - raw values stored")

            # Store sensor data in profile
            if self.profile:
                print("Storing sensor data in profile")
                self.profile["sensor_data"] = self.sensor_averages
            else:
                print("WARNING: No profile available to store data")

            # Generate layout using weight distribution calculator
            print("Initiating layout generation")
            self._generate_initial_layout()

            # Enable bias controls
            print("Enabling bias controls")
            self._set_bias_controls_enabled(True)

            # Mark as generated
            self.has_generated = True

        except Exception as e:
            print(f"Error processing collected data: {e}")
            import traceback
            traceback.print_exc()

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Processing Error",
                f"Failed to process sensor data: {str(e)}",
                QMessageBox.Ok
            )

    def _generate_initial_layout(self):
        """Generate the initial tray layout using collected sensor data"""
        print("_generate_initial_layout called")

        # Check prerequisites
        if not self.profile:
            print("Error: No profile available for layout generation")
            return

        if not self.weight_distribution:
            print("Error: No weight distribution calculator available")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Generation Error",
                "Weight distribution calculator is not available. Cannot generate layout.",
                QMessageBox.Ok
            )
            return

        try:
            # Refresh settings to get the latest values
            general_settings = self.get_general_settings()
            print(
                f"Using latest general settings with tray1: {general_settings.get('weight_tray1')} and tray2: {general_settings.get('weight_tray2')}")

            # Get required data from profile
            print("Extracting parameters for layout generation")

            # Get sensor data
            sensor_data = self.profile.get("sensor_data", [0.0, 0.0, 0.0, 0.0])
            print(f"Using sensor data: {sensor_data}")

            # Validate sensor data
            if len(sensor_data) != 4:
                print(f"Invalid sensor data: Expected 4 values, got {len(sensor_data)}")
                raise ValueError(f"Invalid sensor data: Expected 4 values, got {len(sensor_data)}")

            # Examine weight_distribution object
            print(f"Weight distribution: {type(self.weight_distribution)}")

            # Log all attributes to help diagnose issues
            for attr_name in dir(self.weight_distribution):
                if not attr_name.startswith('__'):
                    try:
                        attr_value = getattr(self.weight_distribution, attr_name)
                        if callable(attr_value):
                            print(f"WeightDistribution has method: {attr_name}")
                        elif not attr_name.startswith('_'):
                            print(f"WeightDistribution.{attr_name} = {attr_value}")
                    except Exception as e:
                        print(f"Error getting WeightDistribution.{attr_name}: {e}")

            # Get required parameters
            print("Getting bias and tray settings")

            # Get bias settings
            bias = self.profile.get("bias", {})

            # Get tray settings
            trays_enabled = self.profile.get("trays_enabled", {"front": True, "back": True})

            # Create bias settings dict
            bias_settings = {
                "x": bias.get("x", 0.0),
                "y": bias.get("y", 0.0)
            }

            # Get sensor positions
            print("Getting sensor positions")

            # Use actual sensor positions from weight_distribution if available
            sensor_positions = None
            if hasattr(self.weight_distribution, 'sensor_positions'):
                sensor_positions = self.weight_distribution.sensor_positions
                print(f"Got sensor positions from weight_distribution: {sensor_positions}")

            # Fallback to default if necessary
            if not sensor_positions or len(sensor_positions) != 4:
                sensor_positions = [(0, 0), (1, 0), (1, 1), (0, 1)]  # Default placeholder
                print(f"Using default sensor positions: {sensor_positions}")

            self.sensor_positions = sensor_positions

            # Get ideal COM
            print("Getting ideal COM")

            # Use actual ideal COM from weight_distribution if available
            ideal_com = None
            if hasattr(self.weight_distribution, 'ideal_com'):
                ideal_com = self.weight_distribution.ideal_com
                print(f"Got ideal COM from weight_distribution: {ideal_com}")

            # Fallback to default if necessary
            if not ideal_com or ideal_com == (0.0, 0.0):
                ideal_com = (0.5, 0.5)  # Default placeholder
                print(f"Using default ideal COM: {ideal_com}")

            self.ideal_com = ideal_com

            print(
                f"Using general settings with tray1: {general_settings.get('weight_tray1')} and tray2: {general_settings.get('weight_tray2')}")

            # Get max weight settings
            max_weight = bias.get("max_weight", 350.0)
            max_weight_unit = self.weight_unit_combo.currentText()

            # Get threshold settings
            threshold = None
            if bias.get("threshold_enabled", False):
                threshold = bias.get("threshold_percent", 2.5) / 100.0  # Convert to decimal

            # Log generation parameters
            print(f"Generating layout with:")
            print(f"  - sensor_data: {sensor_data}")
            print(f"  - sensor_positions: {sensor_positions}")
            print(f"  - ideal_com: {ideal_com}")
            print(f"  - bias_settings: {bias_settings}")
            print(f"  - tray_flags: {trays_enabled}")
            print(f"  - max_weight: {max_weight}{max_weight_unit}")
            print(f"  - threshold: {threshold}")

            # Call the weight distribution calculator to generate layout
            print("Calling weight_distribution.generate_layout()")

            # Check if the method exists
            if not hasattr(self.weight_distribution, 'generate_layout'):
                print("ERROR: weight_distribution has no generate_layout method!")
                raise AttributeError("Weight distribution calculator has no generate_layout method")

            print("==== DEBUGGING TRAY GENERATION ====")
            print(f"Calibration data present: {self.calibration_data is not None}")
            if self.calibration_data and hasattr(self.calibration_data, 'is_loaded'):
                print(f"Calibration is_loaded(): {self.calibration_data.is_loaded()}")
                print(f"Calibration filename: {getattr(self.calibration_data, 'filename', None)}")

            print(f"Weight distribution: {self.weight_distribution}")
            print(f"General settings: {general_settings}")
            if 'weight_tray1' in general_settings:
                print(
                    f"Tray1 dimensions: rows={general_settings['weight_tray1']['rows']}, cols={general_settings['weight_tray1']['columns']}")
            if 'weight_tray2' in general_settings:
                print(
                    f"Tray2 dimensions: rows={general_settings['weight_tray2']['rows']}, cols={general_settings['weight_tray2']['columns']}")
            print("=====================================")

            # Call the method
            self.weight_distribution.generate_layout(
                sensor_data,
                sensor_positions,
                ideal_com,
                bias_settings,
                general_settings,
                trays_enabled,
                max_weight,
                max_weight_unit,
                threshold
            )

            print("Initial layout generation initiated")

        except Exception as e:
            print(f"Error during layout generation: {str(e)}")
            import traceback
            traceback.print_exc()

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Generation Error",
                f"Failed to generate layout: {str(e)}",
                QMessageBox.Ok
            )