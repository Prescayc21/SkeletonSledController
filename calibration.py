from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit,
    QHBoxLayout, QScrollArea, QFileDialog, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from Cal_Math import CalibrationData
import numpy as np
import os


class CalibrationTab(QWidget):
    def __init__(self, bt_manager, main_window):
        super().__init__()
        self.bt_manager = bt_manager
        self.cal_data = CalibrationData()
        self.current_sensor = 0  # Index 0-3 for sensors
        self.sample_buffer = []

        # New structure to store calibration points
        self.calibration_points = []  # List of (raw_value, weight, unit) tuples

        self.baseline = 0.0
        self.baseline_collected = False
        self.main_window = main_window

        # Total number of sensors supported
        self.total_sensors = 4

        # Flag to track if we're currently collecting baseline data
        self.collecting_baseline = False
        # Flag to track if we're currently collecting weight data
        self.collecting_weight = False

        # Set up the UI
        self.setup_ui()

        # Connect to data signal using the standard Python method
        # This avoids IDE warnings but works in PyQt
        self.bt_manager.data_signal.connect(self.handle_data_line)

        # Connect to the stop_completed signal if it exists
        if hasattr(self.bt_manager, 'stop_completed_signal'):
            self.bt_manager.stop_completed_signal.connect(self.handle_stop_result)

        # Debug message
        print("Calibration tab initialized")

    def handle_stop_result(self, success):
        """Handle the result of a STOP command"""
        if success:
            self.status_log.append("Data streaming stopped successfully.")
        else:
            self.status_log.append("[Warning] Failed to confirm data stream stop.")

    def setup_ui(self):
        """Set up all UI elements"""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setAlignment(Qt.AlignTop)

        self.instructions = QLabel("Click 'Start Calibration' to begin.", container)
        self.layout.addWidget(self.instructions)

        self.start_button = QPushButton("Start Calibration", container)
        self.start_button.clicked.connect(self.start_calibration)
        self.layout.addWidget(self.start_button)

        self.load_button = QPushButton("Load Calibration", container)
        self.load_button.clicked.connect(self.load_calibration)
        self.layout.addWidget(self.load_button)

        self.skip_button = QPushButton("Skip Sensor", container)
        self.skip_button.clicked.connect(self.skip_sensor)
        self.skip_button.setVisible(False)
        self.layout.addWidget(self.skip_button)

        self.live_reading_label = QLabel("Live Reading: ---", container)
        self.live_reading_label.setStyleSheet("font-size: 18px;")
        self.live_reading_label.setVisible(False)
        self.layout.addWidget(self.live_reading_label)

        self.zero_button = QPushButton("Start Baseline Measurement", container)
        self.zero_button.clicked.connect(self.start_baseline)
        self.zero_button.setVisible(False)
        self.layout.addWidget(self.zero_button)

        unit_row = QHBoxLayout()
        self.unit_selector = QComboBox(container)
        self.unit_selector.addItems(["g", "kg", "oz", "lb"])
        unit_row.addWidget(QLabel("Unit:", container))
        unit_row.addWidget(self.unit_selector)

        self.weight_input = QLineEdit(container)
        self.weight_input.setPlaceholderText("Enter known weight")
        self.weight_input.setFixedWidth(100)
        unit_row.addWidget(self.weight_input)

        self.measure_button = QPushButton("Measure Weight", container)
        self.measure_button.clicked.connect(self.measure_weight)
        self.measure_button.setVisible(False)
        unit_row.addWidget(self.measure_button)
        self.layout.addLayout(unit_row)

        self.finish_sensor_button = QPushButton("Finish Sensor Calibration", container)
        self.finish_sensor_button.clicked.connect(self.finish_sensor)
        self.finish_sensor_button.setVisible(False)
        self.layout.addWidget(self.finish_sensor_button)

        self.status_log = QTextEdit(container)
        self.status_log.setReadOnly(True)
        self.status_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.status_log)

        self.save_button = QPushButton("Save Calibration Profile...", container)
        self.save_button.clicked.connect(self.save_calibration)
        self.save_button.setVisible(False)
        self.layout.addWidget(self.save_button)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def showEvent(self, event):
        """Called when the calibration tab becomes visible"""
        super().showEvent(event)
        # Tell the bluetooth manager we're the active tab using our identifier
        self.bt_manager.set_active_tab("calibration")
        print("Calibration tab is now visible")

        # If we're actively collecting data, make sure to restart data flow
        if self.collecting_baseline or self.collecting_weight:
            self.check_and_start_data()

    def hideEvent(self, event):
        """Called when the calibration tab is hidden"""
        super().hideEvent(event)

        # Stop data streaming when leaving the tab
        # Only if we're in calibration mode
        if hasattr(self, 'collecting_baseline') and (self.collecting_baseline or self.collecting_weight):
            self.bt_manager.send_stop_command()
            print("Calibration tab hidden, stopping data stream")

            # Reset collection flags
            self.collecting_baseline = False
            self.collecting_weight = False

    def handle_data_line(self, line):
        """Process incoming data from Bluetooth"""
        # Skip processing if we've moved past all valid sensors
        if hasattr(self, 'total_sensors') and self.current_sensor >= self.total_sensors:
            return
        # Check if this is sensor data (comma-separated values)
        if "," in line:
            try:
                # Split into values
                values = line.split(",")

                # Only proceed if we have enough values
                if len(values) > self.current_sensor:
                    # Get the value for the current sensor
                    try:
                        current_value = float(values[self.current_sensor])

                        # Always update the live reading display
                        print(f"Updating live reading: {current_value:.2f}")
                        self.live_reading_label.setText(f"Live Reading: {current_value:.2f}")

                        # Process baseline data collection if active
                        if self.collecting_baseline:
                            self.sample_buffer.append(current_value)
                            print(f"Baseline sample {len(self.sample_buffer)}/20: {current_value:.2f}")

                            # Update status log but not too frequently
                            if len(self.sample_buffer) % 4 == 0 or len(self.sample_buffer) == 20:
                                self.status_log.append(
                                    f"Baseline sample {len(self.sample_buffer)}/20: {current_value:.2f}")

                            # Check if we've collected enough samples
                            if len(self.sample_buffer) >= 20:
                                # Finish the baseline collection
                                self.baseline = sum(self.sample_buffer) / 20
                                self.baseline_collected = True
                                self.collecting_baseline = False

                                # Add baseline as a calibration point with weight 0
                                self.add_calibration_point(self.baseline, 0.0, "g")
                                print(f"Added baseline as calibration point: raw={self.baseline:.2f}, weight=0g")

                                # Update UI
                                self.status_log.append(f"Baseline completed! Average: {self.baseline:.2f}")
                                self.instructions.setText(
                                    "Baseline done. Place known weight and click 'Measure Weight'.")
                                self.zero_button.setEnabled(True)
                                self.measure_button.setVisible(True)

                                print("Baseline collection complete")

                        # Process weight data collection if active
                        elif self.collecting_weight:
                            self.sample_buffer.append(current_value)
                            print(f"Weight sample {len(self.sample_buffer)}/20: {current_value:.2f}")

                            # Update status log but not too frequently
                            if len(self.sample_buffer) % 4 == 0 or len(self.sample_buffer) == 20:
                                self.status_log.append(
                                    f"Weight sample {len(self.sample_buffer)}/20: {current_value:.2f}")

                            # Check if we've collected enough samples
                            if len(self.sample_buffer) >= 20:
                                # Finish the weight measurement
                                avg_raw = sum(self.sample_buffer) / 20
                                weight = self._current_known
                                unit = self.unit_selector.currentText()

                                # Add this as a calibration point
                                self.add_calibration_point(avg_raw, weight, unit)

                                print(f"Added calibration point: raw={avg_raw:.2f}, weight={weight}{unit}")
                                print(f"Current calibration points: {self.calibration_points}")

                                # Update UI
                                self.collecting_weight = False
                                self.status_log.append(
                                    f"Weight measurement completed! Raw: {avg_raw:.2f}, Weight: {weight} {unit}")
                                self.instructions.setText("Point recorded. Measure again or finish sensor.")
                                self.finish_sensor_button.setVisible(True)
                                self.measure_button.setEnabled(True)

                                print("Weight measurement complete")
                    except ValueError as e:
                        print(f"Error converting value to float: {e}")
                else:
                    print(f"Current sensor {self.current_sensor} out of range (values: {len(values)})")
            except Exception as e:
                print(f"Error processing data: {e}")

    def add_calibration_point(self, raw_value, weight, unit):
        """Add a calibration point to the current sensor data"""
        # Store the calibration point
        self.calibration_points.append((raw_value, weight, unit))
        print(f"Added calibration point: raw={raw_value:.2f}, weight={weight}{unit}")

        # If we have at least 2 points, calculate and show preliminary fit
        if len(self.calibration_points) >= 2:
            try:
                # Convert all points to common unit (g)
                points_in_g = []
                for raw, weight, point_unit in self.calibration_points:
                    # Convert weight to grams
                    if point_unit == "kg":
                        weight_g = weight * 1000
                    elif point_unit == "oz":
                        weight_g = weight * 28.3495
                    elif point_unit == "lb":
                        weight_g = weight * 453.592
                    else:  # Already in grams
                        weight_g = weight

                    points_in_g.append((raw, weight_g))

                # Extract x and y values for fitting
                x_vals = np.array([point[0] for point in points_in_g])
                y_vals = np.array([point[1] for point in points_in_g])

                # Perform linear regression
                slope, intercept = np.polyfit(x_vals, y_vals, 1)

                # Calculate R-squared to measure fit quality
                y_pred = slope * x_vals + intercept
                ss_total = np.sum((y_vals - np.mean(y_vals)) ** 2)
                ss_residual = np.sum((y_vals - y_pred) ** 2)
                r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

                print(f"Preliminary fit: slope={slope:.4f}, intercept={intercept:.2f}, R²={r_squared:.4f}")
                self.status_log.append(f"Fit quality: R² = {r_squared:.4f}")

            except Exception as e:
                print(f"Error calculating preliminary fit: {e}")

    def start_calibration(self):
        """Begin the calibration process"""
        # Make sure we're the active tab
        self.bt_manager.set_active_tab("calibration")

        # Ensure data is flowing
        if not self.check_and_start_data():
            return

        # Start with the first sensor
        self.current_sensor = 0
        self.status_log.clear()
        self._enter_sensor_step()

        print("Started calibration process")

    def check_and_start_data(self):
        """Ensure data is flowing"""
        if hasattr(self.bt_manager, 'serial') and self.bt_manager.serial and self.bt_manager.serial.is_open:
            self.status_log.append("Starting data stream...")
            print("Sending START command")

            # Send START command - tab management is now handled by bt_manager
            self.bt_manager.send_command("START")
            return True
        else:
            self.status_log.append("Error: No active connection. Please connect first.")
            return False

    def skip_sensor(self):
        """Skip the current sensor"""
        # Set default calibration parameters
        self.cal_data.set_sensor_calibration(self.current_sensor, [])
        self.status_log.append(f"Sensor {self.current_sensor + 1} skipped.")
        self._next_sensor()

    def start_baseline(self):
        """Begin baseline measurement - collecting 20 samples"""
        # Make sure we're the active tab
        self.bt_manager.set_active_tab("calibration")

        # Ensure data is flowing
        if not self.check_and_start_data():
            return

        # Reset calibration points for this sensor
        self.calibration_points = []

        # Reset and prepare for baseline collection
        self.instructions.setText("Baseline: ensure nothing on scale.")
        self.sample_buffer = []
        self.baseline_collected = False
        self.zero_button.setEnabled(False)
        self.measure_button.setVisible(False)

        # Set flag to start collecting baseline data
        self.collecting_baseline = True
        self.collecting_weight = False

        self.status_log.append("Starting baseline measurement. Keep the scale empty.")
        print("Starting baseline measurement")

    def measure_weight(self):
        """Begin weight measurement - collecting 20 samples"""
        # Check that we have a valid weight input
        try:
            known = float(self.weight_input.text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Enter a valid weight.")
            return

        # Make sure we're the active tab
        self.bt_manager.set_active_tab("calibration")

        # Ensure data is flowing
        if not self.check_and_start_data():
            return

        # Reset and prepare for weight measurement
        self.instructions.setText(f"Measuring weight ({known} {self.unit_selector.currentText()})...")
        self.sample_buffer = []
        self._current_known = known
        self.measure_button.setEnabled(False)

        # Set flag to start collecting weight data
        self.collecting_weight = True
        self.collecting_baseline = False

        self.status_log.append(f"Starting weight measurement with {known} {self.unit_selector.currentText()}.")
        print(f"Starting weight measurement with {known}")

    def finish_sensor(self):
        """Complete calibration for this sensor"""
        if not self.baseline_collected or len(self.calibration_points) < 2:
            QMessageBox.warning(self, "Incomplete", "Need baseline and at least one weight point.")
            return

        try:
            # Pass all calibration points to Cal_Math for processing
            self.cal_data.set_sensor_calibration(self.current_sensor, self.calibration_points)

            # Get the calculated parameters to display to user
            params = self.cal_data.get_calibration_params(self.current_sensor)
            if params:
                slope, intercept = params.get('slope', 0), params.get('intercept', 0)
                self.status_log.append(
                    f"Sensor {self.current_sensor + 1} calibrated: "
                    f"slope={slope:.4f}, intercept={intercept:.2f} "
                    f"with {len(self.calibration_points)} points.")
            else:
                self.status_log.append(
                    f"Sensor {self.current_sensor + 1} calibrated with {len(self.calibration_points)} points.")

            # Move to next sensor
            self._next_sensor()

        except Exception as e:
            QMessageBox.warning(self, "Calibration Error", f"Error during calibration: {str(e)}")
            print(f"Error in finish_sensor: {e}")

    def _next_sensor(self):
        """Move to the next sensor"""
        # Reset state for next sensor
        self.current_sensor += 1
        self.sample_buffer = []
        self.calibration_points = []
        self.baseline_collected = False
        self.weight_input.clear()
        self.measure_button.setVisible(False)
        self.finish_sensor_button.setVisible(False)
        self.zero_button.setEnabled(True)

        # Reset collection flags
        self.collecting_baseline = False
        self.collecting_weight = False

        print(f"Moving to sensor {self.current_sensor + 1}")  # Display 1-based for human readability

        # Check if we're done with all sensors - we only have 4 sensors (indices 0-3)
        if self.current_sensor < self.total_sensors:
            self._enter_sensor_step()
        else:
            # Calibration complete - stop data flow with retry capability
            if hasattr(self.bt_manager, 'send_stop_command'):
                self.bt_manager.send_stop_command()
            else:
                self.bt_manager.send_command("STOP")

            self.status_log.append("Calibration complete. Data streaming stopped.")

            # Update UI for completion
            self.instructions.setText("All done! Click 'Save Calibration Profile' to save.")
            self.start_button.setVisible(False)
            self.skip_button.setVisible(False)
            self.zero_button.setVisible(False)
            self.measure_button.setVisible(False)
            self.finish_sensor_button.setVisible(False)
            self.save_button.setVisible(True)

    def _enter_sensor_step(self):
        """Set up UI for the current sensor"""
        # Display sensor number (1-based) for human readability
        self.instructions.setText(f"--- Sensor {self.current_sensor + 1} ---")
        self.start_button.setVisible(False)
        self.skip_button.setVisible(True)
        self.zero_button.setVisible(True)
        self.live_reading_label.setVisible(True)

        print(f"Entered calibration step for sensor {self.current_sensor + 1}")  # 1-based for human readability

    def save_calibration(self):
        """Save calibration to file"""
        # Use app data directory if available through main_window
        if hasattr(self.main_window, 'calibrations_dir'):
            default_dir = self.main_window.calibrations_dir
            # Use a default filename based on date
            import datetime
            default_filename = os.path.join(
                default_dir,
                f"calibration_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.cal"
            )
        else:
            default_dir = ""
            default_filename = ""

        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Calibration", default_filename, "Calibration (*.cal)"
        )

        if fname:
            try:
                self.cal_data.save_to_file(fname)
                self.status_log.append(f"Saved: {fname}")

                # Also update the main window's current calibration
                if hasattr(self.main_window, 'current_calibration'):
                    # Make sure the main window's reference is the same object
                    self.main_window.current_calibration = self.cal_data
                    self.main_window.calibration_updated.emit()

                    # Log the filename for debugging
                    print(f"Calibration saved with filename: {self.cal_data.filename}")
                    self.status_log.append("Calibration applied to application.")

            except Exception as e:
                self.status_log.append(f"Error saving: {str(e)}")

    def load_calibration(self):
        """Load calibration from file"""
        # Use app data directory if available through main_window
        if hasattr(self.main_window, 'calibrations_dir'):
            default_dir = self.main_window.calibrations_dir
        else:
            default_dir = ""

        fname, _ = QFileDialog.getOpenFileName(
            self, "Load Calibration", default_dir, "Calibration (*.cal)"
        )

        if fname:
            try:
                self.cal_data.load_from_file(fname)
                QMessageBox.information(self, "Loaded", f"Loaded calibration from: {fname}")

                # Update the main window's current calibration
                if hasattr(self.main_window, 'current_calibration'):
                    # Make sure the main window's reference is the same object
                    self.main_window.current_calibration = self.cal_data

                    # Log the filename for debugging
                    print(f"Calibration loaded with filename: {self.cal_data.filename}")

                    # Emit the calibration_updated signal if it exists
                    if hasattr(self.main_window, 'calibration_updated'):
                        self.main_window.calibration_updated.emit()

                    # Force update all components that need calibration
                    if hasattr(self.main_window, 'weight_distribution'):
                        self.main_window.weight_distribution.calibration = self.cal_data
                        print("Updated weight_distribution calibration")

                    # Directly update users_tab profile_edit_view
                    if hasattr(self.main_window, 'users_tab'):
                        if hasattr(self.main_window.users_tab, 'profile_edit_view'):
                            self.main_window.users_tab.profile_edit_view.calibration_data = self.cal_data
                            print(f"Updated profile_edit_view calibration: {self.cal_data.filename}")

                    QMessageBox.information(self, "Loaded", f"Loaded calibration from: {fname}")

            except Exception as e:
                QMessageBox.warning(self, "Failed", f"Failed to load: {e}")
