import pygame
import math
import colorsys

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
MAX_LAYERS = 50
LAYER_SPACING_RATIO = 0.9   # High number = tight tunnel, Low number = deep tunnel

# --- COLOR ---
COLOR_SATURATION = 1.0
COLOR_VALUE = 1.0

# ==============================================================================
#                               LOGIC
# ==============================================================================

class ProjectorWild:
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

        # State
        self.running = True
        self.shape_index = 4 # Start with the Astroid (it's cool)
        self.num_layers = 8
        self.thickness = 3
        self.base_rotation = 0.0

        # Color & Twist
        self.hue = 0.0
        self.auto_color = True
        self.color_speed = 0.002
        self.twist = 0.02 # Start with a slight twist for effect

    # --- GEOMETRY GENERATORS ---

    def get_regular_poly(self, sides, radius, rotation):
        """ Standard closed polygons """
        points = []
        step = (2 * math.pi) / sides
        for i in range(sides):
            angle = (step * i) + rotation
            x = self.center[0] + radius * math.cos(angle)
            y = self.center[1] + radius * math.sin(angle)
            points.append((x, y))
        return points

    def get_star_points(self, points_count, radius, rotation):
        """ Spiky stars """
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
        """ A star with curved inward edges (x = cos^3, y = sin^3) """
        points = []
        steps = 40 # Resolution of curve
        for i in range(steps + 1):
            t = (2 * math.pi * i) / steps
            # Parametric equation for Astroid, rotated
            # We apply rotation manually
            raw_x = (math.cos(t) ** 3)
            raw_y = (math.sin(t) ** 3)

            # Rotate 2D
            rx = raw_x * math.cos(rotation) - raw_y * math.sin(rotation)
            ry = raw_x * math.sin(rotation) + raw_y * math.cos(rotation)

            x = self.center[0] + radius * rx
            y = self.center[1] + radius * ry
            points.append((x, y))
        return points

    def get_sine_flower(self, radius, rotation):
        """ A circle that wobbles with a sine wave """
        points = []
        steps = 60
        freq = 6 # How many petals
        amp = 0.15 # How deep the petals are relative to radius

        for i in range(steps + 1):
            theta = (2 * math.pi * i) / steps
            # Radius varies based on angle
            r_dynamic = radius * (1 + amp * math.sin(freq * (theta + rotation*2))) # rotation*2 makes wave spin faster

            angle = theta + rotation
            x = self.center[0] + r_dynamic * math.cos(angle)
            y = self.center[1] + r_dynamic * math.sin(angle)
            points.append((x, y))
        return points

    def draw_triskelion(self, radius, rotation, color, thickness):
        """ 3 curved arms spiraling out """
        arms = 3
        points_per_arm = 15

        for a in range(arms):
            arm_points = []
            base_angle = (2 * math.pi * a) / arms + rotation

            for i in range(points_per_arm):
                # Logic: Go outwards (r) while shifting angle (curvature)
                progress = i / points_per_arm
                r = radius * progress
                # Curvature: The further out, the more we add to angle
                theta = base_angle + (progress * 2.0)

                x = self.center[0] + r * math.cos(theta)
                y = self.center[1] + r * math.sin(theta)
                arm_points.append((x, y))

            if len(arm_points) > 1:
                pygame.draw.lines(self.screen, color, False, arm_points, thickness)

    def draw_brackets(self, radius, rotation, color, thickness):
        """
        Draws the corners of a square, but leaves the sides open.
        Sci-fi HUD look.
        """
        # Calculate the 4 corners of a square
        corners = []
        for i in range(4):
            angle = (math.pi/2 * i) + rotation + (math.pi/4)
            cx = self.center[0] + radius * math.cos(angle)
            cy = self.center[1] + radius * math.sin(angle)
            corners.append((cx, cy))

        # Draw "L" shapes at each corner
        arm_len = radius * 0.25 # Length of the bracket arm

        for i in range(4):
            curr = corners[i]

            # Vector pointing to previous corner (approx)
            prev_angle = (math.pi/2 * (i)) + rotation + (math.pi/4) - (math.pi/2)
            # Vector pointing to next corner
            next_angle = (math.pi/2 * (i)) + rotation + (math.pi/4) + (math.pi/2)

            # Point 1 (Arm one way)
            p1_x = curr[0] + arm_len * math.cos(prev_angle)
            p1_y = curr[1] + arm_len * math.sin(prev_angle)

            # Point 2 (Arm other way)
            p2_x = curr[0] + arm_len * math.cos(next_angle)
            p2_y = curr[1] + arm_len * math.sin(next_angle)

            # Draw the corner as a strip: P1 -> Corner -> P2
            pygame.draw.lines(self.screen, color, False, [(p1_x, p1_y), curr, (p2_x, p2_y)], thickness)


    # --- INPUT & UPDATE ---

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.running = False
                if event.key == pygame.K_SPACE: self.base_rotation = 0

                # SHAPES
                keys_map = {
                    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3,
                    pygame.K_5: 4, pygame.K_6: 5, pygame.K_7: 6, pygame.K_8: 7,
                    pygame.K_9: 8, pygame.K_0: 9
                }
                if event.key in keys_map:
                    self.shape_index = keys_map[event.key]

                # LAYERS
                if event.key == pygame.K_q: self.num_layers = max(1, self.num_layers - 1)
                if event.key == pygame.K_w: self.num_layers = min(MAX_LAYERS, self.num_layers + 1)

                # THICKNESS
                if event.key == pygame.K_a: self.thickness = max(1, self.thickness - 1)
                if event.key == pygame.K_s: self.thickness = min(40, self.thickness + 1)

                if event.key == pygame.K_c: self.auto_color = not self.auto_color

        # CONTINUOUS KEYS
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: self.twist -= 0.002
        if keys[pygame.K_RIGHT]: self.twist += 0.002
        if keys[pygame.K_UP]: self.color_speed += 0.0002
        if keys[pygame.K_DOWN]: self.color_speed = max(0, self.color_speed - 0.0002)

    def update_vars(self):
        mx, my = pygame.mouse.get_pos()

        # SIZE (Mouse X)
        nx = mx / self.w
        max_r = (self.h / 2) * 0.95
        self.current_radius = max_r * (0.02 + (0.98 * nx))

        # ROTATION (Mouse Y)
        ny = (my / self.h) - 0.5
        self.base_rotation += ny * ROTATION_MAX_SPEED

        # COLOR
        if self.auto_color:
            self.hue += self.color_speed
            if self.hue > 1.0: self.hue -= 1.0

        r, g, b = colorsys.hsv_to_rgb(self.hue, COLOR_SATURATION, COLOR_VALUE)
        self.current_rgb = (int(r*255), int(g*255), int(b*255))

    def draw_scene(self):
        self.screen.fill(BG_COLOR)

        # Loop for layers (Tunnel effect)
        for i in range(self.num_layers):
            # Determine scale and rotation for this specific layer
            scale = math.pow(LAYER_SPACING_RATIO, i)
            r = self.current_radius * scale
            rot = self.base_rotation + (i * self.twist)

            if r < 2: break

            # -- DRAW DISPATCH --
            idx = self.shape_index

            # 1. Triangle
            if idx == 0:
                pts = self.get_regular_poly(3, r, rot - math.pi/6)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 2. Square
            elif idx == 1:
                pts = self.get_regular_poly(4, r, rot + math.pi/4)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 3. Pentagon
            elif idx == 2:
                pts = self.get_regular_poly(5, r, rot - math.pi/2)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 4. THE ASTROID (Curved Diamond)
            elif idx == 3:
                pts = self.get_astroid_points(r, rot)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 5. THE FLOWER (Sine Wave Circle)
            elif idx == 4:
                pts = self.get_sine_flower(r, rot)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 6. Circle
            elif idx == 5:
                pygame.draw.circle(self.screen, self.current_rgb, self.center, r, self.thickness)

            # 7. Star 5
            elif idx == 6:
                pts = self.get_star_points(5, r, rot)
                pygame.draw.lines(self.screen, self.current_rgb, True, pts, self.thickness)

            # 8. Star David
            elif idx == 7:
                p1 = self.get_regular_poly(3, r, rot - math.pi/6)
                p2 = self.get_regular_poly(3, r, rot - math.pi/6 + math.pi)
                pygame.draw.lines(self.screen, self.current_rgb, True, p1, self.thickness)
                pygame.draw.lines(self.screen, self.current_rgb, True, p2, self.thickness)

            # 9. THE TRISKELION (Galaxy Spiral)
            elif idx == 8:
                self.draw_triskelion(r, rot, self.current_rgb, self.thickness)

            # 0. THE BRACKETS (Sci-Fi Corners)
            elif idx == 9:
                self.draw_brackets(r, rot, self.current_rgb, self.thickness)

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_input()
            self.update_vars()
            self.draw_scene()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    ProjectorWild().run()
