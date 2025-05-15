import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from Cal_Math import CalibrationData  # Import from the existing file


class WeightDistribution(QObject):
    """
    Handles weight distribution calculations including center of mass
    and displacement vectors.
    """
    # Define signals for updates
    geometry_changed = pyqtSignal()
    com_calculated = pyqtSignal(tuple)  # Emits (x, y) of center of mass
    displacement_calculated = pyqtSignal(tuple)  # Emits (dx, dy) of displacement vector
    layout_generated = pyqtSignal(dict)

    def __init__(self, calibration=None):
        """
        Initialize the weight distribution calculator

        Args:
            calibration: Optional CalibrationData instance for applying calibration
        """
        super().__init__()
        self.calibration = calibration

        # Store latest values
        self.sensor_weights = [0.0, 0.0, 0.0, 0.0]  # Calibrated weights
        self.sensor_positions = [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]
        self.ideal_com = (0.0, 0.0)
        self.actual_com = (0.0, 0.0)
        self.displacement = (0.0, 0.0)

        # Debugging
        self.debug = True

        self.optimized_layout = None
        self.tray_optimizer = TrayOptimizer()

    def update_sensor_positions(self, positions):
        """
        Update the sensor positions

        Args:
            positions: List of (x, y) tuples for sensor positions
        """
        print(f"DEBUG [AlgMath] update_sensor_positions called with: {positions}")
        self.sensor_positions = positions

        # Always recalculate COM when positions change, regardless of weight values
        print(f"DEBUG [AlgMath] Calling calculate_com from update_sensor_positions")
        self.calculate_com()

        # Emit signal that geometry has changed
        print(f"DEBUG [AlgMath] Emitting geometry_changed signal")
        self.geometry_changed.emit()

    def update_ideal_com(self, com_pos):
        """
        Update the ideal center of mass position

        Args:
            com_pos: (x, y) tuple of ideal COM position
        """
        self.ideal_com = com_pos
        # Recalculate displacement if we have an actual COM
        if self.actual_com != (0.0, 0.0):
            self.calculate_displacement()

    # 2. WeightDistribution.update_sensor_data() modification
    def update_sensor_data(self, values, tare_values=None, pre_calibrated=False):
        """
        Update with new sensor data and calculate COM

        Args:
            values: List of sensor values (raw or pre-calibrated)
            tare_values: Optional list of tare values to subtract
            pre_calibrated: Flag indicating if values are already calibrated
        """
        print(f"DEBUG [AlgMath] update_sensor_data called with values: {values}")
        print(f"DEBUG [AlgMath] update_sensor_data tare values: {tare_values}")
        print(f"DEBUG [AlgMath] values are pre-calibrated: {pre_calibrated}")

        # Skip if we don't have enough values
        if len(values) < 4:
            if self.debug:
                print(f"Insufficient values: {len(values)}")
            return

        if pre_calibrated:
            # Values are already calibrated, use them directly
            calibrated = values
            print(f"DEBUG [AlgMath] Using pre-calibrated values: {calibrated}")
        else:
            # Apply calibration if available
            if self.calibration:
                # Get calibrated values in grams
                calibrated = self.calibration.apply(values, "g")
                print(f"DEBUG [AlgMath] Raw values calibrated to: {calibrated}")
            else:
                # No calibration, use values as is
                calibrated = values
                print(f"DEBUG [AlgMath] No calibration, using raw values")

        # Apply tare if provided (tare values should be in grams)
        if tare_values and len(tare_values) >= 4:
            self.sensor_weights = [
                max(0, cal - tare) for cal, tare in zip(calibrated, tare_values)
            ]
        else:
            # Make sure all values are positive for weight calculation
            self.sensor_weights = [abs(val) if pre_calibrated else max(0, val) for val in calibrated]

        print(f"DEBUG [AlgMath] Final sensor weights: {self.sensor_weights}")
        print(f"DEBUG [AlgMath] Current sensor positions: {self.sensor_positions}")

        # Calculate center of mass
        print(f"DEBUG [AlgMath] Calling calculate_com from update_sensor_data")
        self.calculate_com()

    def calculate_com(self):
        """
        Calculate center of mass based on current weights and positions
        """
        try:
            print(f"DEBUG [AlgMath] calculate_com called")
            print(f"DEBUG [AlgMath] Current positions: {self.sensor_positions}")
            print(f"DEBUG [AlgMath] Current weights: {self.sensor_weights}")
            print(f"DEBUG [AlgMath] Previous actual_com: {self.actual_com}")

            # Get total weight
            total_weight = sum(self.sensor_weights)
            print(f"DEBUG [AlgMath] Total weight: {total_weight}")

            if total_weight <= 0:
                print(f"DEBUG [AlgMath] Total weight is zero or negative")

                # Use the geometric center of sensors as default COM when no weights
                if len(self.sensor_positions) > 0:
                    x_values = [pos[0] for pos in self.sensor_positions]
                    y_values = [pos[1] for pos in self.sensor_positions]

                    center_x = sum(x_values) / len(x_values)
                    center_y = sum(y_values) / len(y_values)

                    self.actual_com = (center_x, center_y)
                    print(f"DEBUG [AlgMath] Setting COM to geometric center: {self.actual_com}")

                    # Emit signal with new COM
                    print(f"DEBUG [AlgMath] Emitting com_calculated signal with {self.actual_com}")
                    self.com_calculated.emit(self.actual_com)

                    # Calculate displacement from ideal COM
                    self.calculate_displacement()
                return

            # Calculate weighted sum of positions
            weighted_x = sum(weight * pos[0] for weight, pos in zip(self.sensor_weights, self.sensor_positions))
            weighted_y = sum(weight * pos[1] for weight, pos in zip(self.sensor_weights, self.sensor_positions))

            print(f"DEBUG [AlgMath] Weighted sum X: {weighted_x}")
            print(f"DEBUG [AlgMath] Weighted sum Y: {weighted_y}")

            # Calculate center of mass
            com_x = weighted_x / total_weight
            com_y = weighted_y / total_weight

            print(f"DEBUG [AlgMath] Calculated COM: ({com_x:.2f}, {com_y:.2f})")

            # Update actual COM
            self.actual_com = (com_x, com_y)

            # Emit signal with new COM
            print(f"DEBUG [AlgMath] Emitting com_calculated signal with {self.actual_com}")
            self.com_calculated.emit(self.actual_com)

            # Calculate displacement from ideal COM
            self.calculate_displacement()

        except Exception as e:
            print(f"ERROR [AlgMath] Error calculating COM: {str(e)}")
            import traceback
            traceback.print_exc()

    def calculate_displacement(self):
        """
        Calculate displacement vector from ideal to actual COM
        """
        # Calculate displacement vector components
        dx = self.actual_com[0] - self.ideal_com[0]
        dy = self.actual_com[1] - self.ideal_com[1]

        self.displacement = (dx, dy)

        if self.debug:
            print(f"Displacement: ({dx:.2f}, {dy:.2f})")

        # Emit signal with displacement
        self.displacement_calculated.emit(self.displacement)

    def calculate_display_scaling(self, view_width, view_height, margin_percent=10):
        """
        Calculate scaling factors to fit sensor positions and COM in view,
        always filling the available width and expanding height accordingly.
        """
        all_points = self.sensor_positions.copy()
        if self.actual_com != (0.0, 0.0):
            all_points.append(self.actual_com)
        if self.ideal_com != (0.0, 0.0):
            all_points.append(self.ideal_com)

        if not all_points:
            return 1.0, view_width / 2, 0, -1.0, -1.0, 1.0, 1.0

        x_values = [p[0] for p in all_points]
        y_values = [p[1] for p in all_points]

        min_x, max_x = min(x_values), max(x_values)
        min_y, max_y = min(y_values), max(y_values)

        if min_x == max_x:
            min_x -= 1.0
            max_x += 1.0
        if min_y == max_y:
            min_y -= 1.0
            max_y += 1.0

        data_width = max_x - min_x
        data_height = max_y - min_y

        # Add margins
        margin_x = data_width * (margin_percent / 100.0)
        margin_y = data_height * (margin_percent / 100.0)

        min_x -= margin_x
        max_x += margin_x
        min_y -= margin_y
        max_y += margin_y

        data_width = max_x - min_x
        data_height = max_y - min_y

        # Calculate scale based on width only
        scale = view_width / data_width

        # Calculate the required height based on the data height and scale
        required_height = data_height * scale

        # Center vertically within the available height
        offset_x = 0  # Left-aligned
        offset_y = (view_height - required_height) / 2 if view_height > required_height else 0

        return scale, offset_x, offset_y, min_x, min_y, max_x, max_y

    def transform_point(self, point, scale, offset_x, offset_y, min_x, min_y):
        """
        Transform a point from data coordinates to view coordinates

        Args:
            point: (x, y) tuple in data coordinates
            scale, offset_x, offset_y, min_x, min_y: Values from calculate_display_scaling

        Returns:
            tuple: (x, y) in view coordinates
        """
        view_x = offset_x + (point[0] - min_x) * scale
        # Flip y-axis for screen coordinates (origin at top-left)
        view_y = offset_y + (min_y + (min_y - point[1]) * -1) * scale

        return view_x, view_y

    class LayoutWorker(QRunnable):
        def __init__(self, outer, *args, **kwargs):
            super().__init__()
            self.outer = outer
            self.args = args
            self.kwargs = kwargs

        def run(self):
            result = self.outer.tray_optimizer.compute_optimal_tray_layout(*self.args, **self.kwargs)
            self.outer.optimized_layout = result
            self.outer.layout_generated.emit(result)

    def generate_layout(self, sensor_weights, sensor_positions, ideal_com,
                        bias_settings, general_settings, tray_flags,
                        max_weight, max_weight_unit="g", threshold=None):
        worker = self.LayoutWorker(
            self,
            sensor_weights,
            sensor_positions,
            ideal_com,
            bias_settings,
            general_settings,
            tray_flags,
            max_weight,
            max_weight_unit,
            threshold
        )
        QThreadPool.globalInstance().start(worker)


# ========== NEW CLASS: TrayOptimizer ==========
class TrayOptimizer:
    def __init__(self, calibration_helper=None):
        self.calibration_helper = calibration_helper or CalibrationData()
        self.effect_weight_grams = 113  # One tray slot = 113g

    def apply_bias_to_com(self, com, bias):
        return (com[0] + bias.get("x", 0.0), com[1] + bias.get("y", 0.0))

    def convert_to_grams(self, value, from_unit):
        return self.calibration_helper.convert_unit(value, from_unit, "g")

    # 1. Fixed implementation of threshold logic in TrayOptimizer.compute_optimal_tray_layout
    # This addresses the threshold functionality without introducing any crashes

    # This implements only the threshold logic in TrayOptimizer without
    # modifying any visualization code that was working before

    def compute_optimal_tray_layout(self, sensor_weights, sensor_positions, ideal_com,
                                    bias_settings, general_settings, tray_flags,
                                    max_weight, max_weight_unit="g", threshold=None):
        """
        Compute optimal tray layout with threshold functionality and total weight limit
        """
        # Apply bias
        ideal_com = self.apply_bias_to_com(ideal_com, bias_settings)

        # Convert max weight to grams
        max_weight_g = self.convert_to_grams(max_weight, max_weight_unit)

        # Calculate the initial weight from sensors (athlete weight)
        initial_weight = sum(sensor_weights)
        print(f"Initial weight from sensors: {initial_weight}g")

        # Calculate how much additional weight we can add
        available_weight = max_weight_g - initial_weight
        print(f"Available weight for additions: {available_weight}g")

        # If already over the limit, we can't add any weights
        if available_weight <= 0:
            print("Warning: Already at or over weight limit, cannot add weights")
            # Return current state without any additions
            return {
                "front_tray": [],
                "back_tray": [],
                "final_com": self.calculate_com(sensor_weights, sensor_positions),
                "displacement": self.calculate_displacement(
                    self.calculate_com(sensor_weights, sensor_positions),
                    ideal_com
                ),
                "total_weight": initial_weight,
                "effect_map": {"front": [], "back": []}
            }

        # Compute current COM and displacement
        original_com = self.calculate_com(sensor_weights, sensor_positions)
        original_disp = self.calculate_displacement(original_com, ideal_com)

        print(f"Original COM: {original_com}")
        print(f"Original displacement: {original_disp}")
        print(f"Threshold value: {threshold}")

        tray_slots = []
        effect_map = {"front": [], "back": []}
        layout = {"front_tray": [], "back_tray": []}

        # Build slot positions from general settings
        for tray_name in ["front", "back"]:
            if not tray_flags.get(tray_name, False):
                continue

            tray = general_settings[f"weight_tray1" if tray_name == "front" else "weight_tray2"]
            rows = tray["rows"]
            cols = tray["columns"]
            y_center = tray["y_position"]
            cell_w = tray["cell_width"]
            cell_h = tray["cell_height"]
            wall = tray["wall_thickness"]

            x_spacing = cell_w + wall
            y_spacing = cell_h + wall
            center_row = (rows - 1) / 2
            center_col = (cols - 1) / 2

            layout[f"{tray_name}_tray"] = [[0 for _ in range(cols)] for _ in range(rows)]
            effect_map[tray_name] = [[0.0 for _ in range(cols)] for _ in range(rows)]

            for row in range(rows):
                for col in range(cols):
                    dx = (col - center_col) * x_spacing
                    dy = (row - center_row) * y_spacing
                    x = dx
                    y = y_center + dy
                    tray_slots.append({
                        "tray": tray_name,
                        "row": row,
                        "col": col,
                        "x": x,
                        "y": y
                    })

        # Simulate weight placement and compute effect
        candidates = []
        max_improvement = 0

        for slot in tray_slots:
            test_weights = sensor_weights.copy()
            test_positions = sensor_positions.copy()

            test_weights.append(self.effect_weight_grams)
            test_positions.append((slot["x"], slot["y"]))

            test_com = self.calculate_com(test_weights, test_positions)
            new_disp = self.calculate_displacement(test_com, ideal_com)

            improvement = original_disp - new_disp
            percent = improvement / original_disp if original_disp != 0 else 0

            # Track maximum improvement for threshold calculation
            if percent > max_improvement:
                max_improvement = percent

            if percent > 0:
                slot["percent_improvement"] = percent
                candidates.append(slot)

        # Sort candidates by effectiveness
        candidates.sort(key=lambda s: s["percent_improvement"], reverse=True)

        # Apply threshold if specified
        if threshold is not None and threshold > 0 and max_improvement > 0:
            absolute_threshold = max_improvement * threshold
            print(f"Max improvement: {max_improvement}")
            print(f"Absolute threshold: {absolute_threshold}")

            filtered_candidates = [c for c in candidates if c["percent_improvement"] >= absolute_threshold]
            print(f"Filtered {len(candidates) - len(filtered_candidates)} candidates below threshold")

            candidates = filtered_candidates

        # Calculate how many 113g weights we can add within the available weight
        max_additional_weights = int(available_weight / self.effect_weight_grams)
        print(f"Maximum number of additional weights allowed: {max_additional_weights}")

        # Track added weight separately from initial weight
        added_weight = 0
        used_slots = []

        for slot in candidates:
            # Check if adding one more weight would exceed the available weight
            if added_weight + self.effect_weight_grams > available_weight:
                print(f"Weight limit reached after adding {len(used_slots)} weights")
                break

            layout[f"{slot['tray']}_tray"][slot["row"]][slot["col"]] = 1
            effect_map[slot["tray"]][slot["row"]][slot["col"]] = slot["percent_improvement"]
            added_weight += self.effect_weight_grams
            used_slots.append(slot)

        # Normalize effect map
        used_effects = []
        for slot in used_slots:
            tray = slot['tray']
            row = slot['row']
            col = slot['col']
            effect_value = effect_map[tray][row][col]
            used_effects.append(effect_value)

        if used_effects:
            max_effect = max(used_effects)

            # Only normalize used slots
            for slot in used_slots:
                tray = slot['tray']
                row = slot['row']
                col = slot['col']
                if effect_map[tray][row][col] > 0:
                    effect_map[tray][row][col] /= max_effect

        # Calculate final COM with added weights
        final_weights = sensor_weights.copy()
        final_positions = sensor_positions.copy()

        for slot in used_slots:
            final_weights.append(self.effect_weight_grams)
            final_positions.append((slot["x"], slot["y"]))

        final_com = self.calculate_com(final_weights, final_positions)
        final_disp = self.calculate_displacement(final_com, ideal_com)

        # Calculate the total weight (initial + added)
        total_weight = initial_weight + added_weight
        print(f"Final total weight: {total_weight}g")

        return {
            "front_tray": layout["front_tray"],
            "back_tray": layout["back_tray"],
            "final_com": final_com,
            "displacement": final_disp,
            "total_weight": total_weight,
            "effect_map": effect_map
        }

    # The original methods from TrayOptimizer that we need to use
    def calculate_com(self, weights, positions):
        total = sum(weights)
        if total == 0:
            return (0.0, 0.0)
        x = sum(w * pos[0] for w, pos in zip(weights, positions)) / total
        y = sum(w * pos[1] for w, pos in zip(weights, positions)) / total
        return (x, y)

    def calculate_displacement(self, actual, ideal):
        dx = actual[0] - ideal[0]
        dy = actual[1] - ideal[1]
        return (dx ** 2 + dy ** 2) ** 0.5