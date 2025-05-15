from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QGridLayout, QGroupBox, QFormLayout, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
import json
import os


class GeneralSettingsTab(QWidget):
    # Signal to notify that settings have changed
    geometry_changed = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.is_active = False

        # Default settings
        self.settings = {
            # Sensor positions (x, y) - relative to center point
            "sensor_positions": [
                (19.0, 0.0),  # Sensor 1
                (-19.0, 0.0),  # Sensor 2
                (-19.0, 26.5),  # Sensor 3
                (19.0, 26.5)  # Sensor 4
            ],
            # Ideal center of mass position (x, y)
            "ideal_com": (0.0, 13.25),
            # Weight tray 1 settings
            "weight_tray1": {
                "rows": 7,
                "columns": 8,
                "y_position": 24.5,
                "cell_width": 3.5,    # New: Width of each cell in cm
                "cell_height": 2.2,   # New: Height of each cell in cm
                "wall_thickness": 0.3  # New: Thickness of walls in cm
            },
            # Weight tray 2 settings
            "weight_tray2": {
                "rows": 6,
                "columns": 8,
                "y_position": 2.0,
                "cell_width": 3.5,    # New: Width of each cell in cm
                "cell_height": 2.2,   # New: Height of each cell in cm
                "wall_thickness": 0.3  # New: Thickness of walls in cm
            }
        }

        # Set up UI
        self.setup_ui()

        # Load settings if file exists
        self.load_settings()

        print("General Settings tab initialized")

    def setup_ui(self):
        """Create the settings interface"""
        # Create a scroll area for the entire tab
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        # Create a container widget for all content
        container = QWidget()
        main_layout = QVBoxLayout(container)

        # Set scroll area widget
        scroll_area.setWidget(container)

        # Main layout to hold the scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(scroll_area)

        # ===== Sensor Positions =====
        sensor_group = QGroupBox("Sensor Positions")
        sensor_layout = QGridLayout()

        # Create sensor position inputs
        self.sensor_inputs = []

        # Header labels
        sensor_layout.addWidget(QLabel("Sensor"), 0, 0)
        sensor_layout.addWidget(QLabel("X Position (cm)"), 0, 1)
        sensor_layout.addWidget(QLabel("Y Position (cm)"), 0, 2)

        # Sensor position inputs
        for i in range(4):
            # Sensor label
            sensor_layout.addWidget(QLabel(f"Sensor {i + 1}"), i + 1, 0)

            # X position
            x_pos = QDoubleSpinBox()
            x_pos.setRange(-100, 100)
            x_pos.setSingleStep(0.1)
            x_pos.setDecimals(1)
            x_pos.setValue(self.settings["sensor_positions"][i][0])
            x_pos.valueChanged.connect(self.settings_modified)

            # Y position
            y_pos = QDoubleSpinBox()
            y_pos.setRange(-100, 100)
            y_pos.setSingleStep(0.1)
            y_pos.setDecimals(1)
            y_pos.setValue(self.settings["sensor_positions"][i][1])
            y_pos.valueChanged.connect(self.settings_modified)

            sensor_layout.addWidget(x_pos, i + 1, 1)
            sensor_layout.addWidget(y_pos, i + 1, 2)

            # Store references to these widgets for later
            self.sensor_inputs.append((x_pos, y_pos))

        sensor_group.setLayout(sensor_layout)
        main_layout.addWidget(sensor_group)

        # ===== Ideal Center of Mass =====
        com_group = QGroupBox("Ideal Center of Mass")
        com_layout = QFormLayout()

        # X position
        self.ideal_com_x = QDoubleSpinBox()
        self.ideal_com_x.setRange(-100, 100)
        self.ideal_com_x.setSingleStep(0.1)
        self.ideal_com_x.setDecimals(1)
        self.ideal_com_x.setValue(self.settings["ideal_com"][0])
        self.ideal_com_x.valueChanged.connect(self.settings_modified)

        # Y position
        self.ideal_com_y = QDoubleSpinBox()
        self.ideal_com_y.setRange(-100, 100)
        self.ideal_com_y.setSingleStep(0.1)
        self.ideal_com_y.setDecimals(1)
        self.ideal_com_y.setValue(self.settings["ideal_com"][1])
        self.ideal_com_y.valueChanged.connect(self.settings_modified)

        com_layout.addRow("X Position (cm):", self.ideal_com_x)
        com_layout.addRow("Y Position (cm):", self.ideal_com_y)

        com_group.setLayout(com_layout)
        main_layout.addWidget(com_group)

        # ===== Weight Trays =====
        weight_trays_layout = QHBoxLayout()

        # ----- Weight Tray 1 -----
        tray1_group = QGroupBox("Weight Tray 1")
        tray1_layout = QFormLayout()

        # Rows
        self.tray1_rows = QSpinBox()
        self.tray1_rows.setRange(1, 10)
        self.tray1_rows.setValue(self.settings["weight_tray1"]["rows"])
        self.tray1_rows.valueChanged.connect(self.settings_modified)

        # Columns
        self.tray1_cols = QSpinBox()
        self.tray1_cols.setRange(1, 10)
        self.tray1_cols.setValue(self.settings["weight_tray1"]["columns"])
        self.tray1_cols.valueChanged.connect(self.settings_modified)

        # Y Position
        self.tray1_y_pos = QDoubleSpinBox()
        self.tray1_y_pos.setRange(-100, 100)
        self.tray1_y_pos.setSingleStep(0.1)
        self.tray1_y_pos.setDecimals(1)
        self.tray1_y_pos.setValue(self.settings["weight_tray1"]["y_position"])
        self.tray1_y_pos.valueChanged.connect(self.settings_modified)

        # Cell Width (New)
        self.tray1_cell_width = QDoubleSpinBox()
        self.tray1_cell_width.setRange(0.1, 10)
        self.tray1_cell_width.setSingleStep(0.1)
        self.tray1_cell_width.setDecimals(1)
        self.tray1_cell_width.setValue(self.settings["weight_tray1"]["cell_width"])
        self.tray1_cell_width.valueChanged.connect(self.settings_modified)

        # Cell Height (New)
        self.tray1_cell_height = QDoubleSpinBox()
        self.tray1_cell_height.setRange(0.1, 10)
        self.tray1_cell_height.setSingleStep(0.1)
        self.tray1_cell_height.setDecimals(1)
        self.tray1_cell_height.setValue(self.settings["weight_tray1"]["cell_height"])
        self.tray1_cell_height.valueChanged.connect(self.settings_modified)

        # Wall Thickness (New)
        self.tray1_wall_thickness = QDoubleSpinBox()
        self.tray1_wall_thickness.setRange(0.1, 3)
        self.tray1_wall_thickness.setSingleStep(0.1)
        self.tray1_wall_thickness.setDecimals(1)
        self.tray1_wall_thickness.setValue(self.settings["weight_tray1"]["wall_thickness"])
        self.tray1_wall_thickness.valueChanged.connect(self.settings_modified)

        tray1_layout.addRow("Rows:", self.tray1_rows)
        tray1_layout.addRow("Columns:", self.tray1_cols)
        tray1_layout.addRow("Y Position (cm):", self.tray1_y_pos)
        tray1_layout.addRow("Cell Width (cm):", self.tray1_cell_width)  # New
        tray1_layout.addRow("Cell Height (cm):", self.tray1_cell_height)  # New
        tray1_layout.addRow("Wall Thickness (cm):", self.tray1_wall_thickness)  # New

        tray1_group.setLayout(tray1_layout)
        weight_trays_layout.addWidget(tray1_group)

        # ----- Weight Tray 2 -----
        tray2_group = QGroupBox("Weight Tray 2")
        tray2_layout = QFormLayout()

        # Rows
        self.tray2_rows = QSpinBox()
        self.tray2_rows.setRange(1, 10)
        self.tray2_rows.setValue(self.settings["weight_tray2"]["rows"])
        self.tray2_rows.valueChanged.connect(self.settings_modified)

        # Columns
        self.tray2_cols = QSpinBox()
        self.tray2_cols.setRange(1, 10)
        self.tray2_cols.setValue(self.settings["weight_tray2"]["columns"])
        self.tray2_cols.valueChanged.connect(self.settings_modified)

        # Y Position
        self.tray2_y_pos = QDoubleSpinBox()
        self.tray2_y_pos.setRange(-100, 100)
        self.tray2_y_pos.setSingleStep(0.1)
        self.tray2_y_pos.setDecimals(1)
        self.tray2_y_pos.setValue(self.settings["weight_tray2"]["y_position"])
        self.tray2_y_pos.valueChanged.connect(self.settings_modified)

        # Cell Width (New)
        self.tray2_cell_width = QDoubleSpinBox()
        self.tray2_cell_width.setRange(0.1, 10)
        self.tray2_cell_width.setSingleStep(0.1)
        self.tray2_cell_width.setDecimals(1)
        self.tray2_cell_width.setValue(self.settings["weight_tray2"]["cell_width"])
        self.tray2_cell_width.valueChanged.connect(self.settings_modified)

        # Cell Height (New)
        self.tray2_cell_height = QDoubleSpinBox()
        self.tray2_cell_height.setRange(0.1, 10)
        self.tray2_cell_height.setSingleStep(0.1)
        self.tray2_cell_height.setDecimals(1)
        self.tray2_cell_height.setValue(self.settings["weight_tray2"]["cell_height"])
        self.tray2_cell_height.valueChanged.connect(self.settings_modified)

        # Wall Thickness (New)
        self.tray2_wall_thickness = QDoubleSpinBox()
        self.tray2_wall_thickness.setRange(0.1, 3)
        self.tray2_wall_thickness.setSingleStep(0.1)
        self.tray2_wall_thickness.setDecimals(1)
        self.tray2_wall_thickness.setValue(self.settings["weight_tray2"]["wall_thickness"])
        self.tray2_wall_thickness.valueChanged.connect(self.settings_modified)

        tray2_layout.addRow("Rows:", self.tray2_rows)
        tray2_layout.addRow("Columns:", self.tray2_cols)
        tray2_layout.addRow("Y Position (cm):", self.tray2_y_pos)
        tray2_layout.addRow("Cell Width (cm):", self.tray2_cell_width)  # New
        tray2_layout.addRow("Cell Height (cm):", self.tray2_cell_height)  # New
        tray2_layout.addRow("Wall Thickness (cm):", self.tray2_wall_thickness)  # New

        tray2_group.setLayout(tray2_layout)
        weight_trays_layout.addWidget(tray2_group)

        main_layout.addLayout(weight_trays_layout)

        # ----- Buttons -----
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)

        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_button)

        main_layout.addLayout(button_layout)

        # Add some space at the bottom
        main_layout.addStretch()

    def showEvent(self, event):
        """Called when the tab is shown"""
        super().showEvent(event)
        print("DEBUG [LiveFeed] showEvent called - tab is now visible")

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

    def update_settings_from_ui(self):
        """Update the settings dictionary with values from UI controls"""
        # Update sensor positions
        for i in range(4):
            x_pos, y_pos = self.sensor_inputs[i]
            self.settings["sensor_positions"][i] = (x_pos.value(), y_pos.value())

        # Update ideal center of mass
        self.settings["ideal_com"] = (self.ideal_com_x.value(), self.ideal_com_y.value())

        # Update weight tray 1
        self.settings["weight_tray1"]["rows"] = self.tray1_rows.value()
        self.settings["weight_tray1"]["columns"] = self.tray1_cols.value()
        self.settings["weight_tray1"]["y_position"] = self.tray1_y_pos.value()
        # Update new settings
        self.settings["weight_tray1"]["cell_width"] = self.tray1_cell_width.value()
        self.settings["weight_tray1"]["cell_height"] = self.tray1_cell_height.value()
        self.settings["weight_tray1"]["wall_thickness"] = self.tray1_wall_thickness.value()

        # Update weight tray 2
        self.settings["weight_tray2"]["rows"] = self.tray2_rows.value()
        self.settings["weight_tray2"]["columns"] = self.tray2_cols.value()
        self.settings["weight_tray2"]["y_position"] = self.tray2_y_pos.value()
        # Update new settings
        self.settings["weight_tray2"]["cell_width"] = self.tray2_cell_width.value()
        self.settings["weight_tray2"]["cell_height"] = self.tray2_cell_height.value()
        self.settings["weight_tray2"]["wall_thickness"] = self.tray2_wall_thickness.value()

    def update_ui_from_settings(self):
        """Update UI controls from the settings dictionary"""
        # Update sensor positions
        for i in range(4):
            x_pos, y_pos = self.sensor_inputs[i]
            x_pos.setValue(self.settings["sensor_positions"][i][0])
            y_pos.setValue(self.settings["sensor_positions"][i][1])

        # Update ideal center of mass
        self.ideal_com_x.setValue(self.settings["ideal_com"][0])
        self.ideal_com_y.setValue(self.settings["ideal_com"][1])

        # Update weight tray 1
        self.tray1_rows.setValue(self.settings["weight_tray1"]["rows"])
        self.tray1_cols.setValue(self.settings["weight_tray1"]["columns"])
        self.tray1_y_pos.setValue(self.settings["weight_tray1"]["y_position"])
        # Update new fields
        self.tray1_cell_width.setValue(self.settings["weight_tray1"]["cell_width"])
        self.tray1_cell_height.setValue(self.settings["weight_tray1"]["cell_height"])
        self.tray1_wall_thickness.setValue(self.settings["weight_tray1"]["wall_thickness"])

        # Update weight tray 2
        self.tray2_rows.setValue(self.settings["weight_tray2"]["rows"])
        self.tray2_cols.setValue(self.settings["weight_tray2"]["columns"])
        self.tray2_y_pos.setValue(self.settings["weight_tray2"]["y_position"])
        # Update new fields
        self.tray2_cell_width.setValue(self.settings["weight_tray2"]["cell_width"])
        self.tray2_cell_height.setValue(self.settings["weight_tray2"]["cell_height"])
        self.tray2_wall_thickness.setValue(self.settings["weight_tray2"]["wall_thickness"])

    def save_settings(self):
        """Save settings to file"""
        try:
            # Ensure we have the latest values
            self.update_settings_from_ui()

            # Save to file
            with open('general_settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)

            print("Settings saved to general_settings.json")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Load settings from file if it exists"""
        try:
            if os.path.exists('general_settings.json'):
                with open('general_settings.json', 'r') as f:
                    loaded_settings = json.load(f)

                    # Update our settings with loaded values
                    self.settings.update(loaded_settings)

                    # Refresh UI to reflect loaded settings
                    if hasattr(self, 'sensor_inputs'):  # Check if UI is already set up
                        self.update_ui_from_settings()

                print("Settings loaded from general_settings.json")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def reset_to_default(self):
        """Reset all settings to default values"""
        # Reset to default values
        self.settings = {
            "sensor_positions": [
                (19.0, 0.0),  # Sensor 1
                (-19.0, 0.0),  # Sensor 2
                (-19.0, 26.5),  # Sensor 3
                (19.0, 26.5)  # Sensor 4
            ],
            "ideal_com": (0.0, 13.25),
            # Weight tray 1 settings
            "weight_tray1": {
                "rows": 7,
                "columns": 8,
                "y_position": 24.5,
                "cell_width": 3.5,    # New: Width of each cell in cm
                "cell_height": 2.2,   # New: Height of each cell in cm
                "wall_thickness": 0.3  # New: Thickness of walls in cm
            },
            # Weight tray 2 settings
            "weight_tray2": {
                "rows": 6,
                "columns": 8,
                "y_position": 2.0,
                "cell_width": 3.5,    # New: Width of each cell in cm
                "cell_height": 2.2,   # New: Height of each cell in cm
                "wall_thickness": 0.3  # New: Thickness of walls in cm
            }
        }

        # Update UI
        self.update_ui_from_settings()

        # Notify that settings have changed
        self.settings_changed.emit()

        print("Settings reset to default values")

    def get_settings(self):
        """Return the current settings dictionary - for use by other tabs"""
        # Ensure dictionary is up-to-date
        self.update_settings_from_ui()
        return self.settings

    def showEvent(self, event):
        """Called when the General Settings tab becomes visible"""
        super().showEvent(event)
        self.is_active = True
        print("General Settings tab is now visible")

    def hideEvent(self, event):
        """Called when the General Settings tab is hidden"""
        super().hideEvent(event)
        self.is_active = False
        print("General Settings tab is now hidden")

    def settings_modified(self):
        """Called when any setting is changed"""
        # Update the settings dictionary with current values
        print("DEBUG [GeneralSettings] settings_modified called")
        self.update_settings_from_ui()

        # Emit signal that settings changed
        print("DEBUG [GeneralSettings] Emitting settings_changed signal")
        self.settings_changed.emit()
        self.geometry_changed.emit()

        print("[GeneralSettings] Settings modified")
        print("[GeneralSettings] Geometry changed signal emitted")