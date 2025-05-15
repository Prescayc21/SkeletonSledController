import os
import json
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QFrame, QStackedWidget
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
import numpy as np
from tabs.profile_edit_view import ProfileEditView  # Import the new module


class UsersTab(QWidget):
    """
    Tab for managing athlete profiles, including creation, loading, editing, and deletion.
    """

    # Signal when a profile is selected
    profile_selected = pyqtSignal(str)

    def __init__(self, bt_manager=None, current_calibration=None, weight_distribution=None, main_window=None):
        super().__init__()
        self.bt_manager = bt_manager
        self.calibration_data = current_calibration  # Optional CalibrationData instance
        self.weight_distribution = weight_distribution  # Add weight_distribution reference
        self.main_window = main_window  # Store reference to main window

        # Use the profiles directory from main window if available
        if main_window and hasattr(main_window, 'profiles_dir'):
            self.profiles_dir = main_window.profiles_dir
        else:
            # Create profiles directory if it doesn't exist
            self.profiles_dir = os.path.join(os.getcwd(), "profiles")

        os.makedirs(self.profiles_dir, exist_ok=True)

        # Data collection state
        self._collecting = False
        self._raw_buffer = []
        self.sensor_averages = None

        # Current profile
        self.current_profile = None
        self.current_profile_name = None

        # Constants
        self._REQUIRED_SAMPLES = 20
        self._MAX_BUFFER_SIZE = 100
        self._TIMEOUT_MS = 10000  # 10 seconds

        # Timeout timer
        self._collection_timer = QTimer()
        self._collection_timer.setSingleShot(True)
        self._collection_timer.timeout.connect(self._handle_collection_timeout)

        # Set up the UI
        self._setup_ui()

        # Connect to BluetoothManager
        if self.bt_manager:
            self.bt_manager.data_signal.connect(self.handle_data)

        # Refresh profile list on startup
        self.refresh_profile_list()

    def _setup_ui(self):
        """Set up the main user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)

        # Create stacked widget for multiple views
        self.stacked_widget = QStackedWidget()

        # Create profile list view
        self.profile_list_view = QWidget()
        self._setup_profile_list_view()

        # Create profile edit view
        self.profile_edit_view = ProfileEditView(
            self.calibration_data,
            self.bt_manager,
            self.weight_distribution
        )

        # Try to get general settings from main window
        self.general_settings = None
        if hasattr(self, 'main_window') and self.main_window:
            if hasattr(self.main_window, 'general_settings_tab'):
                self.general_settings = self.main_window.general_settings_tab
                # Pass to profile_edit_view
                self.profile_edit_view.general_settings_tab = self.general_settings

        if self.main_window and hasattr(self.main_window, 'general_settings_tab'):
            # Create a method that profile_edit_view can use to get fresh settings
            def get_latest_settings():
                if self.main_window and hasattr(self.main_window, 'general_settings_tab'):
                    return self.main_window.general_settings_tab.get_settings()
                return None

            # Pass this method to the profile_edit_view
            self.profile_edit_view.get_main_window_settings = get_latest_settings

        if self.main_window and hasattr(self.main_window, 'calibration_updated'):
            # Connect the calibration_updated signal to refresh the calibration
            self.main_window.calibration_updated.connect(self._refresh_calibration)

        # Add this line to pass the timeout handler
        self.profile_edit_view.timeout_handler = self._handle_collection_timeout

        # Connect profile edit view signals
        self.profile_edit_view.back_pressed.connect(self.return_to_profile_list)
        self.profile_edit_view.save_profile.connect(self.save_current_profile)

        # Connect weight distribution signals if available
        if self.weight_distribution:
            self.weight_distribution.layout_generated.connect(self.profile_edit_view.on_layout_generated)

        # Add both views to the stacked widget
        self.stacked_widget.addWidget(self.profile_list_view)
        self.stacked_widget.addWidget(self.profile_edit_view)

        # Add stacked widget to main layout
        main_layout.addWidget(self.stacked_widget)

        # Start with profile list view
        self.stacked_widget.setCurrentWidget(self.profile_list_view)

    def _refresh_calibration(self):
        """Update calibration reference when it changes in main window"""
        if hasattr(self, 'profile_edit_view') and self.main_window:
            if hasattr(self.main_window, 'current_calibration'):
                self.profile_edit_view.calibration_data = self.main_window.current_calibration
                print(
                    f"Updated profile_edit_view calibration to: {getattr(self.main_window.current_calibration, 'filename', None)}")

    def _setup_profile_list_view(self):
        """Set up the profile list view"""
        layout = QVBoxLayout(self.profile_list_view)

        # Create button area
        button_frame = QFrame()
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_layout = QHBoxLayout(button_frame)

        # Create buttons
        self.create_button = QPushButton("Create New Profile")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")

        # Initially disable edit and delete buttons
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        # Add buttons to layout
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)

        # Connect button signals
        self.create_button.clicked.connect(self.create_new_profile)
        self.edit_button.clicked.connect(self.edit_selected_profile)
        self.delete_button.clicked.connect(self.delete_selected_profile)

        # Add button frame to main layout
        layout.addWidget(button_frame)

        # Create scroll area for profiles
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Create container widget for the scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Create list widget for profiles
        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self.on_profile_selected)

        # Add list widget to scroll layout
        scroll_layout.addWidget(self.profile_list)

        # Set the scroll content widget
        scroll.setWidget(scroll_content)

        # Add scroll area to main layout
        layout.addWidget(scroll)

    def showEvent(self, event):
        """Called when the users tab becomes visible"""
        super().showEvent(event)
        if self.bt_manager:
            self.bt_manager.set_active_tab("users")
            print("Users tab is now visible")

        # Refresh profile list when tab becomes visible
        self.refresh_profile_list()

    def refresh_profile_list(self):
        """Update the profile list with all available profiles"""
        # Clear current items
        self.profile_list.clear()

        # Get profiles
        profiles = self.list_profiles()

        # Add profiles to list
        for profile_info in profiles:
            # Create item with profile name and creation date
            display_text = f"{profile_info['name']} - Created: {profile_info['created']}"
            item = QListWidgetItem(display_text)

            # Store filename as item data
            item.setData(Qt.UserRole, profile_info['filename'])

            # Add to list
            self.profile_list.addItem(item)

        # Disable edit/delete buttons as no profile is selected
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def on_profile_selected(self, item):
        """Handle when a profile is selected in the list"""
        if item:
            # Enable edit and delete buttons
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)

            # Store selected profile filename
            self.current_profile_name = item.data(Qt.UserRole)
            print(f"Selected profile: {self.current_profile_name}")

    def create_new_profile(self):
        """Create a new empty profile"""
        # Generate a unique name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Athlete_{timestamp}"

        # Create a new profile with default values
        new_profile = {
            "version": "1.0",
            "name": default_name,
            "created": datetime.datetime.now().isoformat(),
            "sensor_data": [0.0, 0.0, 0.0, 0.0],
            "displacement": [0.0, 0.0],
            "bias": {
                "x": 0.0,
                "y": 0.0,  # Will be calculated properly when sensors are set
                "max_weight": 350.0,  # lbs
                "threshold_enabled": False,
                "threshold_percent": 2.5
            },
            "trays_enabled": {
                "front": True,
                "back": True
            },
            "layout": {
                "front_tray": [],
                "back_tray": [],
                "effect_map": {
                    "front": [],
                    "back": []
                }
            }
        }

        # Save the profile
        success, filename = self.save_profile(new_profile)

        if success:
            # Show success message
            QMessageBox.information(
                self,
                "Profile Created",
                f"Created new profile: {default_name}",
                QMessageBox.Ok
            )

            # Refresh profile list
            self.refresh_profile_list()

            # Load and edit the new profile
            self.current_profile_name = filename
            self.current_profile = new_profile
            self.edit_selected_profile()
        else:
            # Show error message
            QMessageBox.critical(
                self,
                "Create Error",
                "Failed to create new profile.",
                QMessageBox.Ok
            )

    def edit_selected_profile(self):
        """Open the selected profile for editing"""
        if not self.current_profile_name:
            return

        # Load the profile if not already loaded
        if not self.current_profile:
            self.current_profile = self.load_profile(self.current_profile_name)

        if self.current_profile:
            # Pass profile to edit view
            self.profile_edit_view.set_profile(self.current_profile)

            # Switch to profile edit view
            self.stacked_widget.setCurrentWidget(self.profile_edit_view)
        else:
            # Show error message
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load profile: {self.current_profile_name}",
                QMessageBox.Ok
            )

    def return_to_profile_list(self):
        """Return to the profile list view"""
        # Switch to profile list view
        self.stacked_widget.setCurrentWidget(self.profile_list_view)

        # Clear current profile
        self.current_profile = None

        # Refresh the list
        self.refresh_profile_list()

    def save_current_profile(self, profile):
        """Save the currently edited profile"""
        if not profile:
            return

        # Update the current profile
        self.current_profile = profile

        # Save to disk
        success, filename = self.save_profile(profile, overwrite=True)

        if success:
            print(f"Profile saved: {filename}")
            # Update current profile name if this is a new profile
            if not self.current_profile_name:
                self.current_profile_name = filename
        else:
            QMessageBox.critical(
                self,
                "Save Error",
                "Failed to save profile.",
                QMessageBox.Ok
            )

    def delete_selected_profile(self):
        """Delete the selected profile"""
        if not self.current_profile_name:
            return

        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this profile?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Delete the profile
            success = self.delete_profile(self.current_profile_name)

            if success:
                # Show success message
                QMessageBox.information(
                    self,
                    "Profile Deleted",
                    "Profile has been deleted.",
                    QMessageBox.Ok
                )

                # Clear current profile
                self.current_profile_name = None
                self.current_profile = None

                # Refresh profile list
                self.refresh_profile_list()
            else:
                # Show error message
                QMessageBox.critical(
                    self,
                    "Delete Error",
                    "Failed to delete profile.",
                    QMessageBox.Ok
                )

    #
    # Profile Management Functions
    #

    def save_profile(self, profile_dict, overwrite=False):
        """
        Save profile to disk. Supports partial saves by filling in defaults.

        Args:
            profile_dict: Dictionary containing profile data
            overwrite: If True, overwrites existing profile; otherwise generates new filename

        Returns:
            tuple: (success, filename) - Boolean success flag and filename used
        """
        try:
            # Ensure profile has required basic fields
            if 'name' not in profile_dict:
                profile_dict['name'] = f"Athlete_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if 'created' not in profile_dict:
                profile_dict['created'] = datetime.datetime.now().isoformat()

            if 'version' not in profile_dict:
                profile_dict['version'] = "1.0"

            # Generate filename based on profile name and timestamp if not overwriting
            if overwrite and self.current_profile_name:
                filename = self.current_profile_name
            else:
                # Sanitize name for filename
                safe_name = "".join(c if c.isalnum() else "_" for c in profile_dict['name'])
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{safe_name}_{timestamp}.json"

            # Construct full path
            filepath = os.path.join(self.profiles_dir, filename)

            # Fill in defaults for missing keys
            complete_profile = self._fill_profile_defaults(profile_dict)

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(complete_profile, f, indent=2)

            print(f"Saved profile to {filepath}")
            return True, filename

        except Exception as e:
            print(f"Error saving profile: {str(e)}")
            return False, None

    def load_profile(self, filename):
        """
        Load a profile from disk

        Args:
            filename: Filename of the profile to load

        Returns:
            dict: Profile data dictionary, or None if loading failed
        """
        try:
            # Construct full path
            filepath = os.path.join(self.profiles_dir, filename)

            # Check if file exists
            if not os.path.exists(filepath):
                print(f"Profile not found: {filepath}")
                return None

            # Load from file
            with open(filepath, 'r') as f:
                profile = json.load(f)

            # Validate profile
            valid, warnings = self.validate_profile(profile)

            # Log warnings but still return the profile
            for warning in warnings:
                print(f"WARNING: {warning}")

            print(f"Loaded profile from {filepath}")
            return profile

        except Exception as e:
            print(f"Error loading profile: {str(e)}")
            return None

    def list_profiles(self):
        """
        List all available profiles

        Returns:
            list: List of dictionaries with profile info
        """
        profiles = []

        try:
            # Get all JSON files in profiles directory
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith('.json'):
                    try:
                        # Load minimal info from each profile
                        filepath = os.path.join(self.profiles_dir, filename)
                        with open(filepath, 'r') as f:
                            profile = json.load(f)

                        # Extract key information
                        profile_info = {
                            'filename': filename,
                            'name': profile.get('name', 'Unnamed'),
                            'created': profile.get('created', 'Unknown')
                        }

                        profiles.append(profile_info)
                    except Exception as e:
                        print(f"Error reading profile {filename}: {str(e)}")

        except Exception as e:
            print(f"Error listing profiles: {str(e)}")

        # Sort profiles by creation date (newest first)
        profiles.sort(key=lambda x: x['created'], reverse=True)

        return profiles

    def delete_profile(self, filename):
        """
        Delete a profile from disk

        Args:
            filename: Filename of the profile to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            # Construct full path
            filepath = os.path.join(self.profiles_dir, filename)

            # Check if file exists
            if not os.path.exists(filepath):
                print(f"Profile not found: {filepath}")
                return False

            # Delete the file
            os.remove(filepath)
            print(f"Deleted profile: {filepath}")
            return True

        except Exception as e:
            print(f"Error deleting profile: {str(e)}")
            return False

    def validate_profile(self, profile_dict):
        """
        Validate profile data and log warnings for missing fields

        Args:
            profile_dict: Dictionary containing profile data

        Returns:
            tuple: (valid, warnings) - Boolean validity flag and list of warning messages
        """
        valid = True
        warnings = []

        # Check required fields
        if 'name' not in profile_dict:
            warnings.append("Profile is missing 'name' field")

        if 'created' not in profile_dict:
            warnings.append("Profile is missing 'created' field")

        if 'version' not in profile_dict:
            warnings.append("Profile is missing 'version' field")

        # Check for sensor data
        if 'sensor_data' not in profile_dict:
            warnings.append("Profile is missing 'sensor_data'")
        elif not isinstance(profile_dict['sensor_data'], list) or len(profile_dict['sensor_data']) != 4:
            warnings.append("Profile has invalid 'sensor_data', should be a list of 4 values")

        # Check bias settings
        if 'bias' not in profile_dict:
            warnings.append("Profile is missing 'bias' settings")
        else:
            bias = profile_dict['bias']
            if not isinstance(bias, dict):
                warnings.append("Profile has invalid 'bias', should be a dictionary")
            else:
                for key in ['x', 'y', 'max_weight', 'threshold_enabled', 'threshold_percent']:
                    if key not in bias:
                        warnings.append(f"Profile 'bias' is missing '{key}' setting")

        # Check tray settings
        if 'trays_enabled' not in profile_dict:
            warnings.append("Profile is missing 'trays_enabled' settings")

        # Check layout
        if 'layout' not in profile_dict:
            warnings.append("Profile is missing 'layout' information")

        return valid, warnings

    def _fill_profile_defaults(self, profile_dict):
        """
        Fill in default values for missing fields in a profile

        Args:
            profile_dict: Dictionary containing profile data

        Returns:
            dict: Complete profile dictionary with defaults for missing fields
        """
        # Create a copy to avoid modifying the input
        result = profile_dict.copy()

        # Add version if missing
        if 'version' not in result:
            result['version'] = "1.0"

        # Add name if missing
        if 'name' not in result:
            result['name'] = f"Athlete_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Add creation timestamp if missing
        if 'created' not in result:
            result['created'] = datetime.datetime.now().isoformat()

        # Add sensor data if missing
        if 'sensor_data' not in result:
            result['sensor_data'] = [0.0, 0.0, 0.0, 0.0]

        # Add displacement if missing
        if 'displacement' not in result:
            result['displacement'] = [0.0, 0.0]

        # Add bias settings if missing
        if 'bias' not in result:
            # Calculate default Y bias (halfway up the sled)
            # Try to get sensor 3 or 4 Y value for the calculation
            y_bias = 0.0
            if hasattr(self, 'settings') and 'sensor_positions' in self.settings:
                sensor_positions = self.settings['sensor_positions']
                if len(sensor_positions) >= 4:
                    # Use sensor 3 (index 2) or 4 (index 3) Y value / 2
                    y_bias = sensor_positions[2][1] / 2

            result['bias'] = {
                "x": 0.0,
                "y": y_bias,
                "max_weight": 350.0,  # lbs
                "threshold_enabled": False,
                "threshold_percent": 2.5
            }
        else:
            # Ensure all bias fields exist
            bias = result['bias']
            if 'x' not in bias:
                bias['x'] = 0.0

            if 'y' not in bias:
                # Calculate default Y bias (halfway up the sled)
                y_bias = 0.0
                if hasattr(self, 'settings') and 'sensor_positions' in self.settings:
                    sensor_positions = self.settings['sensor_positions']
                    if len(sensor_positions) >= 4:
                        # Use sensor 3 (index 2) or 4 (index 3) Y value / 2
                        y_bias = sensor_positions[2][1] / 2
                bias['y'] = y_bias

            if 'max_weight' not in bias:
                bias['max_weight'] = 350.0

            if 'threshold_enabled' not in bias:
                bias['threshold_enabled'] = False

            if 'threshold_percent' not in bias:
                bias['threshold_percent'] = 2.5

        # Add trays enabled settings if missing
        if 'trays_enabled' not in result:
            result['trays_enabled'] = {
                "front": True,
                "back": True
            }

        # Add layout if missing
        if 'layout' not in result:
            result['layout'] = {
                "front_tray": [],
                "back_tray": [],
                "effect_map": {
                    "front": [],
                    "back": []
                }
            }

        return result

    #
    # Data Collection Functions (from original implementation)
    #

    def handle_data(self, line):
        """Handle incoming data lines from BluetoothManager"""
        # This method is kept for compatibility with the profile edit view
        # Actual data collection now happens in the ProfileEditView class
        pass

    def _handle_collection_timeout(self):
        """Handle case where valid samples weren't collected in time"""
        if not self._collecting:
            return

        print(f"ERROR: Data collection timed out after {self._TIMEOUT_MS / 1000} seconds")
        print(f"Only collected {len(self._raw_buffer)}/{self._REQUIRED_SAMPLES} samples")

        # Stop collection
        self._collecting = False

        # Stop data streaming
        if self.bt_manager:
            self.bt_manager.send_command("STOP")

        # Hide progress bar
        self.progress_bar.setVisible(False)

        # Re-enable generate button
        self.generate_button.setEnabled(True)

        # Show error message
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(
            self,
            "Collection Timeout",
            f"Failed to collect {self._REQUIRED_SAMPLES} valid samples within {self._TIMEOUT_MS / 1000} seconds.\nOnly collected {len(self._raw_buffer)} samples.\nPlease try again.",
            QMessageBox.Ok
        )