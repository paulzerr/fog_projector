import pygame
import math
import colorsys
import random
import time

# ==============================================================================
#                               CONFIGURATION
# ==============================================================================

# --- DISPLAY ---
FULLSCREEN = True
WINDOW_W, WINDOW_H = 1000, 800
BG_COLOR = (0, 0, 0)
FPS = 60

# --- CONTROL SENSITIVITY ---
ROTATION_MAX_SPEED = 0.04
MAX_LAYERS = 60
LAYER_SPACING_RATIO = 0.92

# ==============================================================================
#                               LOGIC
# ==============================================================================

class ProjectorV2:
    def __init__(self):
        pygame.init()
        if FULLSCREEN:
            info = pygame.display.Info()
            self.w, self.h = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((self.w, self.h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
            pygame.mouse.set_visible(False)
        else:
            self.w, self.h = WINDOW_W, WINDOW_H
            self.screen = pygame.display.set_mode((self.w, self.h))

        self.clock = pygame.time.Clock()
        self.center = (self.w // 2, self.h // 2)
        
        # Surface for trails/blur effect
        self.trail_surface = pygame.Surface((self.w, self.h), pygame.SRCALPHA)

        # --- STATE ---
        self.running = True
        self.start_time = time.time()
        
        # Core Parameters
        self.shape_index = 0
        self.num_layers = 16
        self.thickness = 3
        self.base_rotation = 0.0
        self.twist = 0.02
        self.current_radius = 300
        
        # Color State
        self.hue = 0.0
        self.color_speed = 0.002
        
        # --- TOGGLES & MODES ---
        # Controlled by z, x, c, v, b, n, m
        self.features = {
            'parallax': False,      # z: Layers drift independently
            'breathing': False,     # x: Radius pulses
            'color_mode': 0,        # c: 0=Solid, 1=Dual, 2=Rainbow, 3=Fog
            'motion_mode': 0,       # v: 0=Normal, 1=Orbit, 2=Swarm, 3=Pulse, 4=Strobe
            'trails': False,        # b: Echo trails (no clear)
            'physics': 0,           # n: 0=None, 1=Vortex, 2=Magnetic
            'chaos': False,         # m: Random noise/glitch
            'show_hud': False       # i: Toggle HUD
        }
        
        # Internal state for features
        self.orbit_angle = 0.0
        self.pulse_phase = 0.0
        self.magnetic_points = []
        self.swarm_offsets = [(0,0)] * MAX_LAYERS
        self.noise_seeds = [random.random() * 100 for _ in range(MAX_LAYERS)]

        # --- DYNAMIC PARAMETERS ---
        self.last_toggled = 'color_mode' # Default to color speed control
        
        self.params = {
            'parallax': {'val': 20.0, 'step': 1.0, 'min': 0.0, 'max': 100.0, 'label': 'Amp'},
            'breathing': {'val': 2.0, 'step': 0.1, 'min': 0.1, 'max': 10.0, 'label': 'Spd'},
            'color_mode': {'val': 0.002, 'step': 0.0002, 'min': 0.0, 'max': 0.05, 'label': 'Spd'},
            'motion_mode': {'val': 1.0, 'step': 0.1, 'min': 0.0, 'max': 5.0, 'label': 'Spd'},
            'trails': {'val': 20, 'step': 5, 'min': 0, 'max': 255, 'label': 'Alpha'},
            'physics': {'val': 0.01, 'step': 0.001, 'min': 0.0, 'max': 0.1, 'label': 'Str'},
            'chaos': {'val': 0.1, 'step': 0.01, 'min': 0.0, 'max': 1.0, 'label': 'Amt'}
        }

        # --- WAYPOINTS ---
        self.waypoints = []
        self.current_waypoint_idx = -1
        
        # --- INPUT COOLDOWN ---
        self.last_input_time = 0
        self.input_cooldown = 0.05 # 50ms

        # Shape Registry
        self.shapes = [
            "Triangle", "Square", "Pentagon", "Astroid", "SineFlower", 
            "Circle", "Star5", "StarDavid", "Triskelion", "Brackets",
            "Lissajous", "Hypotrochoid", "NoiseRing", "Calligraphy"
        ]

    # --- GEOMETRY GENERATORS ---

    def get_regular_poly(self, sides, radius, rotation):
        points = []
        step = (2 * math.pi) / sides
        for i in range(sides):
            angle = (step * i) + rotation
            x = self.center[0] + radius * math.cos(angle)
            y = self.center[1] + radius * math.sin(angle)
            points.append((x, y))
        return points

    def get_star_points(self, points_count, radius, rotation):
        points = []
        step = (2 * math.pi) / (points_count * 2)
        for i in range(points_count * 2):
            r = radius if i % 2 == 0 else radius * 0.4
            angle = (step * i) + rotation - (math.pi/2)
            x = self.center[0] + r * math.cos(angle)
            y = self.center[1] + r * math.sin(angle)
            points.append((x, y))
        return points

    def get_astroid_points(self, radius, rotation):
        points = []
        steps = 40
        for i in range(steps + 1):
            t = (2 * math.pi * i) / steps
            raw_x = (math.cos(t) ** 3)
            raw_y = (math.sin(t) ** 3)
            rx = raw_x * math.cos(rotation) - raw_y * math.sin(rotation)
            ry = raw_x * math.sin(rotation) + raw_y * math.cos(rotation)
            x = self.center[0] + radius * rx
            y = self.center[1] + radius * ry
            points.append((x, y))
        return points

    def get_sine_flower(self, radius, rotation):
        points = []
        steps = 60
        freq = 6
        amp = 0.15
        for i in range(steps + 1):
            theta = (2 * math.pi * i) / steps
            r_dynamic = radius * (1 + amp * math.sin(freq * (theta + rotation*2)))
            angle = theta + rotation
            x = self.center[0] + r_dynamic * math.cos(angle)
            y = self.center[1] + r_dynamic * math.sin(angle)
            points.append((x, y))
        return points

    def get_lissajous(self, radius, rotation, layer_idx):
        points = []
        steps = 60
        # Parameters change slightly per layer for morphing effect
        a = 3
        b = 2
        delta = rotation + (layer_idx * 0.1)
        
        for i in range(steps + 1):
            t = (2 * math.pi * i) / steps
            # Lissajous parametric
            raw_x = math.sin(a * t + delta)
            raw_y = math.sin(b * t)
            
            # Rotate
            rx = raw_x * math.cos(rotation) - raw_y * math.sin(rotation)
            ry = raw_x * math.sin(rotation) + raw_y * math.cos(rotation)
            
            x = self.center[0] + radius * rx
            y = self.center[1] + radius * ry
            points.append((x, y))
        return points

    def get_hypotrochoid(self, radius, rotation):
        points = []
        steps = 100
        R = radius # Fixed circle
        r = radius * 0.3 # Rolling circle
        d = radius * 0.5 # Distance from center of rolling circle
        
        for i in range(steps + 1):
            t = (4 * math.pi * i) / steps
            # Hypotrochoid equations
            raw_x = (R - r) * math.cos(t) + d * math.cos(((R - r) / r) * t)
            raw_y = (R - r) * math.sin(t) - d * math.sin(((R - r) / r) * t)
            
            # Normalize to approx radius 1 for scaling
            scale_factor = 1.0 / (R + d) if (R+d) != 0 else 1
            raw_x *= scale_factor * radius * 1.5
            raw_y *= scale_factor * radius * 1.5

            # Rotate
            rx = raw_x * math.cos(rotation) - raw_y * math.sin(rotation)
            ry = raw_x * math.sin(rotation) + raw_y * math.cos(rotation)
            
            x = self.center[0] + rx
            y = self.center[1] + ry
            points.append((x, y))
        return points

    def get_noise_ring(self, radius, rotation, layer_idx):
        points = []
        steps = 40
        seed = self.noise_seeds[layer_idx % len(self.noise_seeds)]
        time_offset = time.time() * 2
        
        for i in range(steps + 1):
            angle = (2 * math.pi * i) / steps
            # Simple pseudo-noise using sin combinations
            noise = math.sin(angle * 5 + time_offset + seed) * math.cos(angle * 3 - seed)
            r_dynamic = radius * (1 + 0.2 * noise)
            
            final_angle = angle + rotation
            x = self.center[0] + r_dynamic * math.cos(final_angle)
            y = self.center[1] + r_dynamic * math.sin(final_angle)
            points.append((x, y))
        return points

    # --- DRAWING HELPERS ---

    def draw_triskelion(self, radius, rotation, color, thickness):
        arms = 3
        points_per_arm = 15
        for a in range(arms):
            arm_points = []
            base_angle = (2 * math.pi * a) / arms + rotation
            for i in range(points_per_arm):
                progress = i / points_per_arm
                r = radius * progress
                theta = base_angle + (progress * 2.0)
                x = self.center[0] + r * math.cos(theta)
                y = self.center[1] + r * math.sin(theta)
                arm_points.append((x, y))
            if len(arm_points) > 1:
                pygame.draw.lines(self.screen, color, False, arm_points, thickness)

    def draw_brackets(self, radius, rotation, color, thickness):
        corners = []
        for i in range(4):
            angle = (math.pi/2 * i) + rotation + (math.pi/4)
            cx = self.center[0] + radius * math.cos(angle)
            cy = self.center[1] + radius * math.sin(angle)
            corners.append((cx, cy))
        
        arm_len = radius * 0.25
        for i in range(4):
            curr = corners[i]
            prev_angle = (math.pi/2 * i) + rotation + (math.pi/4) - (math.pi/2)
            next_angle = (math.pi/2 * i) + rotation + (math.pi/4) + (math.pi/2)
            
            p1_x = curr[0] + arm_len * math.cos(prev_angle)
            p1_y = curr[1] + arm_len * math.sin(prev_angle)
            p2_x = curr[0] + arm_len * math.cos(next_angle)
            p2_y = curr[1] + arm_len * math.sin(next_angle)
            
            pygame.draw.lines(self.screen, color, False, [(p1_x, p1_y), curr, (p2_x, p2_y)], thickness)

    def draw_calligraphy(self, radius, rotation, color, thickness):
        # Expanding strokes: Draw arcs with varying thickness
        rect = pygame.Rect(self.center[0] - radius, self.center[1] - radius, radius*2, radius*2)
        start_angle = rotation
        end_angle = rotation + math.pi * 1.5
        # Pygame arc angles are in radians? No, documentation says radians.
        # Actually pygame.draw.arc uses bounding rect and start/stop angles in radians.
        # But it doesn't support float thickness well or varying thickness.
        # Let's simulate with polygons.
        
        points = []
        steps = 20
        for i in range(steps):
            t = i / steps
            angle = start_angle + t * (math.pi * 1.5)
            # Width varies
            w = thickness * (1 + math.sin(t * math.pi)) 
            
            x = self.center[0] + radius * math.cos(angle)
            y = self.center[1] + radius * math.sin(angle)
            # Just drawing circles for now to simulate brush tip
            pygame.draw.circle(self.screen, color, (int(x), int(y)), int(w/2))

    # --- PHYSICS & TRANSFORMS ---

    def apply_physics(self, points, layer_idx):
        mode = self.features['physics']
        if mode == 0: return points
        
        new_points = []
        for x, y in points:
            dx = x - self.center[0]
            dy = y - self.center[1]
            dist = math.sqrt(dx*dx + dy*dy)
            angle = math.atan2(dy, dx)
            
            # 1. Vortex
            if mode == 1:
                twist_amt = dist * self.params['physics']['val']
                angle += twist_amt
                nx = self.center[0] + dist * math.cos(angle)
                ny = self.center[1] + dist * math.sin(angle)
                new_points.append((nx, ny))
                
            # 2. Magnetic (Attractor)
            elif mode == 2:
                # Create a virtual attractor moving in a figure 8
                t = time.time()
                ax = self.center[0] + math.cos(t) * 300
                ay = self.center[1] + math.sin(t*2) * 200
                
                adx = x - ax
                ady = y - ay
                adist = math.sqrt(adx*adx + ady*ady)
                
                # Pull towards attractor
                if adist < 200:
                    pull = (200 - adist) / 200
                    x -= adx * pull * 0.5
                    y -= ady * pull * 0.5
                new_points.append((x, y))
                
        return new_points

    # --- INPUT & UPDATE ---

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.running = False
                if event.key == pygame.K_SPACE: self.base_rotation = 0

                # --- SHAPE CYCLING ---
                if event.key == pygame.K_MINUS:
                    self.shape_index = (self.shape_index - 1) % len(self.shapes)
                if event.key == pygame.K_EQUALS:
                    self.shape_index = (self.shape_index + 1) % len(self.shapes)

                # --- TOGGLES ---
                if event.key == pygame.K_z:
                    self.features['parallax'] = not self.features['parallax']
                    self.last_toggled = 'parallax'
                if event.key == pygame.K_x:
                    self.features['breathing'] = not self.features['breathing']
                    self.last_toggled = 'breathing'
                if event.key == pygame.K_c:
                    self.features['color_mode'] = (self.features['color_mode'] + 1) % 4
                    self.last_toggled = 'color_mode'
                if event.key == pygame.K_v:
                    self.features['motion_mode'] = (self.features['motion_mode'] + 1) % 5
                    self.last_toggled = 'motion_mode'
                if event.key == pygame.K_b:
                    self.features['trails'] = not self.features['trails']
                    self.last_toggled = 'trails'
                if event.key == pygame.K_n:
                    self.features['physics'] = (self.features['physics'] + 1) % 3
                    self.last_toggled = 'physics'
                if event.key == pygame.K_m:
                    self.features['chaos'] = not self.features['chaos']
                    self.last_toggled = 'chaos'
                if event.key == pygame.K_i: self.features['show_hud'] = not self.features['show_hud']

                # --- WAYPOINTS ---
                # J: Save NEW waypoint
                if event.key == pygame.K_j:
                    self.waypoints.append(self.get_state())
                    self.current_waypoint_idx = len(self.waypoints) - 1
                
                # H: Update CURRENT waypoint
                if event.key == pygame.K_h:
                    if self.waypoints and self.current_waypoint_idx >= 0:
                        self.waypoints[self.current_waypoint_idx] = self.get_state()
                
                # K: Previous Waypoint
                if event.key == pygame.K_k:
                    if self.waypoints:
                        self.current_waypoint_idx = (self.current_waypoint_idx - 1) % len(self.waypoints)
                        self.set_state(self.waypoints[self.current_waypoint_idx])
                
                # L: Next Waypoint
                if event.key == pygame.K_l:
                    if self.waypoints:
                        self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
                        self.set_state(self.waypoints[self.current_waypoint_idx])
                
                # G: Delete LAST waypoint
                if event.key == pygame.K_g:
                    if self.waypoints:
                        self.waypoints.pop()
                        self.current_waypoint_idx = len(self.waypoints) - 1
                        if self.current_waypoint_idx >= 0:
                            self.set_state(self.waypoints[self.current_waypoint_idx])

                # --- PRESETS ---
                if event.key == pygame.K_1: self.load_preset("Cathedral")
                if event.key == pygame.K_2: self.load_preset("Galactic")
                if event.key == pygame.K_3: self.load_preset("Jelly")
                if event.key == pygame.K_4: self.load_preset("Crystal")
                if event.key == pygame.K_5: self.load_preset("Default")

                # LAYERS
                if event.key == pygame.K_q: self.num_layers = max(1, self.num_layers - 1)
                if event.key == pygame.K_w: self.num_layers = min(MAX_LAYERS, self.num_layers + 1)

                # THICKNESS
                if event.key == pygame.K_a: self.thickness = max(1, self.thickness - 1)
                if event.key == pygame.K_s: self.thickness = min(40, self.thickness + 1)

        # CONTINUOUS KEYS (Throttled)
        now = time.time()
        if now - self.last_input_time > self.input_cooldown:
            keys = pygame.key.get_pressed()
            input_processed = False
            
            if keys[pygame.K_LEFT]:
                self.twist -= 0.002
                input_processed = True
            if keys[pygame.K_RIGHT]:
                self.twist += 0.002
                input_processed = True
            if keys[pygame.K_UP]:
                p = self.params[self.last_toggled]
                p['val'] = min(p['max'], p['val'] + p['step'])
                input_processed = True
            if keys[pygame.K_DOWN]:
                p = self.params[self.last_toggled]
                p['val'] = max(p['min'], p['val'] - p['step'])
                input_processed = True
            
            if input_processed:
                self.last_input_time = now

    def load_preset(self, name):
        if name == "Cathedral":
            self.shape_index = 9 # Brackets
            self.features['color_mode'] = 3 # Fog
            self.features['motion_mode'] = 0
            self.features['physics'] = 0
            self.twist = 0.0
            self.num_layers = 20
            self.hue = 0.1 # Gold-ish
            
        elif name == "Galactic":
            self.shape_index = 8 # Triskelion
            self.features['motion_mode'] = 1 # Orbit
            self.features['physics'] = 1 # Vortex
            self.features['trails'] = True
            self.twist = 0.1
            self.num_layers = 15
            
        elif name == "Jelly":
            self.shape_index = 4 # SineFlower
            self.features['breathing'] = True
            self.features['color_mode'] = 2 # Rainbow
            self.features['motion_mode'] = 3 # Pulse
            self.twist = 0.01
            self.num_layers = 12
            
        elif name == "Crystal":
            self.shape_index = 3 # Astroid
            self.features['parallax'] = True
            self.features['color_mode'] = 1 # Dual
            self.twist = 0.05
            self.num_layers = 25
            
        elif name == "Default":
            self.shape_index = 0
            self.features = {k: False for k in self.features}
            self.features['color_mode'] = 0
            self.features['motion_mode'] = 0
            self.features['physics'] = 0
            self.twist = 0.02
            self.num_layers = 16

    def get_state(self):
        # Deep copy of params is needed because it contains dicts
        import copy
        return {
            'shape_index': self.shape_index,
            'num_layers': self.num_layers,
            'thickness': self.thickness,
            'twist': self.twist,
            'features': self.features.copy(),
            'params': copy.deepcopy(self.params),
            'hue': self.hue
        }

    def set_state(self, state):
        self.shape_index = state['shape_index']
        self.num_layers = state['num_layers']
        self.thickness = state['thickness']
        self.twist = state['twist']
        self.features = state['features'].copy()
        
        # Restore params carefully
        import copy
        self.params = copy.deepcopy(state['params'])
        self.hue = state['hue']

    def update_vars(self):
        mx, my = pygame.mouse.get_pos()
        t = time.time()

        # SIZE (Mouse X)
        nx = mx / self.w
        max_r = (self.h / 2) * 0.95
        target_radius = max_r * (0.02 + (0.98 * nx))
        
        # Breathing Effect
        if self.features['breathing']:
            target_radius *= (1.0 + 0.2 * math.sin(t * self.params['breathing']['val']))
            
        self.current_radius = target_radius

        # ROTATION (Mouse Y)
        ny = (my / self.h) - 0.5
        self.base_rotation += ny * ROTATION_MAX_SPEED
        
        # Chaos Knob
        if self.features['chaos']:
            val = self.params['chaos']['val']
            self.base_rotation += (random.random() - 0.5) * val
            self.current_radius *= (1.0 - val + random.random() * (val*2))

        # COLOR
        self.hue += self.params['color_mode']['val']
        if self.hue > 1.0: self.hue -= 1.0
        
        # Motion Modes Update
        m_speed = self.params['motion_mode']['val']
        if self.features['motion_mode'] == 1: # Orbit
            self.orbit_angle += 0.01 * m_speed
        elif self.features['motion_mode'] == 2: # Swarm
            for i in range(MAX_LAYERS):
                # Browninan-ish motion
                ox, oy = self.swarm_offsets[i]
                ox += (random.random() - 0.5) * 2
                oy += (random.random() - 0.5) * 2
                # Dampen
                ox *= 0.95
                oy *= 0.95
                self.swarm_offsets[i] = (ox, oy)

    def get_layer_color(self, i, total_layers):
        mode = self.features['color_mode']
        
        # Base Color
        h = self.hue
        s = 1.0
        v = 1.0
        
        # 1. Dual Color
        if mode == 1:
            if i % 2 == 0:
                h = (h + 0.5) % 1.0
        
        # 2. Rainbow / Hue Waves
        elif mode == 2:
            h = (h + (i * 0.05)) % 1.0
            
        # 3. Fog (Depth Fade)
        elif mode == 3:
            # Core is white/desaturated, edges are colored
            # Or: Far layers dim
            depth_factor = 1.0 - (i / total_layers)
            v = depth_factor
            s = depth_factor
            
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r*255), int(g*255), int(b*255))

    def draw_scene(self):
        # Trails vs Clear
        if self.features['trails']:
            # Draw semi-transparent black rect to fade old frames
            fade_surface = pygame.Surface((self.w, self.h))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(int(self.params['trails']['val'])) # Adjust for trail length
            self.screen.blit(fade_surface, (0,0))
        else:
            self.screen.fill(BG_COLOR)

        # Loop for layers (Tunnel effect)
        for i in range(self.num_layers):
            # Determine scale and rotation for this specific layer
            scale = math.pow(LAYER_SPACING_RATIO, i)
            r = self.current_radius * scale
            
            # Parallax Drift & Z-Push
            cx, cy = self.center
            if self.features['parallax']:
                # Layers drift based on depth
                amp = self.params['parallax']['val']
                drift_x = math.sin(time.time() * 0.5 + i * 0.2) * amp * (i/self.num_layers)
                drift_y = math.cos(time.time() * 0.3 + i * 0.2) * amp * (i/self.num_layers)
                cx += drift_x
                cy += drift_y
                
                # Z-Push (Oscillate depth/spacing)
                z_push = 1.0 + 0.05 * math.sin(time.time() * 0.5)
                # Re-calculate radius with pushed spacing
                scale = math.pow(LAYER_SPACING_RATIO * z_push, i)
                r = self.current_radius * scale
                
            # Orbit Mode
            if self.features['motion_mode'] == 1:
                orbit_r = 50 * (i / self.num_layers)
                cx += math.cos(self.orbit_angle + i*0.1) * orbit_r
                cy += math.sin(self.orbit_angle + i*0.1) * orbit_r
                
            # Swarm Mode
            if self.features['motion_mode'] == 2:
                ox, oy = self.swarm_offsets[i]
                cx += ox
                cy += oy

            # Pulse Mode (Radius modulation per layer)
            if self.features['motion_mode'] == 3:
                r *= (1.0 + 0.1 * math.sin(time.time() * 2 + i * 0.5))

            # Strobe Mode (Skip layers)
            if self.features['motion_mode'] == 4:
                # Blink layers in a sequence
                strobe_speed = 15 # Hz approx
                t_idx = int(time.time() * strobe_speed)
                if (i + t_idx) % 3 != 0:
                    continue

            # Rotation
            rot = self.base_rotation + (i * self.twist)
            
            # Phase Shift (Temporal)
            # rot += math.sin(time.time() + i) * 0.1

            if r < 2: break
            
            # Color
            color = self.get_layer_color(i, self.num_layers)

            # -- DRAW DISPATCH --
            # Temporarily override center for drawing methods
            original_center = self.center
            self.center = (cx, cy)
            
            idx = self.shape_index
            shape_name = self.shapes[idx]
            
            pts = []
            
            if shape_name == "Triangle":
                pts = self.get_regular_poly(3, r, rot - math.pi/6)
            elif shape_name == "Square":
                pts = self.get_regular_poly(4, r, rot + math.pi/4)
            elif shape_name == "Pentagon":
                pts = self.get_regular_poly(5, r, rot - math.pi/2)
            elif shape_name == "Astroid":
                pts = self.get_astroid_points(r, rot)
            elif shape_name == "SineFlower":
                pts = self.get_sine_flower(r, rot)
            elif shape_name == "Circle":
                pygame.draw.circle(self.screen, color, (int(cx), int(cy)), int(r), self.thickness)
            elif shape_name == "Star5":
                pts = self.get_star_points(5, r, rot)
            elif shape_name == "StarDavid":
                p1 = self.get_regular_poly(3, r, rot - math.pi/6)
                p2 = self.get_regular_poly(3, r, rot - math.pi/6 + math.pi)
                # Apply physics to both
                p1 = self.apply_physics(p1, i)
                p2 = self.apply_physics(p2, i)
                pygame.draw.lines(self.screen, color, True, p1, self.thickness)
                pygame.draw.lines(self.screen, color, True, p2, self.thickness)
            elif shape_name == "Triskelion":
                self.draw_triskelion(r, rot, color, self.thickness)
            elif shape_name == "Brackets":
                self.draw_brackets(r, rot, color, self.thickness)
            elif shape_name == "Lissajous":
                pts = self.get_lissajous(r, rot, i)
            elif shape_name == "Hypotrochoid":
                pts = self.get_hypotrochoid(r, rot)
            elif shape_name == "NoiseRing":
                pts = self.get_noise_ring(r, rot, i)
            elif shape_name == "Calligraphy":
                self.draw_calligraphy(r, rot, color, self.thickness)

            # Draw points if generated
            if pts:
                pts = self.apply_physics(pts, i)
                if len(pts) > 1:
                    pygame.draw.lines(self.screen, color, True, pts, self.thickness)

            # Restore center
            self.center = original_center

        # UI / HUD (Optional, to show active modes)
        if self.features['show_hud']:
            self.draw_hud()

        pygame.display.flip()

    def draw_hud(self):
        # Detailed HUD
        font = pygame.font.SysFont("Arial", 24, bold=True)
        y = 20
        x = 20
        line_height = 30
        
        # Helper to format boolean/modes
        def on_off(val): return "ON" if val else "OFF"
        
        color_modes = ["Solid", "Dual", "Rainbow", "Fog"]
        motion_modes = ["Normal", "Orbit", "Swarm", "Pulse", "Strobe"]
        physics_modes = ["None", "Vortex", "Magnetic"]
        
        texts = [
            f"[-/+] Shape: {self.shapes[self.shape_index]}",
            f"[Q/W] Layers: {self.num_layers}",
            f"[A/S] Thickness: {self.thickness}",
            f"[L/R Arrows] Twist: {self.twist:.3f}",
            f"[U/D Arrows] Adjusting: {self.last_toggled.upper()} ({self.params[self.last_toggled]['label']})",
            "",
            f"[Z] Parallax: {on_off(self.features['parallax'])} | Amp: {self.params['parallax']['val']:.1f}",
            f"[X] Breathing: {on_off(self.features['breathing'])} | Spd: {self.params['breathing']['val']:.1f}",
            f"[C] Color Mode: {color_modes[self.features['color_mode']]} | Spd: {self.params['color_mode']['val']:.4f}",
            f"[V] Motion Mode: {motion_modes[self.features['motion_mode']]} | Spd: {self.params['motion_mode']['val']:.1f}",
            f"[B] Trails: {on_off(self.features['trails'])} | Alpha: {self.params['trails']['val']}",
            f"[N] Physics: {physics_modes[self.features['physics']]} | Str: {self.params['physics']['val']:.3f}",
            f"[M] Chaos: {on_off(self.features['chaos'])} | Amt: {self.params['chaos']['val']:.2f}",
            "",
            "[1-5] Presets: Cathedral, Galactic, Jelly, Crystal, Default",
            "",
            f"Waypoints: {len(self.waypoints)} | Curr: {self.current_waypoint_idx + 1 if self.waypoints else '-'}",
            "[J] New | [H] Update | [K/L] Prev/Next | [G] Del Last"
        ]
        
        # Draw semi-transparent background
        bg_rect = pygame.Rect(10, 10, 500, len(texts) * line_height + 20)
        s = pygame.Surface((bg_rect.w, bg_rect.h))
        s.set_alpha(180)
        s.fill((0,0,0))
        self.screen.blit(s, (10,10))
        
        for t in texts:
            if t == "":
                y += line_height // 2
                continue
            surf = font.render(t, True, (255, 255, 255))
            self.screen.blit(surf, (x, y))
            y += line_height

    def run(self):
        while self.running:
            self.handle_input()
            self.update_vars()
            self.draw_scene()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    ProjectorV2().run()