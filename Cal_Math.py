import json
import numpy as np


class CalibrationData:
    def __init__(self):
        # Initialize with empty calibrations for 4 sensors
        self.calibrations = []
        for _ in range(4):
            self.calibrations.append({
                "slope": 1.0,
                "intercept": 0.0,
                "unit": "g",
                "calibration_points": []  # List to store raw calibration points
            })

        # Add filename property
        self.filename = None

        # Debug flag
        self.debug = True

        self.loaded = False

    def apply(self, values, unit="g"):
        """
        Apply calibration to raw sensor values and convert to requested unit

        Args:
            values: List of raw sensor values
            unit: Target unit for conversion (g, kg, oz, lb)

        Returns:
            List of calibrated values in the requested unit
        """
        if self.debug:
            print(f"Applying calibration to {len(values)} values, target unit: {unit}")

        adjusted = []
        for i, value in enumerate(values):
            if i < len(self.calibrations):
                cal = self.calibrations[i]
                slope = cal.get("slope", 1.0)
                intercept = cal.get("intercept", 0.0)

                # Apply linear calibration: y = mx + b
                # Where:
                #   y = weight in grams
                #   m = slope
                #   x = raw value
                #   b = intercept
                calibrated_value = slope * value + intercept

                if self.debug and i == 0:  # Only show debug for first sensor to avoid spam
                    print(f"Sensor {i}: raw={value:.2f}, calibrated={calibrated_value:.2f}g")
            else:
                # Use identity calibration for out-of-range sensors
                calibrated_value = value

            # Convert to the requested unit (from grams)
            adjusted_value = self.convert_unit(calibrated_value, "g", unit)
            adjusted.append(adjusted_value)

        return adjusted

    def convert_unit(self, value, from_unit, to_unit):
        """
        Convert value from one unit to another

        Args:
            value: Value to convert
            from_unit: Source unit (g, kg, oz, lb)
            to_unit: Target unit (g, kg, oz, lb)

        Returns:
            Converted value
        """
        # First convert to grams (base unit)
        if from_unit != "g":
            if from_unit == "kg":
                value = value * 1000
            elif from_unit == "oz":
                value = value * 28.3495
            elif from_unit in ["lb", "lbs"]:
                value = value * 453.592

        # Now convert from g to target unit
        if to_unit == "g":
            return value
        elif to_unit == "kg":
            return value / 1000
        elif to_unit == "oz":
            return value * 0.03527396195
        elif to_unit in ["lb", "lbs"]:
            return value * 0.00220462262
        else:
            # Default to no conversion if unknown unit
            return value

    def set_sensor_calibration(self, sensor_index, calibration_points):
        """
        Set calibration for a specific sensor based on multiple calibration points

        Args:
            sensor_index: Sensor index (0-3)
            calibration_points: List of (raw_value, weight, unit) tuples

        Returns:
            True if calibration was successful, False otherwise
        """
        # Ensure sensor_index is valid
        if sensor_index < 0 or sensor_index >= len(self.calibrations):
            print(f"Error: Invalid sensor index {sensor_index}. Must be 0-3.")
            return False

        if self.debug:
            print(f"Setting calibration for sensor {sensor_index} with {len(calibration_points)} points")

        # Handle empty or insufficient points
        if not calibration_points or len(calibration_points) < 2:
            print(f"Warning: Not enough calibration points for sensor {sensor_index}. Setting default.")
            self.calibrations[sensor_index] = {
                "slope": 1.0,
                "intercept": 0.0,
                "unit": "g",
                "calibration_points": []
            }
            return False

        try:
            # Convert all points to common unit (g) for regression
            points_in_g = []
            for raw, weight, point_unit in calibration_points:
                # Convert weight to grams
                weight_g = self.convert_unit(weight, point_unit, "g")
                points_in_g.append((raw, weight_g))

                if self.debug:
                    print(f"  Point: raw={raw:.2f}, weight={weight}{point_unit} → {weight_g:.2f}g")

            # Extract x and y values for fitting
            x_vals = np.array([point[0] for point in points_in_g])
            y_vals = np.array([point[1] for point in points_in_g])

            # Perform linear regression (y = mx + b)
            # This fits a line that minimizes the sum of squared residuals
            slope, intercept = np.polyfit(x_vals, y_vals, 1)

            # Calculate R-squared to measure fit quality
            y_pred = slope * x_vals + intercept
            ss_total = np.sum((y_vals - np.mean(y_vals)) ** 2)
            ss_residual = np.sum((y_vals - y_pred) ** 2)
            r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

            if self.debug:
                print(f"  Fit results: slope={slope:.4f}, intercept={intercept:.2f}, R²={r_squared:.4f}")

            # Save the calibration parameters and original points
            self.calibrations[sensor_index] = {
                "slope": slope,
                "intercept": intercept,
                "unit": "g",  # Always store in base unit
                "r_squared": r_squared,
                "calibration_points": calibration_points
            }

            return True

        except Exception as e:
            print(f"Error during calibration calculation: {str(e)}")
            # Set default values on error
            self.calibrations[sensor_index] = {
                "slope": 1.0,
                "intercept": 0.0,
                "unit": "g",
                "calibration_points": []
            }
            return False

    def get_calibration_params(self, sensor_index):
        """
        Get calibration parameters for a specific sensor

        Args:
            sensor_index: Sensor index (0-3)

        Returns:
            Dictionary of calibration parameters or None if invalid
        """
        if sensor_index < 0 or sensor_index >= len(self.calibrations):
            return None

        return self.calibrations[sensor_index]

    def save_to_file(self, filepath):
        """
        Save calibration data to a file

        Args:
            filepath: Path to save the calibration file

        Returns:
            None
        """
        try:
            # Create a copy to remove unnecessary data
            save_data = []
            for cal in self.calibrations:
                # Create a clean copy with essential data
                cal_copy = {
                    "slope": cal.get("slope", 1.0),
                    "intercept": cal.get("intercept", 0.0),
                    "unit": cal.get("unit", "g"),
                    "calibration_points": cal.get("calibration_points", [])
                }
                save_data.append(cal_copy)

            # Add version information
            output_data = {
                "version": "2.0",
                "calibrations": save_data
            }

            with open(filepath, "w") as f:
                json.dump(output_data, f, indent=2)

            import os
            self.filename = os.path.basename(filepath)

            if self.debug:
                print(f"Calibration saved to {filepath}")

        except Exception as e:
            print(f"Error saving calibration file: {str(e)}")
            raise

    def load_from_file(self, filepath):
        """
        Load calibration data from a file

        Args:
            filepath: Path to load the calibration file from

        Returns:
            None
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Handle different format versions
            if isinstance(data, dict) and "version" in data:
                version = data.get("version", "1.0")

                if version.startswith("2"):
                    self.calibrations = data.get("calibrations", [])
                else:
                    self._convert_v1_format(data.get("calibrations", []))
            elif isinstance(data, list):
                self._convert_v1_format(data)
            else:
                raise ValueError(f"Unknown calibration file format")

            self._ensure_four_calibrations()

            import os
            self.filename = os.path.basename(filepath)
            self.loaded = True  # ✅ Set loaded flag

            if self.debug:
                print(f"Calibration loaded from {filepath}")
                for i, cal in enumerate(self.calibrations):
                    print(f"Sensor {i}: slope={cal.get('slope', 1.0):.4f}, "
                          f"intercept={cal.get('intercept', 0.0):.2f}")

        except Exception as e:
            print(f"Error loading calibration file: {str(e)}")
            raise

    def _convert_v1_format(self, old_calibrations):
        """
        Convert old format calibrations to new format

        Args:
            old_calibrations: List of old format calibration dictionaries

        Returns:
            None (updates self.calibrations)
        """
        self.calibrations = []

        for cal in old_calibrations:
            if isinstance(cal, dict):
                # Handle dictionary format
                zero_offset = cal.get("zero_offset", 0.0)
                scale_factor = cal.get("scale_factor", 1.0)
                unit = cal.get("unit", "g")

                # Convert to slope/intercept format using the formula:
                # (raw - offset) * scale = slope * raw + intercept
                # This gives: slope = scale, intercept = -offset * scale
                slope = scale_factor
                intercept = -zero_offset * scale_factor

                self.calibrations.append({
                    "slope": slope,
                    "intercept": intercept,
                    "unit": unit,
                    "calibration_points": []  # No points available from old format
                })
            elif isinstance(cal, tuple) and len(cal) >= 2:
                # Handle tuple format (offset, scale, unit)
                zero_offset = cal[0]
                scale_factor = cal[1]
                unit = cal[2] if len(cal) > 2 else "g"

                slope = scale_factor
                intercept = -zero_offset * scale_factor

                self.calibrations.append({
                    "slope": slope,
                    "intercept": intercept,
                    "unit": unit,
                    "calibration_points": []
                })
            else:
                # Unknown format, use defaults
                self.calibrations.append({
                    "slope": 1.0,
                    "intercept": 0.0,
                    "unit": "g",
                    "calibration_points": []
                })

        if self.debug:
            print(f"Converted {len(old_calibrations)} calibrations from old format")

    def _ensure_four_calibrations(self):
        """
        Ensure we have exactly 4 calibrations

        Args:
            None

        Returns:
            None (updates self.calibrations)
        """
        # Trim excess calibrations
        if len(self.calibrations) > 4:
            print(f"Warning: Trimming excess calibration data")
            self.calibrations = self.calibrations[:4]

        # Add missing calibrations
        while len(self.calibrations) < 4:
            self.calibrations.append({
                "slope": 1.0,
                "intercept": 0.0,
                "unit": "g",
                "calibration_points": []
            })

    def is_loaded(self):
        """
        Returns True if valid calibration is available
        (either explicitly loaded from a file or manually calibrated)
        """
        # Check if loaded flag is True (set when loaded from a file)
        if getattr(self, 'loaded', False):
            return True

        # Check if any sensor has non-default calibration parameters
        for cal in self.calibrations:
            if isinstance(cal, dict):
                # Check if slope or intercept are non-default values
                if cal.get('slope', 1.0) != 1.0 or cal.get('intercept', 0.0) != 0.0:
                    return True
                # Check if there are calibration points
                if len(cal.get('calibration_points', [])) > 0:
                    return True

        # No valid calibration found
        return False