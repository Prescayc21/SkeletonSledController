import serial
import serial.tools.list_ports
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class BluetoothManager(QObject):
    data_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    stop_completed_signal = pyqtSignal(bool)  # Signal to inform about STOP result

    def __init__(self):
        super().__init__()
        self.serial = None
        self.read_thread = None
        self.keep_reading = False
        self.lock = threading.Lock()
        self.last_command_time = 0
        self.command_queue = []
        self.command_thread = None
        self.keep_sending = False

        # Data forwarding settings
        self.forward_data = False
        self.read_pending = False

        # Track which tab is currently active (using string identifiers)
        self.active_tab = "live_feed"  # Default to live_feed instead of settings

        # Define tab-specific behaviors
        self.tab_behaviors = {
            "bluetooth_settings": {  # Updated from "settings" to "bluetooth_settings"
                "forward_sensor_data": False,  # Settings tab just shows commands
                "forward_command_responses": True
            },
            "calibration": {
                "forward_sensor_data": True,  # Calibration needs sensor data
                "forward_command_responses": True
            },
            "live_feed": {
                "forward_sensor_data": True,  # Live feed needs all data
                "forward_command_responses": True
            },
            "users": {
                "forward_sensor_data": True,
                "forward_command_responses": True
            },
            "general_settings": {  # Add the new tab
                "forward_sensor_data": False,  # General settings tab doesn't need data
                "forward_command_responses": True
            }
        }

        # Stream status tracking
        self.streaming_data = False

        # STOP command tracking
        self.waiting_for_stop_ack = False
        self.stop_retry_timer = None
        self.stop_retry_count = 0
        self.max_stop_retries = 3
        self.stop_retry_interval = 500  # ms

    def log_status(self, message):
        """Print a formatted status message and emit it as a signal"""
        formatted_msg = f"[{self.__class__.__name__}] {message}"
        print(formatted_msg)
        self.status_signal.emit(formatted_msg)

    def list_ports(self):
        """List available serial ports in a cross-platform way"""
        import sys

        # Get all physical ports from the system
        available_ports = [port.device for port in serial.tools.list_ports.comports()]

        # Sort ports in a platform-appropriate way
        if sys.platform == 'darwin':  # macOS
            # On macOS, prioritize Bluetooth and USB serial ports
            mac_ports = []

            # First add Bluetooth ports
            for port in available_ports:
                if 'Bluetooth' in port:
                    mac_ports.append(port)

            # Then add USB serial ports
            for port in available_ports:
                if 'usbserial' in port or 'usbmodem' in port:
                    if port not in mac_ports:  # Avoid duplicates
                        mac_ports.append(port)

            # Add any remaining ports
            for port in available_ports:
                if port not in mac_ports:
                    mac_ports.append(port)

            available_ports = mac_ports
        else:
            # On Windows, sort COM ports numerically
            com_ports = [p for p in available_ports if p.startswith('COM')]
            try:
                com_ports.sort(key=lambda p: int(p[3:]) if p[3:].isdigit() else float('inf'))
            except:
                # Fall back to basic sorting if the above fails
                com_ports.sort()

            # Start with sorted COM ports
            sorted_ports = com_ports

            # Add any non-COM ports at the end
            for port in available_ports:
                if not port.startswith('COM') and port not in sorted_ports:
                    sorted_ports.append(port)

            available_ports = sorted_ports

        # Add fake port if appropriate
        try:
            # Attempt to import FakeBluetoothManager
            from fake_bluetooth import FakeBluetoothManager
            if hasattr(FakeBluetoothManager, 'FAKE_PORT'):
                available_ports.append(FakeBluetoothManager.FAKE_PORT)
        except ImportError:
            # Module not available, skip adding fake port
            pass

        return available_ports

    def connect(self, port, baudrate=9600):
        try:
            self.status_signal.emit(f"Connecting to {port} at {baudrate} baud...")
            self.serial = serial.Serial(port, baudrate, timeout=1)
            self.keep_reading = True
            self.read_thread = threading.Thread(target=self._read_data_thread, daemon=True)
            self.read_thread.start()

            # Also start the command sending thread
            self.keep_sending = True
            self.command_thread = threading.Thread(target=self._command_thread, daemon=True)
            self.command_thread.start()

            # Emit signals for status tracking
            self.status_signal.emit(f"Connected to {port}")
            self.status_signal.emit("[Status] Connected")

            # Send a clear message to the console for the Bluetooth UI
            self.data_signal.emit(f"=== CONNECTED TO {port} ===")

            time.sleep(1)
            self.send_command("STOP")
        except Exception as e:
            self.status_signal.emit(f"[Error] Connection failed: {e}")

    def disconnect(self):
        self.keep_reading = False
        self.keep_sending = False
        if self.serial and self.serial.is_open:
            try:
                # Send a clear message to the console for the Bluetooth UI
                self.data_signal.emit(f"=== DISCONNECTED ===")

                self.serial.close()
                self.status_signal.emit("[Status] Disconnected")
            except Exception as e:
                self.status_signal.emit(f"[Error] Disconnect failed: {e}")

    def set_active_tab(self, tab_id):
        """Set which tab is currently active using string identifier, with duplicate prevention"""
        # Skip if already set to this tab (prevents duplicate events)
        if self.active_tab == tab_id:
            return

        self.active_tab = tab_id
        print(f"[BluetoothManager] Active tab set to: {tab_id}")

        # If we have tab-specific behaviors defined, apply them
        if tab_id in self.tab_behaviors:
            # If we're actively streaming data and the new tab needs data
            if self.streaming_data and self.tab_behaviors[tab_id]["forward_sensor_data"]:
                self.forward_data = True
            # If the new tab doesn't need sensor data, stop forwarding
            elif not self.tab_behaviors[tab_id]["forward_sensor_data"]:
                self.forward_data = False

    def send_command(self, command):
        """Add command to queue for processing by command thread"""
        cmd = command.strip()
        self.command_queue.append(cmd)

        # If this is START/STOP, update data forwarding mode
        if cmd == "START":
            self.streaming_data = True
            # Only set forward_data to true if the active tab needs sensor data
            if self.active_tab in self.tab_behaviors and self.tab_behaviors[self.active_tab]["forward_sensor_data"]:
                self.forward_data = True
            else:
                self.forward_data = False
        elif cmd == "STOP":
            # Handle STOP specially - don't update streaming_data until we get confirmation
            # This is now handled in the _read_data_thread when "STOPPED" response is received
            pass
        elif cmd == "READ":
            self.forward_data = True  # But do forward one reading
            self.read_pending = True  # Flag that we need one reading

    def send_stop_command(self):
        """Send STOP command with retry capability"""
        # If we're already trying to stop, don't start another attempt
        if self.waiting_for_stop_ack:
            return

        self.status_signal.emit("Stopping data stream...")
        self.send_command("STOP")

        # Set up retry mechanism
        self.waiting_for_stop_ack = True
        self.stop_retry_count = 0

        # Create a timer for retry
        self.stop_retry_timer = QTimer()
        self.stop_retry_timer.timeout.connect(self._check_stop_ack)
        self.stop_retry_timer.start(self.stop_retry_interval)

    def _check_stop_ack(self):
        """Check if STOP was acknowledged, retry if needed"""
        # If we're no longer streaming, STOP was successful
        if not self.streaming_data:
            self.waiting_for_stop_ack = False
            self.stop_retry_timer.stop()
            self.stop_completed_signal.emit(True)
            print("[BluetoothManager] STOP command confirmed")
            return

        # If we've reached max retries, give up
        if self.stop_retry_count >= self.max_stop_retries:
            self.waiting_for_stop_ack = False
            self.stop_retry_timer.stop()
            self.status_signal.emit("[Warning] Failed to confirm STOP after multiple attempts")
            self.stop_completed_signal.emit(False)
            print("[BluetoothManager] STOP command failed after max retries")
            return

        # Otherwise, retry
        self.stop_retry_count += 1
        print(f"[BluetoothManager] Retrying STOP command (attempt {self.stop_retry_count}/{self.max_stop_retries})")
        self.send_command("STOP")

    def _command_thread(self):
        """Process commands from queue with proper timing"""
        while self.keep_sending:
            if self.command_queue and self.serial and self.serial.is_open:
                # Get the next command
                command = self.command_queue.pop(0)

                # Ensure we don't send commands too quickly
                now = time.time()
                if now - self.last_command_time < 0.1:
                    time.sleep(0.1)  # Ensure minimum gap between commands

                try:
                    # Send the command with proper termination
                    clean_command = command.strip() + "\r\n"
                    with self.lock:
                        self.serial.write(clean_command.encode("utf-8"))
                        # Flush to ensure data is sent immediately
                        self.serial.flush()

                    self.last_command_time = time.time()
                    print(f"[BluetoothManager] Sent: {command}")
                except Exception as e:
                    self.status_signal.emit(f"[Error] Failed to send command: {e}")
            else:
                # Sleep a bit to avoid CPU spinning
                time.sleep(0.05)

    def _read_data_thread(self):
        partial_line = ""

        while self.keep_reading:
            try:
                if self.serial and self.serial.is_open:
                    if self.serial.in_waiting:
                        # Read incoming bytes
                        data = self.serial.read(self.serial.in_waiting).decode("utf-8", errors="ignore")

                        if data:
                            # Combine with any partial line from previous read
                            partial_line += data

                            # Process complete lines
                            lines = partial_line.splitlines(True)  # Keep line endings

                            # Save the last incomplete line (if any)
                            partial_line = ""

                            for line in lines:
                                if line.endswith('\n') or line.endswith('\r'):
                                    # This is a complete line, process it
                                    clean_line = line.strip()
                                    if clean_line:
                                        print(f"[BluetoothManager] Received: {clean_line}")

                                        # Check if this is a sensor data line (comma-separated numbers)
                                        is_sensor_data = "," in clean_line and all(
                                            part.strip().replace(".", "").replace("-", "").isdigit()
                                            for part in clean_line.split(",") if part.strip()
                                        )

                                        # Handle command responses
                                        if not is_sensor_data:
                                            # Check for STOPPED response
                                            if "STOPPED" in clean_line:
                                                self.streaming_data = False
                                                self.forward_data = False

                                                # If we were waiting for STOP confirmation, signal success
                                                if self.waiting_for_stop_ack:
                                                    self.waiting_for_stop_ack = False
                                                    if self.stop_retry_timer:
                                                        self.stop_retry_timer.stop()
                                                    self.stop_completed_signal.emit(True)

                                            # If this is a STARTED response, update streaming state
                                            elif "STARTED" in clean_line:
                                                self.streaming_data = True
                                                # Set forward_data based on active tab's behavior
                                                if self.active_tab in self.tab_behaviors:
                                                    self.forward_data = self.tab_behaviors[self.active_tab][
                                                        "forward_sensor_data"]

                                            # Always emit command responses for everyone
                                            self.data_signal.emit(clean_line)

                                        # For sensor data, only forward if the active tab needs it
                                        elif is_sensor_data:
                                            # Forward data if either:
                                            # 1. We're supposed to forward all data to the active tab
                                            # 2. We're waiting for a single READ response
                                            should_forward = self.forward_data or self.read_pending

                                            if should_forward:
                                                self.data_signal.emit(clean_line)

                                                # If we were waiting for a single READ, mark it as received
                                                if self.read_pending:
                                                    self.read_pending = False

                                                    # If the active tab doesn't need continuous data,
                                                    # stop forwarding after this READ
                                                    if self.active_tab in self.tab_behaviors and not \
                                                    self.tab_behaviors[self.active_tab]["forward_sensor_data"]:
                                                        self.forward_data = False
                                else:
                                    # This is an incomplete line, save for next iteration
                                    partial_line = line
            except Exception as e:
                self.status_signal.emit(f"[Error] Read thread error: {e}")
                time.sleep(0.1)  # Avoid rapid error loops

            # Sleep to avoid high CPU usage when there's no data
            time.sleep(0.01)