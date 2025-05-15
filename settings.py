from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QHBoxLayout, QLineEdit
import serial.tools.list_ports
import threading
from PyQt5.QtCore import QTimer
from fake_bluetooth import FakeBluetoothManager  # Import the fake manager


class SettingsTab(QWidget):
    def __init__(self, bt_manager):
        super().__init__()
        self.bt_manager = bt_manager
        self._sending = False
        self.is_active = False  # Track if this tab is currently visible
        self.layout = QVBoxLayout(self)

        # Port picker
        row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        row.addWidget(QLabel("Port:"))
        row.addWidget(self.port_combo)
        row.addWidget(self.refresh_btn)
        self.layout.addLayout(row)

        # Connect/Disconnect
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.connect_btn.clicked.connect(self.connect)
        self.disconnect_btn.clicked.connect(self.disconnect)
        self.layout.addWidget(self.connect_btn)
        self.layout.addWidget(self.disconnect_btn)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.layout.addWidget(QLabel("Console"))
        self.layout.addWidget(self.console)

        # Command
        row2 = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)
        self.command_send = QPushButton("Send")
        self.command_send.clicked.connect(self.send_command)
        row2.addWidget(self.command_input)
        row2.addWidget(self.command_send)
        self.layout.addLayout(row2)

        # Buffered console messages when tab is inactive
        self.buffered_important_messages = []

        # Connect signals
        # Create a single connection to data_signal
        print("DEBUG: Connecting SettingsTab to data_signal - initial connection")
        self.bt_manager.data_signal.connect(self.handle_data)

        # Connect to status_signal
        print("DEBUG: Connecting SettingsTab to status_signal - initial connection")
        self.bt_manager.status_signal.connect(self.handle_status)

        # Connect to the stop completed signal if it exists
        if hasattr(self.bt_manager, 'stop_completed_signal'):
            self.bt_manager.stop_completed_signal.connect(self.handle_stop_result)

        # Initial setup
        self.refresh_ports()

    def _block_signals(self, block=True):
        """
        Block/unblock all signals to prevent duplicates.

        Args:
            block: True to block signals, False to unblock
        """
        if hasattr(self.bt_manager, 'data_signal'):
            self.bt_manager.data_signal.blockSignals(block)

        if hasattr(self.bt_manager, 'status_signal'):
            self.bt_manager.status_signal.blockSignals(block)

        if hasattr(self.bt_manager, 'stop_completed_signal'):
            self.bt_manager.stop_completed_signal.blockSignals(block)

    def append_console(self, msg):
        """Add message to console"""
        self.console.append(msg)

    def handle_status(self, msg):
        """
        Handle status messages - buffer important ones if tab is inactive
        """
        # If tab is not active, only buffer critical messages
        if not self.is_active:
            # Only buffer important messages
            if ("[Status]" in msg or
                    "Connected to" in msg or
                    "Disconnected" in msg or
                    "Ports refreshed" in msg):
                self.buffered_important_messages.append(msg)
            # Ignore other status messages when inactive
            return

        # Tab is active, append the message to console
        self.console.append(msg)

    def handle_stop_result(self, success):
        """Handle the result of a STOP command"""
        msg = "STOP command executed successfully" if success else "[Warning] STOP command failed after multiple attempts"
        if self.is_active:
            self.append_console(msg)
        else:
            self.buffered_important_messages.append(msg)

    def handle_data(self, line):
        """Process incoming data with strict duplicate prevention"""
        # If not active, don't process at all
        if not self.is_active:
            return

        # Skip duplicate lines using a simple caching mechanism
        if hasattr(self, '_last_data_line') and self._last_data_line == line:
            print(f"DEBUG: Skipping duplicate data line: {line[:20]}...")
            return

        # Store this line to detect duplicates
        self._last_data_line = line

        # Process the data
        if "," in line:
            try:
                # Only format if it's sensor data (comma-separated values)
                parts = line.split(",")
                if len(parts) >= 4:
                    # Check if all parts can be treated as numbers
                    can_be_numbers = True
                    for part in parts[:4]:
                        part = part.strip()
                        if not part.replace(".", "").replace("-", "").isdigit():
                            can_be_numbers = False
                            break

                    if can_be_numbers:
                        vals = [part.strip() for part in parts[:4]]
                        self.append_console(f"Data: S1={vals[0]}, S2={vals[1]}, S3={vals[2]}, S4={vals[3]}")
                        return
            except:
                pass

        # Just append the line directly for non-sensor data
        self.append_console(line.strip())

    def refresh_ports(self):
        """
        Get list of available ports and add FAKE_COM option.
        """
        # First get actual physical ports
        real_ports = [p.device for p in serial.tools.list_ports.comports()]

        # Add the fake port as an option
        all_ports = real_ports + [FakeBluetoothManager.FAKE_PORT]

        # Update the combo box
        self.port_combo.clear()
        self.port_combo.addItems(all_ports)

        if self.is_active:
            self.append_console("Ports refreshed.")
        else:
            self.buffered_important_messages.append("Ports refreshed.")

    def connect(self):
        """Connect to the selected port with signal management"""
        port = self.port_combo.currentText()
        if not port:
            return

        # Special handling for FAKE_COM
        if port == FakeBluetoothManager.FAKE_PORT:
            # Find the main window
            main_window = None
            parent = self.parent()
            while parent:
                if hasattr(parent, 'switch_to_fake_manager'):
                    main_window = parent
                    break
                parent = parent.parent()

            if main_window:
                # Temporarily disconnect our slots to avoid duplicates during switch
                if hasattr(self.bt_manager, 'data_signal'):
                    try:
                        self.bt_manager.data_signal.disconnect(self.handle_data)
                        print("Disconnected data signal during manager switch")
                    except TypeError:
                        pass

                if hasattr(self.bt_manager, 'status_signal'):
                    try:
                        self.bt_manager.status_signal.disconnect(self.handle_status)
                        print("Disconnected status signal during manager switch")
                    except TypeError:
                        pass

                if hasattr(self.bt_manager, 'stop_completed_signal'):
                    try:
                        self.bt_manager.stop_completed_signal.disconnect(self.handle_stop_result)
                        print("Disconnected stop signal during manager switch")
                    except TypeError:
                        pass

                # Log to console that we're switching
                self.append_console(f"Switching to fake Bluetooth manager...")

                # Switch to fake manager
                main_window.switch_to_fake_manager()

                # Update our reference to the new manager
                self.bt_manager = main_window.bt_manager

                # Wait a moment to ensure proper sequencing
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: self.bt_manager.connect(port))
            else:
                self.append_console("[Error] Could not find main window to switch managers")
        else:
            # Real port - make sure we're using a real manager
            if isinstance(self.bt_manager, FakeBluetoothManager):
                # Find the main window
                main_window = None
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'switch_to_real_manager'):
                        main_window = parent
                        break
                    parent = parent.parent()

                if main_window:
                    # Disconnect our signals first
                    if hasattr(self.bt_manager, 'data_signal'):
                        try:
                            self.bt_manager.data_signal.disconnect(self.handle_data)
                            print("Disconnected data signal during manager switch")
                        except TypeError:
                            pass

                    if hasattr(self.bt_manager, 'status_signal'):
                        try:
                            self.bt_manager.status_signal.disconnect(self.handle_status)
                            print("Disconnected status signal during manager switch")
                        except TypeError:
                            pass

                    if hasattr(self.bt_manager, 'stop_completed_signal'):
                        try:
                            self.bt_manager.stop_completed_signal.disconnect(self.handle_stop_result)
                            print("Disconnected stop signal during manager switch")
                        except TypeError:
                            pass

                    # Log to console that we're switching
                    self.append_console(f"Switching to real Bluetooth manager...")

                    # Switch to real manager
                    main_window.switch_to_real_manager()

                    # Update our reference to the new manager
                    self.bt_manager = main_window.bt_manager

                    # Connect to the real port
                    threading.Thread(target=self.bt_manager.connect, args=(port,), daemon=True).start()
                else:
                    self.append_console("[Error] Could not find main window to switch managers")
            else:
                # Already using real manager, just connect
                threading.Thread(target=self.bt_manager.connect, args=(port,), daemon=True).start()

    # Modified version for better handling:
    def disconnect(self):
        threading.Thread(target=self.bt_manager.disconnect, daemon=True).start()

    def send_command(self):
        if self._sending:
            return

        self._sending = True

        # If called by a button, use the command input field
        if isinstance(self.sender(), QPushButton):
            cmd = self.command_input.text().strip()
            if cmd:
                self.append_console(f"> {cmd}")
                self.bt_manager.send_command(cmd)
                self.command_input.clear()
        # If called by pressing Enter in the command field
        else:
            cmd = self.command_input.text().strip()
            if cmd:
                self.append_console(f"> {cmd}")
                self.bt_manager.send_command(cmd)
                self.command_input.clear()

        # Prevent rapid sending by temporarily disabling
        QTimer.singleShot(200, lambda: setattr(self, "_sending", False))

    def showEvent(self, event):
        """Called when the settings tab becomes visible"""
        super().showEvent(event)
        # Tell the bluetooth manager we're the active tab
        if hasattr(self.bt_manager, 'set_active_tab'):
            self.bt_manager.set_active_tab("bluetooth_settings")  # Use bluetooth_settings instead of settings
        self.is_active = True
        print("Settings tab is now visible")

        # Clear previous data cache to avoid false duplicate detection
        if hasattr(self, '_last_data_line'):
            del self._last_data_line

        # Process any buffered messages
        if hasattr(self, 'buffered_important_messages') and self.buffered_important_messages:
            # Add a header to show that these were buffered
            self.console.append("--- Buffered messages while tab was inactive ---")

            # Add all important messages - these shouldn't be too many
            for msg in self.buffered_important_messages:
                self.console.append(msg)

            # Clear the buffer
            self.buffered_important_messages = []

            # Add a separator
            self.console.append("--- End of buffered messages ---")

    def hideEvent(self, event):
        """Called when the settings tab is hidden"""
        super().hideEvent(event)
        self.is_active = False
        print("Settings tab is now hidden")