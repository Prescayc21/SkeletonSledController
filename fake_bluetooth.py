import threading
import time
import random
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import sys


class FakeBluetoothManager(QObject):
    """
    A simplified fake Bluetooth manager that simulates a Bluetooth connection.
    """
    data_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    stop_completed_signal = pyqtSignal(bool)

    # Choose fake port name based on platform
    if sys.platform == 'darwin':  # macOS
        FAKE_PORT = "/dev/tty.FAKE_DEVICE"
    else:  # Windows, Linux, etc.
        FAKE_PORT = "FAKE_COM"

    def __init__(self):
        super().__init__()

        # Connection state
        self.is_connected = False
        self.streaming_data = False
        self.recent_commands = {}
        self._initial_stop_sent = False

        # For rate limiting
        self._last_packet_time = 0

        # Create a fake serial object
        class FakeSerial:
            def __init__(self):
                self.is_open = False
                self.port = None
                self.baudrate = None
                self.in_waiting = 0

            def close(self):
                self.is_open = False

            def write(self, data):
                pass

            def flush(self):
                pass

            def read(self, size):
                return b''

        self.serial = FakeSerial()

        # Active tab tracking
        self.active_tab = "live_feed"

        # Tab behavior settings
        self.tab_behaviors = {
            "bluetooth_settings": {
                "forward_sensor_data": False,
                "forward_command_responses": True
            },
            "calibration": {
                "forward_sensor_data": True,
                "forward_command_responses": True
            },
            "live_feed": {
                "forward_sensor_data": True,
                "forward_command_responses": True
            },
            "users": {
                "forward_sensor_data": True,
                "forward_command_responses": True
            },
            "general_settings": {
                "forward_sensor_data": False,
                "forward_command_responses": True
            }
        }

        # Sensor values (with default test values)
        self.sensor_values = [5.0, 5.0, 5.0, 5.0]

        # Data streaming control
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self._send_data_packet)
        self.data_timer.setInterval(500)  # 500ms = 2Hz data rate

        # Flag for noise addition
        self.add_noise = True
        self.noise_amplitude = 0.1

        # Data forwarding flags
        self.forward_data = False
        self.read_pending = False

    def log_status(self, message):
        """Print a formatted status message and emit it as a signal"""
        formatted_msg = f"[{self.__class__.__name__}] {message}"
        print(formatted_msg)
        self.status_signal.emit(formatted_msg)

    def list_ports(self):
        """Return list of fake ports"""
        return [self.FAKE_PORT]

    def connect(self, port, baudrate=9600):
        """Connect to fake port"""
        if port != self.FAKE_PORT:
            self.status_signal.emit(f"[Error] Cannot connect to {port}. Only {self.FAKE_PORT} is supported.")
            return

        # Prevent multiple connection attempts
        if self.is_connected:
            print("DEBUG: Already connected, ignoring duplicate connect call")
            return

        # Important: Only emit a single "Connecting" message
        self.status_signal.emit(f"Connecting to {port} at {baudrate} baud...")

        # Use a single timer to complete the connection once
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._complete_connection(port, baudrate))

    def _complete_connection(self, port, baudrate):
        """Complete the connection process after delay"""
        try:
            # Skip if already connected to avoid duplicates
            if self.is_connected:
                print("DEBUG: Already connected, skipping duplicate connection")
                return

            # Setup the serial object
            self.serial.is_open = True
            self.serial.port = port
            self.serial.baudrate = baudrate

            # Set connected state
            self.is_connected = True

            # Clear the initial stop sent flag to ensure we start fresh
            self._initial_stop_sent = False

            # Emit status messages - first to main app for status tracking
            print("DEBUG: Emitting connection status messages")
            self.status_signal.emit(f"Connected to {port}")
            self.status_signal.emit("[Status] Connected")

            # Now emit a clear message to the console that will show in the Bluetooth UI
            self.data_signal.emit(f"=== CONNECTED TO {port} ===")

            # Send STOPPED message only once
            print("DEBUG: Sending initial STOPPED message")
            self.data_signal.emit("STOPPED")
            self._initial_stop_sent = True

        except Exception as e:
            self.status_signal.emit(f"[Error] Connection failed: {str(e)}")

    # Replace the disconnect method with:
    def disconnect(self):
        """Disconnect from fake port"""
        print("DEBUG: FakeBluetoothManager.disconnect called")

        # Skip if already disconnected
        if not self.is_connected:
            print("DEBUG: Already disconnected, skipping")
            return

        # Stop data streaming
        if self.data_timer.isActive():
            self.data_timer.stop()

        # Reset state
        self.streaming_data = False
        self.is_connected = False
        self.serial.is_open = False

        # Send a clear message to the console that will show in the Bluetooth UI
        self.data_signal.emit(f"=== DISCONNECTED FROM {self.FAKE_PORT} ===")

        # Emit disconnection signals for status tracking
        print("DEBUG: Emitting disconnection status signals")
        self.status_signal.emit(f"Disconnected from {self.FAKE_PORT}")

        # Add a small delay to ensure signals are processed in order
        import time
        time.sleep(0.05)

        # Then emit standard disconnection message
        self.status_signal.emit("[Status] Disconnected")

    def set_active_tab(self, tab_id):
        """Set the active tab"""
        self.active_tab = tab_id
        print(f"[FakeBluetoothManager] Active tab set to: {tab_id}")

        # Apply tab-specific behaviors
        if tab_id in self.tab_behaviors:
            if self.streaming_data and self.tab_behaviors[tab_id]["forward_sensor_data"]:
                self.forward_data = True
            elif not self.tab_behaviors[tab_id]["forward_sensor_data"]:
                self.forward_data = False

    def send_command(self, command):
        """Process a command with improved duplicate prevention"""
        command = command.strip()

        # Check if this is a duplicate within a short time window
        import time
        current_time = time.time()

        if hasattr(self, 'recent_commands') and command in self.recent_commands:
            last_time = self.recent_commands[command]
            if current_time - last_time < 0.5:  # Within 0.5 seconds
                print(f"DEBUG: Ignoring duplicate command: {command} (sent {current_time - last_time:.2f}s ago)")
                return

        # Initialize if needed
        if not hasattr(self, 'recent_commands'):
            self.recent_commands = {}

        # Update command timestamp
        self.recent_commands[command] = current_time

        # Clean up old entries
        for cmd in list(self.recent_commands.keys()):
            if current_time - self.recent_commands[cmd] > 3.0:  # 3 seconds
                del self.recent_commands[cmd]

        # Now process the command
        print(f"[FakeBluetoothManager] Processing command: {command}")

        if command == "START":
            # Start data streaming
            self.streaming_data = True

            # Start the timer if not already running
            if not self.data_timer.isActive():
                self.data_timer.start()

            # Update forwarding based on active tab
            if self.active_tab in self.tab_behaviors:
                self.forward_data = self.tab_behaviors[self.active_tab]["forward_sensor_data"]

            # Send confirmation - once
            self.data_signal.emit("STARTED")

        elif command == "STOP":
            # Stop data streaming
            self.streaming_data = False
            self.forward_data = False

            # Stop the timer
            if self.data_timer.isActive():
                self.data_timer.stop()

            # Send confirmation - once
            self.data_signal.emit("STOPPED")

        elif command == "READ":
            # Request a single data packet
            self.read_pending = True
            self._send_data_packet()

        elif command.startswith("SET"):
            self._handle_set_command(command)

        elif command == "PING":
            # Simple response
            self.data_signal.emit("PONG")

        else:
            # Unknown command
            self.data_signal.emit(f"UNKNOWN_COMMAND: {command}")

    def send_stop_command(self):
        """Special method for STOP command with confirmation"""
        print("[FakeBluetoothManager] Sending STOP command")
        self.status_signal.emit("Stopping data stream...")

        # Process STOP
        self.send_command("STOP")

        # Emit confirmation after short delay
        QTimer.singleShot(100, lambda: self.stop_completed_signal.emit(True))

    def _handle_set_command(self, command):
        """Process SET commands in various formats"""
        try:
            # Standard format: SET(v1, v2, v3, v4)
            if command.startswith("SET(") and command.endswith(")"):
                values_str = command[4:-1]
                values = [float(v.strip()) for v in values_str.split(",")]

                if len(values) != 4:
                    raise ValueError(f"Expected 4 values, got {len(values)}")

                self.sensor_values = values
                self.data_signal.emit(f"SET_OK: Values set to {values}")

            # Preset configurations
            elif command == "SET_WEIGHT_TEST":
                # Good values for weight distribution testing
                self.sensor_values = [8.2, 7.8, 9.1, 8.9]
                self.data_signal.emit(f"SET_OK: Values set for weight test: {self.sensor_values}")

            elif command == "SET_EVEN":
                # Perfectly balanced
                self.sensor_values = [10.0, 10.0, 10.0, 10.0]
                self.data_signal.emit(f"SET_OK: Values set to even distribution: {self.sensor_values}")

            elif command == "SET_UNEVEN":
                # Unbalanced (front-left heavy)
                self.sensor_values = [15.0, 5.0, 5.0, 10.0]
                self.data_signal.emit(f"SET_OK: Values set to uneven distribution: {self.sensor_values}")

            elif command == "SET_RANDOM":
                # Random values
                self.sensor_values = [random.uniform(5.0, 15.0) for _ in range(4)]
                self.data_signal.emit(f"SET_OK: Values set to random distribution: {self.sensor_values}")

            elif command == "SET_USERS_TEST":
                # Special values optimized for Users tab
                self.sensor_values = [25.0, 20.0, 22.0, 18.0]
                self.data_signal.emit(f"SET_OK: Values set for Users tab testing: {self.sensor_values}")

            else:
                self.data_signal.emit(f"SET_ERROR: Unknown SET format: {command}")

        except Exception as e:
            self.data_signal.emit(f"SET_ERROR: {str(e)}")

    def _send_data_packet(self):
        """Generate and send a data packet with duplicate prevention"""
        if not self.is_connected:
            return

        # Add rate-limiting to prevent rapid duplicates
        if hasattr(self, '_last_packet_time'):
            import time
            now = time.time()
            if now - self._last_packet_time < 0.2:  # At least 200ms between packets
                return

        # Update last packet time
        import time
        self._last_packet_time = time.time()

        # Generate data with optional noise
        values = []
        for base_value in self.sensor_values:
            if self.add_noise:
                noise = (random.random() - 0.5) * 2 * self.noise_amplitude
                values.append(base_value + noise)
            else:
                values.append(base_value)

        # Format data packet
        data_packet = ", ".join([f"{value:.2f}" for value in values])

        # Check if we should send this packet
        should_forward = self.streaming_data and self.forward_data

        # Always send for READ requests
        if self.read_pending:
            should_forward = True
            self.read_pending = False

            # Reset forwarding for tabs that don't need continuous data
            if self.active_tab in self.tab_behaviors and not self.tab_behaviors[self.active_tab]["forward_sensor_data"]:
                self.forward_data = False

        # Send the data if needed
        if should_forward:
            print(f"DEBUG: Sending data packet: {data_packet[:20]}...")
            self.data_signal.emit(data_packet)