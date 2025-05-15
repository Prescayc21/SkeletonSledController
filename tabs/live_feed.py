from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QGridLayout, QFrame, QSizePolicy, QGroupBox, QTabWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPointF
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPainterPath
from Cal_Math import CalibrationData


class COMVisualization(QWidget):
    """Custom widget for visualizing center of mass and sensor positions"""

    def __init__(self, weight_distribution=None):
        super().__init__()
        self.weight_distribution = weight_distribution

        # Set a minimum size for the visualization
        self.setMinimumSize(400, 300)

        # Visual settings
        self.sensor_size = 10
        self.com_size = 15
        self.arrow_head_size = 10

        # Colors
        self.sensor_color = QColor(100, 100, 255)
        self.ideal_com_color = QColor(0, 200, 0)
        self.actual_com_color = QColor(255, 50, 50)
        self.displacement_color = QColor(255, 150, 0)

        # Cached transform values
        self.transform_data = None

        # Background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(240, 240, 240))
        self.setPalette(palette)

        # Enable tracking for tooltips
        self.setMouseTracking(True)

        # Connect signals from weight distribution if available
        if self.weight_distribution:
            self.weight_distribution.com_calculated.connect(self.update)
            self.weight_distribution.displacement_calculated.connect(self.update)

            # Log signal connections for debugging
        # Connect signals from weight distribution if available
        if self.weight_distribution:
            print("DEBUG [COMViz] Connecting COM signals to update method")
            self.weight_distribution.com_calculated.connect(self.update)
            self.weight_distribution.displacement_calculated.connect(self.update)
            print("DEBUG [COMViz] COM signals connected")

    def paintEvent(self, event):
        """Paint the visualization"""
        if not self.weight_distribution:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get the current size
        width = self.width()
        height = self.height()

        # Get scaling information
        scale, offset_x, offset_y, min_x, min_y, max_x, max_y = self.weight_distribution.calculate_display_scaling(
            width, height)

        # Cache the transform values for tooltip calculations
        self.transform_data = (scale, offset_x, offset_y, min_x, min_y)

        # Draw coordinate axes
        self.draw_axes(painter, width, height, scale, offset_x, offset_y, min_x, min_y)

        # Draw sensor positions
        for i, pos in enumerate(self.weight_distribution.sensor_positions):
            x, y = self.weight_distribution.transform_point(pos, scale, offset_x, offset_y, min_x, min_y)

            # Draw sensor points
            painter.setPen(QPen(self.sensor_color, 2))
            painter.setBrush(QBrush(self.sensor_color))
            painter.drawEllipse(QPointF(x, y), self.sensor_size, self.sensor_size)

            # Create a background rectangle for better label visibility
            label_rect = QRect(int(x - 25), int(y - 25), 50, 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))  # Semi-transparent black background
            painter.drawRect(label_rect)

            # Draw sensor number label
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(label_rect, Qt.AlignCenter, f"S{i + 1}")

            # Add weight value below the sensor if available
            if i < len(self.weight_distribution.sensor_weights) and self.weight_distribution.sensor_weights[i] > 0:
                weight = self.weight_distribution.sensor_weights[i]
                weight_rect = QRect(int(x - 30), int(y + 10), 60, 20)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
                painter.drawRect(weight_rect)
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(weight_rect, Qt.AlignCenter, f"{weight:.1f}")

        # Draw sensor perimeter lines if there are 4 sensors
        sensor_points = []
        for pos in self.weight_distribution.sensor_positions:
            x, y = self.weight_distribution.transform_point(pos, scale, offset_x, offset_y, min_x, min_y)
            sensor_points.append(QPointF(x, y))

        if len(sensor_points) == 4 and all(isinstance(p, QPointF) for p in sensor_points):
            painter.setPen(QPen(Qt.gray, 1, Qt.SolidLine))
            order = [0, 1, 3, 2, 0]  # S1 → S2 → S4 → S3 → S1
            for i in range(len(order) - 1):
                p1 = sensor_points[order[i]]
                p2 = sensor_points[order[i + 1]]
                painter.drawLine(p1, p2)

        # Draw ideal COM
        if self.weight_distribution.ideal_com != (0.0, 0.0):
            x, y = self.weight_distribution.transform_point(
                self.weight_distribution.ideal_com, scale, offset_x, offset_y, min_x, min_y)

            # Draw ideal COM point
            painter.setPen(QPen(self.ideal_com_color, 2))
            painter.setBrush(QBrush(self.ideal_com_color))
            painter.drawEllipse(QPointF(x, y), self.com_size, self.com_size)

            # Draw ideal COM label with background
            label_rect = QRect(int(x - 30), int(y - 30), 60, 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 100, 0, 160)))
            painter.drawRect(label_rect)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(label_rect, Qt.AlignCenter, "Ideal")

        # Draw actual COM
        if self.weight_distribution.actual_com != (0.0, 0.0):
            x, y = self.weight_distribution.transform_point(
                self.weight_distribution.actual_com, scale, offset_x, offset_y, min_x, min_y)

            # Draw actual COM point
            painter.setPen(QPen(self.actual_com_color, 2))
            painter.setBrush(QBrush(self.actual_com_color))
            painter.drawEllipse(QPointF(x, y), self.com_size, self.com_size)

            # Draw actual COM label with background
            label_rect = QRect(int(x - 30), int(y - 30), 60, 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(150, 0, 0, 160)))
            painter.drawRect(label_rect)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(label_rect, Qt.AlignCenter, "Actual")

            # Draw displacement vector if both COMs exist
            if self.weight_distribution.ideal_com != (0.0, 0.0):
                ideal_x, ideal_y = self.weight_distribution.transform_point(
                    self.weight_distribution.ideal_com, scale, offset_x, offset_y, min_x, min_y)

                # Draw arrow from ideal to actual
                self.draw_arrow(painter, ideal_x, ideal_y, x, y, self.displacement_color)

                # Draw displacement value with background
                dx, dy = self.weight_distribution.displacement
                length = (dx ** 2 + dy ** 2) ** 0.5

                mid_x = (ideal_x + x) / 2
                mid_y = (ideal_y + y) / 2

                disp_rect = QRect(int(mid_x - 40), int(mid_y - 15), 80, 20)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(150, 75, 0, 160)))
                painter.drawRect(disp_rect)

                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(disp_rect, Qt.AlignCenter, f"{length:.1f} cm")


    def draw_axes(self, painter, width, height, scale, offset_x, offset_y, min_x, min_y):
        """Draw coordinate axes through ideal COM if available"""
        origin_data = self.weight_distribution.ideal_com if self.weight_distribution and self.weight_distribution.ideal_com != (0.0, 0.0) else (0, 0)
        origin_x, origin_y = self.weight_distribution.transform_point(origin_data, scale, offset_x, offset_y, min_x, min_y)


        # Draw axes if they're visible
        pen = QPen(QColor(180, 180, 180))
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)

        # X-axis
        if min_y <= 0 and 0 <= height:
            painter.drawLine(0, origin_y, width, origin_y)

        # Y-axis
        if min_x <= 0 and 0 <= width:
            painter.drawLine(origin_x, 0, origin_x, height)

    def draw_arrow(self, painter, x1, y1, x2, y2, color):
        """Draw an arrow from (x1,y1) to (x2,y2)"""
        # Arrow parameters
        arrow_size = self.arrow_head_size

        # Calculate direction vector
        dx = x2 - x1
        dy = y2 - y1
        length = (dx ** 2 + dy ** 2) ** 0.5

        if length < 1e-6:  # Avoid division by zero
            return

        # Normalize direction
        dx /= length
        dy /= length

        # Calculate arrow head points
        p1x = x2 - arrow_size * (dx + 0.5 * dy)
        p1y = y2 - arrow_size * (dy - 0.5 * dx)
        p2x = x2 - arrow_size * (dx - 0.5 * dy)
        p2y = y2 - arrow_size * (dy + 0.5 * dx)

        # Draw the line
        painter.setPen(QPen(color, 2))
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw the arrow head
        path = QPainterPath()
        path.moveTo(x2, y2)
        path.lineTo(p1x, p1y)
        path.lineTo(p2x, p2y)
        path.closeSubpath()

        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))
        painter.drawPath(path)

    def tooltip_text_at_position(self, pos):
        """Generate tooltip text for position"""
        if not self.weight_distribution or not self.transform_data:
            return ""

        scale, offset_x, offset_y, min_x, min_y = self.transform_data

        # Convert screen coordinates to data coordinates
        # Inverse of transform_point
        data_x = (pos.x() - offset_x) / scale + min_x
        data_y = min_y - ((pos.y() - offset_y) / scale - min_y)

        # Check if we're near a sensor
        for i, sensor_pos in enumerate(self.weight_distribution.sensor_positions):
            sensor_x, sensor_y = self.weight_distribution.transform_point(
                sensor_pos, scale, offset_x, offset_y, min_x, min_y)

            # Calculate distance to sensor
            dist = ((pos.x() - sensor_x) ** 2 + (pos.y() - sensor_y) ** 2) ** 0.5

            if dist <= self.sensor_size + 5:
                weight = 0
                if len(self.weight_distribution.sensor_weights) > i:
                    weight = self.weight_distribution.sensor_weights[i]

                return f"Sensor {i + 1}\nPosition: ({sensor_pos[0]:.1f}, {sensor_pos[1]:.1f})\nWeight: {weight:.1f}g"

        # Check if we're near ideal COM
        if self.weight_distribution.ideal_com != (0.0, 0.0):
            ideal_x, ideal_y = self.weight_distribution.transform_point(
                self.weight_distribution.ideal_com, scale, offset_x, offset_y, min_x, min_y)

            # Calculate distance to ideal COM
            dist = ((pos.x() - ideal_x) ** 2 + (pos.y() - ideal_y) ** 2) ** 0.5

            if dist <= self.com_size + 5:
                return f"Ideal COM\nPosition: ({self.weight_distribution.ideal_com[0]:.1f}, {self.weight_distribution.ideal_com[1]:.1f})"

        # Check if we're near actual COM
        if self.weight_distribution.actual_com != (0.0, 0.0):
            actual_x, actual_y = self.weight_distribution.transform_point(
                self.weight_distribution.actual_com, scale, offset_x, offset_y, min_x, min_y)

            # Calculate distance to actual COM
            dist = ((pos.x() - actual_x) ** 2 + (pos.y() - actual_y) ** 2) ** 0.5

            if dist <= self.com_size + 5:
                return f"Actual COM\nPosition: ({self.weight_distribution.actual_com[0]:.1f}, {self.weight_distribution.actual_com[1]:.1f})"

        # Return coordinates if nothing else
        return f"({data_x:.1f}, {data_y:.1f})"

    def event(self, event):
        """Handle events including tooltips"""
        if event.type() == event.ToolTip:
            tooltip = self.tooltip_text_at_position(event.pos())
            if tooltip:
                from PyQt5.QtWidgets import QToolTip
                QToolTip.showText(event.globalPos(), tooltip, self)
            else:
                from PyQt5.QtWidgets import QToolTip
                QToolTip.hideText()

        return super().event(event)


class LiveFeedTab(QWidget):
    def __init__(self, bt_manager, main_window, general_settings_tab=None, weight_distribution=None):
        super().__init__()
        self.bt_manager = bt_manager
        self.main_window = main_window
        self.general_settings_tab = general_settings_tab
        self.weight_distribution = weight_distribution
        self.is_active = False

        # Track if we have calibration data
        self.calibration_loaded = False
        self.calibration_filename = None

        # Keep track of tare values (always in grams)
        self.tare_values = [0.0, 0.0, 0.0, 0.0]
        self.tare_active = False

        # Current display unit
        self.current_unit = "g"

        # Initialize center of mass variables
        self.com_position = (0.0, 0.0)
        self.com_offset = (0.0, 0.0)

        # General settings reference
        if self.general_settings_tab:
            # Connect to the settings_changed signal if available
            if hasattr(self.general_settings_tab, 'settings_changed'):
                self.general_settings_tab.settings_changed.connect(self.on_settings_changed)

            # Load initial settings
            self.settings = self.general_settings_tab.get_settings()
        else:
            # Default settings if general_settings_tab is not provided
            self.settings = {
                "sensor_positions": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)],
                "ideal_com": (0.0, 0.0),
                "weight_tray1": {"rows": 3, "columns": 5, "y_position": 10.0},
                "weight_tray2": {"rows": 3, "columns": 5, "y_position": -10.0}
            }

        # Set up the UI
        self.setup_ui()

        # Connect to Bluetooth signals
        self.bt_manager.data_signal.connect(self.handle_data)
        self.bt_manager.status_signal.connect(self.handle_status)

        # Update timer to refresh UI and check calibration status
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.periodic_update)
        self.refresh_timer.start(100)  # Refresh 10 times per second

        # Last received values
        self.last_raw_values = [0.0, 0.0, 0.0, 0.0]
        self.last_calibrated_values = [0.0, 0.0, 0.0, 0.0]
        self.last_adjusted_values = [0.0, 0.0, 0.0, 0.0]

        print("Live Feed tab initialized")

        # Debug - show loaded settings
        if self.general_settings_tab:
            print(f"Loaded settings from General Settings tab: {self.settings}")

    def on_settings_changed(self):
        """Handle updates from the General Settings tab"""
        if self.general_settings_tab:
            # Update settings from the General Settings tab
            self.settings = self.general_settings_tab.get_settings()
            print(f"Updated settings: {self.settings}")

            # Refresh displays or other UI elements that depend on settings
            self.refresh_displays()

    def handle_status(self, msg):
        """Handle status messages from bluetooth manager"""
        print(f"LiveFeed received status: {msg}")

        # Update connection status display
        if "Connected to" in msg:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("color: green")
            print("DEBUG: LiveFeedTab - Set status to Connected")
        # Very explicit check for various disconnection patterns
        elif "Disconnected" in msg or msg == "[Status] Disconnected":
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red")
            print("DEBUG: LiveFeedTab - Set status to Disconnected")

    def setup_ui(self):
        """Set up the user interface"""
        # Create outer layout with scroll area
        outer_layout = QVBoxLayout(self)

        # Create a scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        # Create a container widget for all content
        container = QWidget()
        layout = QVBoxLayout(container)

        # Set the scroll area widget
        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

        # Create header with controls
        header_layout = QHBoxLayout()

        # Status indicators
        status_box = QGroupBox("Status")
        status_layout = QGridLayout()

        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red")
        status_layout.addWidget(QLabel("Connection:"), 0, 0)
        status_layout.addWidget(self.connection_status, 0, 1)

        self.calibration_status = QLabel("No Calibration")
        self.calibration_status.setStyleSheet("color: red")
        status_layout.addWidget(QLabel("Calibration:"), 1, 0)
        status_layout.addWidget(self.calibration_status, 1, 1)

        status_box.setLayout(status_layout)
        header_layout.addWidget(status_box)

        # Controls
        controls_box = QGroupBox("Controls")
        controls_layout = QGridLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_streaming)
        controls_layout.addWidget(self.start_button, 0, 0)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_streaming)
        controls_layout.addWidget(self.stop_button, 0, 1)

        self.tare_button = QPushButton("Tare")
        self.tare_button.clicked.connect(self.tare_sensors)
        controls_layout.addWidget(self.tare_button, 1, 0)

        # Add Clear Tare button
        self.clear_tare_button = QPushButton("Clear Tare")
        self.clear_tare_button.clicked.connect(self.clear_tare)
        controls_layout.addWidget(self.clear_tare_button, 1, 1)

        self.unit_selector = QComboBox()
        self.unit_selector.addItems(["g", "kg", "oz", "lb"])
        self.unit_selector.currentTextChanged.connect(self.unit_changed)
        controls_layout.addWidget(QLabel("Unit:"), 2, 0)
        controls_layout.addWidget(self.unit_selector, 2, 1)

        controls_box.setLayout(controls_layout)
        header_layout.addWidget(controls_box)

        layout.addLayout(header_layout)

        # Create sensor displays
        self.sensor_displays = []

        sensors_layout = QGridLayout()
        sensors_layout.setSpacing(20)

        # Column headers
        sensors_layout.addWidget(QLabel("Sensor"), 0, 0, alignment=Qt.AlignCenter)
        sensors_layout.addWidget(QLabel("Raw Value"), 0, 1, alignment=Qt.AlignCenter)
        sensors_layout.addWidget(QLabel("Calibrated Value"), 0, 2, alignment=Qt.AlignCenter)

        # Create 4 rows of displays (one for each sensor)
        for i in range(4):
            sensor_label = QLabel(f"Sensor {i + 1}")
            sensors_layout.addWidget(sensor_label, i + 1, 0, alignment=Qt.AlignCenter)

            raw_display = QLabel("0.00")
            raw_display.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            raw_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            raw_display.setMinimumWidth(120)
            raw_display.setFont(QFont("Monospace", 12))
            sensors_layout.addWidget(raw_display, i + 1, 1, alignment=Qt.AlignCenter)

            cal_display = QLabel("0.00")
            cal_display.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            cal_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cal_display.setMinimumWidth(120)
            cal_display.setFont(QFont("Monospace", 12))
            cal_display.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sensors_layout.addWidget(cal_display, i + 1, 2, alignment=Qt.AlignCenter)

            self.sensor_displays.append((raw_display, cal_display))

        # Add unit label
        self.unit_label = QLabel(f"Units: {self.current_unit}")
        sensors_layout.addWidget(self.unit_label, 5, 2, alignment=Qt.AlignRight)

        layout.addLayout(sensors_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # COM Section
        com_title = QLabel("Center of Mass")
        com_title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(com_title)

        self.com_visualization = COMVisualization(self.weight_distribution)
        self.com_visualization.setMinimumSize(400, 600)
        layout.addWidget(self.com_visualization)

        # COM Info
        com_info_layout = QGridLayout()

        com_info_layout.addWidget(QLabel("Actual COM:"), 0, 0)
        self.actual_com_label = QLabel("(0.00, 0.00)")
        self.actual_com_label.setFont(QFont("Monospace", 11))
        com_info_layout.addWidget(self.actual_com_label, 0, 1)

        com_info_layout.addWidget(QLabel("Ideal COM:"), 1, 0)
        self.ideal_com_label = QLabel("(0.00, 0.00)")
        self.ideal_com_label.setFont(QFont("Monospace", 11))
        com_info_layout.addWidget(self.ideal_com_label, 1, 1)

        com_info_layout.addWidget(QLabel("Displacement:"), 2, 0)
        self.displacement_label = QLabel("0.00 cm")
        self.displacement_label.setFont(QFont("Monospace", 11))
        com_info_layout.addWidget(self.displacement_label, 2, 1)

        layout.addLayout(com_info_layout)

        if self.weight_distribution:
            print("DEBUG [LiveFeed] Connecting COM signals")
            self.weight_distribution.com_calculated.connect(self.update_com_info)
            self.weight_distribution.displacement_calculated.connect(self.update_displacement_info)
            print("DEBUG [LiveFeed] COM signals connected")

        layout.addStretch()

        # Create tab widget for different views

    def update_com_info(self, com_pos):
        """Update the COM position information displays"""
        print(f"DEBUG [LiveFeed] update_com_info called with: {com_pos}")
        x, y = com_pos
        self.actual_com_label.setText(f"({x:.2f}, {y:.2f})")
        # Force a repaint of the visualization
        self.com_visualization.update()

    def update_displacement_info(self, displacement):
        """Update the displacement information display"""
        dx, dy = displacement
        dist = (dx ** 2 + dy ** 2) ** 0.5
        self.displacement_label.setText(f"{dist:.2f} cm")

        # Update ideal COM display
        x, y = self.weight_distribution.ideal_com if self.weight_distribution else (0.0, 0.0)
        self.ideal_com_label.setText(f"({x:.2f}, {y:.2f})")

    def showEvent(self, event):
        """Called when the tab is shown"""
        super().showEvent(event)
        print("DEBUG [LiveFeed] showEvent called - tab is now visible")

        # Clear duplicate detection cache
        if hasattr(self, '_last_data_line'):
            del self._last_data_line

        # Tell Bluetooth manager this tab is active
        self.bt_manager.set_active_tab("live_feed")
        self.is_active = True

        # Refresh settings from General Settings tab if available
        if self.general_settings_tab and hasattr(self.general_settings_tab, 'get_settings'):
            self.settings = self.general_settings_tab.get_settings()
            print(f"DEBUG [LiveFeed] Retrieved settings: {self.settings}")

            # Update weight distribution with new settings
            if self.weight_distribution:
                # Update sensor positions
                if "sensor_positions" in self.settings:
                    print(f"DEBUG [LiveFeed] Updating sensor positions: {self.settings['sensor_positions']}")
                    self.weight_distribution.update_sensor_positions(self.settings["sensor_positions"])

                # Update ideal COM
                if "ideal_com" in self.settings:
                    print(f"DEBUG [LiveFeed] Updating ideal COM: {self.settings['ideal_com']}")
                    self.weight_distribution.update_ideal_com(self.settings["ideal_com"])

                # Force a recalculation
                print("DEBUG [LiveFeed] Forcing COM recalculation")
                self.weight_distribution.calculate_com()
                print(f"DEBUG [LiveFeed] Current actual COM: {self.weight_distribution.actual_com}")

    def hideEvent(self, event):
        """Called when the tab is hidden"""
        super().hideEvent(event)
        self.is_active = False

        # Stop data if streaming
        if hasattr(self.bt_manager, 'streaming_data') and self.bt_manager.streaming_data:
            if hasattr(self.bt_manager, 'send_stop_command'):
                self.bt_manager.send_stop_command()
            else:
                self.bt_manager.send_command("STOP")

        print("Live feed tab is now hidden")

    def handle_data(self, line):
        """Process incoming data with duplicate protection"""
        if not self.is_active:
            return

        # Skip duplicate lines with a simple cache
        if hasattr(self, '_last_data_line') and self._last_data_line == line:
            print(f"DEBUG: LiveFeedTab skipping duplicate data line: {line[:20]}...")
            return

        # Store this line
        self._last_data_line = line

        # Check if this is sensor data (comma-separated values)
        if "," in line:
            try:
                # Split into values and convert to floats
                values = []
                parts = line.split(",")

                for part in parts:
                    if part.strip() == "ERROR":
                        values.append(0.0)  # Use 0 for error values
                    else:
                        try:
                            values.append(float(part.strip()))
                        except ValueError:
                            values.append(0.0)

                # Ensure we have 4 values
                while len(values) < 4:
                    values.append(0.0)

                # Store raw values (only use first 4 values)
                self.last_raw_values = values[:4]

                # Apply calibration and tare - this updates last_calibrated_values
                self.update_values()

                # Update weight distribution if available - use calibrated values instead of raw
                if self.weight_distribution:
                    # Pass the CALIBRATED values and tare values to weight distribution
                    print(
                        f"DEBUG [LiveFeed] Passing calibrated values to WeightDistribution: {self.last_calibrated_values}")
                    self.weight_distribution.update_sensor_data(
                        self.last_calibrated_values,  # Use calibrated values
                        self.tare_values,
                        pre_calibrated=True  # Flag that these are already calibrated
                    )

            except Exception as e:
                print(f"Error processing data: {e}")
                import traceback
                traceback.print_exc()

        # Check for connection status updates
        elif "Connected" in line:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("color: green")
        elif "Disconnected" in line:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red")

    def update_values(self):
        """Process values in proper order:
        1. Apply calibration to raw values (produces grams)
        2. Subtract tare values (in grams)
        3. Convert to selected display unit
        """
        # Step 1: Apply calibration to get values in grams
        if self.calibration_loaded and hasattr(self.main_window, 'current_calibration'):
            # Use the new calibration system to apply calibrations (produces grams)
            try:
                self.last_calibrated_values = self.main_window.current_calibration.apply(
                    self.last_raw_values,
                    "g"  # Always get calibrated values in grams
                )
                print(f"Calibrated values (g): {[f'{v:.2f}' for v in self.last_calibrated_values]}")
            except Exception as e:
                print(f"Error applying calibration: {e}")
                # Fallback to simple conversion
                self.last_calibrated_values = self.simple_unit_conversion(self.last_raw_values, "g")
        else:
            # If no calibration, just assume raw values are in grams
            self.last_calibrated_values = self.simple_unit_conversion(self.last_raw_values, "g")

        # Step 2: Apply tare offsets (tare values are stored in grams)
        calibrated_minus_tare = [
            cal - tare for cal, tare in zip(self.last_calibrated_values, self.tare_values)
        ]
        print(f"After tare (g): {[f'{v:.2f}' for v in calibrated_minus_tare]}")

        # Step 3: Convert to display unit
        if self.current_unit != "g":
            self.last_adjusted_values = self.simple_unit_conversion(calibrated_minus_tare,
                                                                    "g",
                                                                    self.current_unit)
        else:
            self.last_adjusted_values = calibrated_minus_tare

        print(f"Final values ({self.current_unit}): {[f'{v:.2f}' for v in self.last_adjusted_values]}")

    def periodic_update(self):
        """Run periodic updates - refresh displays and check calibration status"""
        if not self.is_active:
            return

        # Update UI displays
        self.refresh_displays()

        # Check if calibration status has changed
        self.check_calibration_status()

    def refresh_displays(self):
        """Update the UI with the latest values"""
        if not self.is_active:
            return

        # Update each sensor display
        for i in range(4):
            if i < len(self.sensor_displays):
                raw_display, cal_display = self.sensor_displays[i]

                # Update raw value display
                if i < len(self.last_raw_values):
                    raw_display.setText(f"{self.last_raw_values[i]:.2f}")

                # Update calibrated value display
                if i < len(self.last_adjusted_values):
                    cal_display.setText(f"{self.last_adjusted_values[i]:.2f}")

    def start_streaming(self):
        """Start data streaming"""
        if hasattr(self.bt_manager, 'serial') and self.bt_manager.serial and self.bt_manager.serial.is_open:
            self.bt_manager.send_command("START")

    def stop_streaming(self):
        """Stop data streaming"""
        if hasattr(self.bt_manager, 'serial') and self.bt_manager.serial and self.bt_manager.serial.is_open:
            if hasattr(self.bt_manager, 'send_stop_command'):
                self.bt_manager.send_stop_command()
            else:
                self.bt_manager.send_command("STOP")

    def tare_sensors(self):
        """Zero out the current readings by setting tare values"""
        # Store current calibrated values as tare offsets (in grams)
        self.tare_values = self.last_calibrated_values.copy()
        self.tare_active = True

        print(f"Tare values set (g): {[f'{v:.2f}' for v in self.tare_values]}")

        # Update displayed values
        self.update_values()

        # If weight distribution is available, update it with the new tare values
        if self.weight_distribution:
            self.weight_distribution.update_sensor_data(self.last_raw_values, self.tare_values)

    def clear_tare(self):
        """Reset all tare values to zero"""
        self.tare_values = [0.0, 0.0, 0.0, 0.0]
        self.tare_active = False

        print("Tare values cleared")

        # Update displayed values
        self.update_values()

        # If weight distribution is available, update it with the cleared tare values
        if self.weight_distribution:
            self.weight_distribution.update_sensor_data(self.last_raw_values, self.tare_values)

    def unit_changed(self, unit):
        """Handle unit change"""
        print(f"Unit changed from {self.current_unit} to {unit}")

        # Update current unit
        self.current_unit = unit
        self.unit_label.setText(f"Units: {unit}")

        # Update all values with new unit (tare is always in grams, so no conversion needed)
        self.update_values()

    def simple_unit_conversion(self, values, from_unit="g", to_unit="g"):
        """Basic unit conversion for different units"""
        result = []
        for val in values:
            # First convert to grams if not already
            if from_unit != "g":
                if from_unit == "kg":
                    val = val * 1000.0  # kg to g
                elif from_unit == "oz":
                    val = val * 28.3495  # oz to g
                elif from_unit == "lb":
                    val = val * 453.592  # lb to g

            # Then convert from grams to target unit
            if to_unit == "kg":
                result.append(val / 1000.0)  # g to kg
            elif to_unit == "oz":
                result.append(val * 0.03527396195)  # g to oz
            elif to_unit == "lb":
                result.append(val * 0.00220462262)  # g to lb
            else:
                result.append(val)  # keep as g

        return result

    def check_calibration_status(self):
        """Check if calibration data is available"""
        if hasattr(self.main_window, 'current_calibration'):
            cal = self.main_window.current_calibration

            # Get the filename if available
            cal_filename = getattr(cal, 'filename', None)

            # Store filename for display
            if cal_filename != self.calibration_filename:
                self.calibration_filename = cal_filename
                print(f"Calibration filename updated: {cal_filename}")

            # Check if we have non-default calibration data
            has_real_calibration = False

            if hasattr(cal, 'calibrations') and len(cal.calibrations) > 0:
                # Check if any sensor has non-default calibration
                for sensor_cal in cal.calibrations:
                    if isinstance(sensor_cal, dict):
                        # Look for non-default slope or intercept
                        if sensor_cal.get('slope', 1.0) != 1.0 or sensor_cal.get('intercept', 0.0) != 0.0:
                            has_real_calibration = True
                            break

            # Update calibration status
            old_status = self.calibration_loaded
            self.calibration_loaded = has_real_calibration

            # Update UI
            if self.calibration_loaded:
                if cal_filename:
                    self.calibration_status.setText(f"Calibration: {cal_filename}")
                else:
                    self.calibration_status.setText("Calibration Loaded")
                self.calibration_status.setStyleSheet("color: green")
            else:
                self.calibration_status.setText("Default Calibration")
                self.calibration_status.setStyleSheet("color: orange")

            # If calibration status changed, update values
            if old_status != self.calibration_loaded:
                self.update_values()
        else:
            self.calibration_loaded = False
            self.calibration_filename = None
            self.calibration_status.setText("No Calibration")
            self.calibration_status.setStyleSheet("color: red")