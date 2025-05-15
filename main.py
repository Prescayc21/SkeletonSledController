# main.py
from bluetooth import BluetoothManager
from fake_bluetooth import FakeBluetoothManager  # Import the fake manager
from tabs.live_feed import LiveFeedTab
from tabs.settings import SettingsTab
from tabs.calibration import CalibrationTab
from tabs.users import UsersTab
from tabs.general_settings import GeneralSettingsTab
from Cal_Math import CalibrationData
from Alg_Math import WeightDistribution
import sys
import os
import platform
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtCore import QObject, pyqtSignal, Qt
_SIGNAL_CONNECTIONS = {}


def safe_connect(signal, slot, connection_id):
    """
    Connect a signal to a slot only if the connection doesn't already exist.

    Args:
        signal: The Qt signal to connect
        slot: The slot (method) to connect the signal to
        connection_id: A unique identifier for this connection

    Returns:
        bool: True if a new connection was made, False if already connected
    """
    global _SIGNAL_CONNECTIONS

    # Check if this connection already exists
    if connection_id in _SIGNAL_CONNECTIONS:
        print(f"DEBUG: Skipping duplicate connection {connection_id}")
        return False

    # To be extra safe, try to disconnect first (catch any errors)
    try:
        signal.disconnect(slot)
        print(f"DEBUG: Disconnected existing connection for {connection_id}")
    except (TypeError, RuntimeError):
        # This is expected if there was no existing connection
        pass

    # Make the connection
    signal.connect(slot)

    # Record the connection
    _SIGNAL_CONNECTIONS[connection_id] = True
    print(f"DEBUG: New connection made: {connection_id}")
    return True


def safe_disconnect(signal, slot=None):
    """
    Safely disconnect a signal from all slots or a specific slot.

    Args:
        signal: The Qt signal to disconnect
        slot: Optional specific slot to disconnect

    Returns:
        bool: True if disconnection was successful
    """
    try:
        if slot is None:
            # Disconnect all slots
            signal.disconnect()
        else:
            # Disconnect specific slot
            signal.disconnect(slot)
        return True
    except TypeError:
        # Signal was not connected
        return False
    except Exception as e:
        print(f"ERROR: Failed to disconnect signal: {e}")
        return False


def reset_connections():
    """Reset the connection registry"""
    global _SIGNAL_CONNECTIONS
    _SIGNAL_CONNECTIONS = {}
    print("DEBUG: Connection registry reset")


def get_app_data_dir():
    """
    Get the platform-specific application data directory

    Returns:
        str: Full path to the application data directory
    """
    import sys
    import os

    app_name = "SkeletonSledController"

    if sys.platform == 'darwin':  # macOS
        # ~/Library/Application Support/SkeletonSledController/
        data_dir = os.path.join(
            os.path.expanduser('~'),
            'Library',
            'Application Support',
            app_name
        )
    elif sys.platform == 'win32':  # Windows
        # Use %APPDATA% (typically C:\Users\<username>\AppData\Roaming)
        data_dir = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            app_name
        )
    else:  # Linux and others
        # Use ~/.skeletonsled/
        data_dir = os.path.join(
            os.path.expanduser('~'),
            f'.{app_name.lower()}'
        )

    # Create if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)

    return data_dir


def configure_platform():
    """Configure platform-specific settings"""
    if sys.platform == 'darwin':  # macOS
        # Fix for macOS Retina displays and transparent widgets
        os.environ['QT_MAC_WANTS_LAYER'] = '1'

        # Enable high-DPI support
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    print(f"Running on: {platform.system()} {platform.release()}")

class MainWindow(QMainWindow):
    calibration_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skeleton Sled Controller")
        self.resize(800, 600)

        # Set up application data directory
        self.app_data_dir = get_app_data_dir()
        self.profiles_dir = os.path.join(self.app_data_dir, "profiles")
        self.calibrations_dir = os.path.join(self.app_data_dir, "calibrations")

        # Ensure directories exist
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(self.calibrations_dir, exist_ok=True)

        print(f"Using application data directory: {self.app_data_dir}")
        print(f"Using profiles directory: {self.profiles_dir}")
        print(f"Using calibrations directory: {self.calibrations_dir}")

        # Create the Bluetooth manager (real by default)
        self.bt_manager = BluetoothManager()

        # Store current connection state
        self.connected_port = None
        self.using_fake_manager = False

        # Connect to status signal to track connection changes
        self.bt_manager.status_signal.connect(self.handle_connection_status)

        self.current_calibration = CalibrationData()

        # Create the weight distribution calculator and pass the calibration reference
        self.weight_distribution = WeightDistribution(self.current_calibration)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create the general settings tab first so it can be referenced by other tabs
        self.general_settings_tab = GeneralSettingsTab(self)

        # Create other tabs with their unique identifiers and pass general_settings_tab reference
        # Pass the weight_distribution instance to LiveFeedTab
        self.live_feed_tab = LiveFeedTab(self.bt_manager, self, self.general_settings_tab, self.weight_distribution)
        self.bluetooth_settings_tab = SettingsTab(self.bt_manager)
        self.calibration_tab = CalibrationTab(self.bt_manager, self)
        self.users_tab = UsersTab(self.bt_manager, self.current_calibration, self.weight_distribution, self)

        # Store mapping of tab indices to identifiers
        self.tab_identifiers = {}

        # Add tabs in the order they should appear in the UI
        tab_index = 0

        # Add tabs and track their identifiers
        self.tabs.addTab(self.live_feed_tab, "Live Feed")
        self.tab_identifiers[0] = "live_feed"
        tab_index += 1

        self.tabs.addTab(self.calibration_tab, "Calibration")
        self.tab_identifiers[tab_index] = "calibration"
        tab_index += 1

        self.tabs.addTab(self.users_tab, "Users")
        self.tab_identifiers[tab_index] = "users"
        tab_index += 1

        self.tabs.addTab(self.general_settings_tab, "General Settings")
        self.tab_identifiers[tab_index] = "general_settings"
        tab_index += 1

        self.tabs.addTab(self.bluetooth_settings_tab, "Bluetooth Settings")
        self.tab_identifiers[tab_index] = "bluetooth_settings"
        tab_index += 1

        # Connect tab change signal to track active tab
        self.tabs.currentChanged.connect(self.tab_changed)

        # Connect general settings changes to weight distribution
        self.general_settings_tab.settings_changed.connect(self.update_weight_distribution_settings)

        # Initial update of weight distribution settings
        self.update_weight_distribution_settings()

        # Set initial active tab
        self.bt_manager.set_active_tab("live_feed")
        self.tab_changed(self.tabs.currentIndex())

    def handle_connection_status(self, msg):
        """
        Handle connection status changes to detect when connecting to FAKE_COM.
        """
        print(f"DEBUG: MainWindow received status: {msg}")

        # Detect connection to FAKE_COM
        if "Connected to FAKE_COM" in msg:
            self.connected_port = FakeBluetoothManager.FAKE_PORT
            self.using_fake_manager = True
            print("Connected to fake Bluetooth manager")
        # Detect disconnection from FAKE_COM
        elif "Disconnected from FAKE_COM" in msg:
            self.connected_port = None
            print("Disconnected from fake Bluetooth manager")

            # If we were using a fake manager and disconnected, delay before switching
            if self.using_fake_manager:
                print("DEBUG: Scheduling switch to real manager after delay")
                # Use QTimer to delay the switch to ensure signals propagate
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, self.switch_to_real_manager)
                return  # Return early to prevent immediate switch
        # Detect connection to real port
        elif "Connected to" in msg and FakeBluetoothManager.FAKE_PORT not in msg:
            self.connected_port = msg.split("Connected to ")[1].split(" ")[0]
            self.using_fake_manager = False
            print(f"Connected to real port: {self.connected_port}")
        # General disconnection
        elif "[Status] Disconnected" in msg:
            self.connected_port = None
            print("DEBUG: General disconnection detected")

            # If we were using a fake manager and disconnected, need to switch back to real
            if self.using_fake_manager:
                print("DEBUG: Switching to real manager after disconnect")
                self.switch_to_real_manager()

    def switch_to_fake_manager(self):
        """
        Switch from real manager to fake manager with improved signal management.
        """
        # Skip if we're already using a fake manager
        if isinstance(self.bt_manager, FakeBluetoothManager):
            return

        print("Switching to fake Bluetooth manager...")

        # Reset the connection registry to clear connection tracking
        reset_connections()

        # Create a fresh fake manager
        fake_manager = FakeBluetoothManager()

        # Store old manager's active tab and disconnect it
        old_active_tab = self.bt_manager.active_tab
        old_manager = self.bt_manager

        # Set the new manager before disconnecting to ensure correct routing
        self.bt_manager = fake_manager
        self.using_fake_manager = True

        # Now disconnect the old manager (might send disconnect signals)
        try:
            if hasattr(old_manager, 'disconnect'):
                old_manager.disconnect()
        except Exception as e:
            print(f"Error disconnecting old manager: {e}")

        # Set active tab to match old manager
        fake_manager.set_active_tab(old_active_tab)

        # Update all tab references to the new manager
        self.live_feed_tab.bt_manager = fake_manager
        self.bluetooth_settings_tab.bt_manager = fake_manager
        self.calibration_tab.bt_manager = fake_manager
        self.users_tab.bt_manager = fake_manager

        # Update profile_edit_view reference if it exists
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'bt_manager'):
            try:
                self.users_tab.profile_edit_view.bt_manager = fake_manager
                print("Updated profile_edit_view.bt_manager reference")
            except Exception as e:
                print(f"Error updating profile_edit_view: {e}")

        # Connect signals using safe_connect to prevent duplicates
        safe_connect(fake_manager.status_signal, self.handle_connection_status, "main_status")

        # LiveFeed connections
        if hasattr(self.live_feed_tab, 'handle_data'):
            safe_connect(fake_manager.data_signal, self.live_feed_tab.handle_data, "live_feed_data")

        if hasattr(self.live_feed_tab, 'handle_status'):
            safe_connect(fake_manager.status_signal, self.live_feed_tab.handle_status, "live_feed_status")

        # Settings connections
        if hasattr(self.bluetooth_settings_tab, 'handle_data'):
            safe_connect(fake_manager.data_signal, self.bluetooth_settings_tab.handle_data, "settings_data")

        if hasattr(self.bluetooth_settings_tab, 'handle_stop_result') and hasattr(fake_manager,
                                                                                  'stop_completed_signal'):
            safe_connect(fake_manager.stop_completed_signal, self.bluetooth_settings_tab.handle_stop_result,
                         "settings_stop")

        # Calibration connections
        if hasattr(self.calibration_tab, 'handle_data_line'):
            safe_connect(fake_manager.data_signal, self.calibration_tab.handle_data_line, "calibration_data")

        if hasattr(self.calibration_tab, 'handle_stop_result') and hasattr(fake_manager, 'stop_completed_signal'):
            safe_connect(fake_manager.stop_completed_signal, self.calibration_tab.handle_stop_result,
                         "calibration_stop")

        # Users connections
        if hasattr(self.users_tab, 'handle_data'):
            safe_connect(fake_manager.data_signal, self.users_tab.handle_data, "users_data")

        # Profile edit view connections
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'handle_data'):
            safe_connect(fake_manager.data_signal, self.users_tab.profile_edit_view.handle_data, "profile_edit_data")

        print("Successfully switched to fake Bluetooth manager")

    def switch_to_real_manager(self):
        """
        Switch from fake manager to real manager with improved signal management.
        """
        # Skip if we're already using a real manager
        if not isinstance(self.bt_manager, FakeBluetoothManager):
            return

        print("Switching to real Bluetooth manager...")

        # Reset the connection registry to clear connection tracking
        reset_connections()

        # Create a fresh real manager
        real_manager = BluetoothManager()

        # Store old manager's active tab and disconnect it
        old_active_tab = self.bt_manager.active_tab
        old_manager = self.bt_manager

        # Set the new manager before disconnecting to ensure correct routing
        self.bt_manager = real_manager
        self.using_fake_manager = False

        # Now disconnect the old manager (might send disconnect signals)
        try:
            if hasattr(old_manager, 'disconnect'):
                old_manager.disconnect()
        except Exception as e:
            print(f"Error disconnecting old manager: {e}")

        # Set active tab to match old manager
        real_manager.set_active_tab(old_active_tab)

        # Update all tab references to the new manager
        self.live_feed_tab.bt_manager = real_manager
        self.bluetooth_settings_tab.bt_manager = real_manager
        self.calibration_tab.bt_manager = real_manager
        self.users_tab.bt_manager = real_manager

        # Update profile_edit_view reference if it exists
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'bt_manager'):
            try:
                self.users_tab.profile_edit_view.bt_manager = real_manager
                print("Updated profile_edit_view.bt_manager reference")
            except Exception as e:
                print(f"Error updating profile_edit_view: {e}")

        # Connect signals using safe_connect to prevent duplicates
        safe_connect(real_manager.status_signal, self.handle_connection_status, "main_status")

        # LiveFeed connections
        if hasattr(self.live_feed_tab, 'handle_data'):
            safe_connect(real_manager.data_signal, self.live_feed_tab.handle_data, "live_feed_data")

        if hasattr(self.live_feed_tab, 'handle_status'):
            safe_connect(real_manager.status_signal, self.live_feed_tab.handle_status, "live_feed_status")

        # Settings connections
        if hasattr(self.bluetooth_settings_tab, 'handle_data'):
            safe_connect(real_manager.data_signal, self.bluetooth_settings_tab.handle_data, "settings_data")

        if hasattr(self.bluetooth_settings_tab, 'handle_stop_result') and hasattr(real_manager,
                                                                                  'stop_completed_signal'):
            safe_connect(real_manager.stop_completed_signal, self.bluetooth_settings_tab.handle_stop_result,
                         "settings_stop")

        # Calibration connections
        if hasattr(self.calibration_tab, 'handle_data_line'):
            safe_connect(real_manager.data_signal, self.calibration_tab.handle_data_line, "calibration_data")

        if hasattr(self.calibration_tab, 'handle_stop_result') and hasattr(real_manager, 'stop_completed_signal'):
            safe_connect(real_manager.stop_completed_signal, self.calibration_tab.handle_stop_result,
                         "calibration_stop")

        # Users connections
        if hasattr(self.users_tab, 'handle_data'):
            safe_connect(real_manager.data_signal, self.users_tab.handle_data, "users_data")

        # Profile edit view connections
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'handle_data'):
            safe_connect(real_manager.data_signal, self.users_tab.profile_edit_view.handle_data, "profile_edit_data")

        print("Successfully switched to real Bluetooth manager")

    def update_manager_references_without_signals(self, new_manager):
        """
        Update references to the Bluetooth manager in all tabs WITHOUT connecting signals.
        """
        # Update tab references
        self.live_feed_tab.bt_manager = new_manager
        self.bluetooth_settings_tab.bt_manager = new_manager
        self.calibration_tab.bt_manager = new_manager
        self.users_tab.bt_manager = new_manager

        # Update profile_edit_view reference if it exists
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'bt_manager'):
            try:
                self.users_tab.profile_edit_view.bt_manager = new_manager
                print("Updated profile_edit_view.bt_manager reference")
            except Exception as e:
                print(f"Error updating profile_edit_view: {e}")

    def _connect_manager_signals(self, manager):
        """
        Cleanly connect all signals from the manager to appropriate handlers.
        """
        # --- MainWindow connections ---
        safe_connect(manager.status_signal, self.handle_connection_status, "main_status")

        # --- LiveFeedTab connections ---
        if hasattr(self.live_feed_tab, 'handle_data'):
            safe_connect(manager.data_signal, self.live_feed_tab.handle_data, "live_feed_data")

        if hasattr(self.live_feed_tab, 'handle_status'):
            safe_connect(manager.status_signal, self.live_feed_tab.handle_status, "live_feed_status")

        # --- Settings tab (bluetooth_settings_tab) connections ---
        # IMPORTANT: Only connect to data_signal to avoid duplicate status messages
        if hasattr(self.bluetooth_settings_tab, 'handle_data'):
            safe_connect(manager.data_signal, self.bluetooth_settings_tab.handle_data, "settings_data")

        if hasattr(self.bluetooth_settings_tab, 'handle_stop_result') and hasattr(manager, 'stop_completed_signal'):
            safe_connect(manager.stop_completed_signal, self.bluetooth_settings_tab.handle_stop_result, "settings_stop")

        # --- Calibration tab connections ---
        if hasattr(self.calibration_tab, 'handle_data_line'):
            safe_connect(manager.data_signal, self.calibration_tab.handle_data_line, "calibration_data")

        if hasattr(self.calibration_tab, 'handle_stop_result') and hasattr(manager, 'stop_completed_signal'):
            safe_connect(manager.stop_completed_signal, self.calibration_tab.handle_stop_result, "calibration_stop")

        # --- Users tab connections ---
        if hasattr(self.users_tab, 'handle_data'):
            safe_connect(manager.data_signal, self.users_tab.handle_data, "users_data")

        # --- Profile edit view connections ---
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'handle_data'):
            safe_connect(manager.data_signal, self.users_tab.profile_edit_view.handle_data, "profile_edit_data")

    def update_manager_references(self, new_manager):
        """
        Update references to the Bluetooth manager in all tabs.
        """
        # Update references in tabs
        self.live_feed_tab.bt_manager = new_manager
        self.bluetooth_settings_tab.bt_manager = new_manager
        self.calibration_tab.bt_manager = new_manager
        self.users_tab.bt_manager = new_manager

        # Log the reference updates for debugging
        print(f"DEBUG: Updated bt_manager reference for all tabs")

        # Explicitly disconnect any existing connections to prevent duplicates
        if hasattr(new_manager, 'data_signal'):
            try:
                new_manager.data_signal.disconnect()
                print("DEBUG: Disconnected all existing data_signal connections")
            except:
                print("DEBUG: No existing data_signal connections to disconnect")

        if hasattr(new_manager, 'status_signal'):
            try:
                new_manager.status_signal.disconnect()
                print("DEBUG: Disconnected all existing status_signal connections")
            except:
                print("DEBUG: No existing status_signal connections to disconnect")

        if hasattr(new_manager, 'stop_completed_signal'):
            try:
                new_manager.stop_completed_signal.disconnect()
                print("DEBUG: Disconnected all existing stop_completed_signal connections")
            except:
                print("DEBUG: No existing stop_completed_signal connections to disconnect")

        # Update signal connections in each tab - use more direct connection approach

        # 1. First connect the main window to status_signal for manager switching
        new_manager.status_signal.connect(self.handle_connection_status)
        print("DEBUG: Connected status_signal to MainWindow.handle_connection_status")

        # 2. Connect LiveFeedTab to signals
        if hasattr(self.live_feed_tab, 'handle_data'):
            new_manager.data_signal.connect(self.live_feed_tab.handle_data)
            print("Connected data_signal to live_feed.handle_data")

        if hasattr(self.live_feed_tab, 'handle_status'):
            new_manager.status_signal.connect(self.live_feed_tab.handle_status)
            print("Connected status_signal to live_feed.handle_status")

        # 3. Only connect SettingsTab to data_signal (NOT status_signal)
        if hasattr(self.bluetooth_settings_tab, 'handle_data'):
            new_manager.data_signal.connect(self.bluetooth_settings_tab.handle_data)
            print("Connected data_signal to bluetooth_settings.handle_data")

        # 4. Connect stop_completed_signal where needed
        if hasattr(self.bluetooth_settings_tab, 'handle_stop_result') and hasattr(new_manager, 'stop_completed_signal'):
            new_manager.stop_completed_signal.connect(self.bluetooth_settings_tab.handle_stop_result)
            print("Connected stop_completed_signal to bluetooth_settings.handle_stop_result")

        if hasattr(self.calibration_tab, 'handle_stop_result') and hasattr(new_manager, 'stop_completed_signal'):
            new_manager.stop_completed_signal.connect(self.calibration_tab.handle_stop_result)
            print("Connected stop_completed_signal to calibration.handle_stop_result")

        # 5. Connect other tabs as needed
        if hasattr(self.calibration_tab, 'handle_data'):
            new_manager.data_signal.connect(self.calibration_tab.handle_data)
            print("Connected data_signal to calibration.handle_data")

        if hasattr(self.users_tab, 'handle_data'):
            new_manager.data_signal.connect(self.users_tab.handle_data)
            print("Connected data_signal to users.handle_data")

        # For users tab, also update profile_edit_view if it exists
        if hasattr(self.users_tab, 'profile_edit_view') and hasattr(self.users_tab.profile_edit_view, 'bt_manager'):
            try:
                self.users_tab.profile_edit_view.bt_manager = new_manager
                print("Updated profile_edit_view.bt_manager reference")

                if hasattr(self.users_tab.profile_edit_view, 'handle_data'):
                    new_manager.data_signal.connect(self.users_tab.profile_edit_view.handle_data)
                    print("Connected data_signal to profile_edit_view.handle_data")
            except Exception as e:
                print(f"Error updating profile_edit_view: {e}")

        print("Updated all manager references")

    def tab_changed(self, index):
        """Update the bluetooth manager about which tab is active using string identifiers"""
        # Get the correct identifier for this tab index
        tab_id = self.tab_identifiers.get(index, "unknown")

        # Tell bluetooth manager which tab is active
        self.bt_manager.set_active_tab(tab_id)
        print(f"Switched to tab: {tab_id}")

    def update_weight_distribution_settings(self):
        """Update the weight distribution calculator with settings from general settings tab"""
        try:
            print("DEBUG [Main] update_weight_distribution_settings called")
            settings = self.general_settings_tab.get_settings()
            print(f"DEBUG [Main] Settings retrieved: {settings}")

            # Update sensor positions
            if "sensor_positions" in settings:
                print(f"DEBUG [Main] Updating sensor positions: {settings['sensor_positions']}")
                self.weight_distribution.update_sensor_positions(settings["sensor_positions"])

            # Update ideal COM
            if "ideal_com" in settings:
                print(f"DEBUG [Main] Updating ideal COM: {settings['ideal_com']}")
                self.weight_distribution.update_ideal_com(settings["ideal_com"])

            print("DEBUG [Main] Weight distribution settings updated")
        except Exception as e:
            print(f"ERROR [Main] Error updating weight distribution settings: {e}")
            import traceback
            traceback.print_exc()


def main():
    # Configure platform-specific settings
    configure_platform()

    app = QApplication(sys.argv)

    # Apply platform-specific styling
    if sys.platform == 'darwin':  # macOS
        # Use macOS native styling where possible
        app.setStyle('Fusion')  # Fusion style works well on macOS too
    else:
        # Use Fusion style for Windows & Linux
        app.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()