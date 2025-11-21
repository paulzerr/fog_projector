import pygame
import math
import colorsys

# ==============================================================================
#                               CONFIGURATION
# ==============================================================================

# --- DISPLAY SETTINGS ---
FULLSCREEN = True           # Set to False for testing in a window
WINDOW_W, WINDOW_H = 1000, 800 # Only used if FULLSCREEN is False
BG_COLOR = (0, 0, 0)        # Black background is best for projection
FPS = 60                    # Smooth framerate

# --- MOUSE MAPPING SETTINGS ---
# How fast the shape spins when mouse is at top/bottom of screen
# Lower number = Slower maximum rotation speed
ROTATION_MAX_SPEED = 0.05
# How sensitive the mouse X axis is for zooming
ZOOM_SENSITIVITY = 1.0

# --- SHAPE DEFAULTS ---
DEFAULT_THICKNESS = 4       # Starting line thickness
DEFAULT_LAYERS = 1          # Starting number of nested shapes
DEFAULT_SHAPE_INDEX = 1     # Starting shape (0-9)
MAX_LAYERS = 50             # Limit to prevent crashing
LAYER_SPACING_RATIO = 0.85  # 1.0 = all stacked, 0.1 = tiny tunnel.
                            # (This represents how big the inner shape is vs outer)

# --- COLOR SETTINGS ---
COLOR_CYCLE_SPEED_BASE = 0.002 # How fast colors fade automatically
COLOR_SATURATION = 1.0
COLOR_VALUE = 1.0

# --- GEOMETRY TWEAKS ---
# Adds a slight rotation to inner layers for a "Vortex" effect
# Set to 0.0 for straight tunnels, 0.1 for twisting tunnels
LAYER_TWIST_FACTOR = 0.0

# ==============================================================================
#                               LOGIC
# ==============================================================================

class ProjectorVisuals:
    def __init__(self):
        pygame.init()

        # Display Setup
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

        # State Variables
        self.running = True
        self.shape_index = DEFAULT_SHAPE_INDEX # 0 to 9
        self.num_layers = DEFAULT_LAYERS
        self.thickness = DEFAULT_THICKNESS
        self.base_rotation = 0.0

        # Color State
        self.hue = 0.0
        self.auto_color = True
        self.color_speed = COLOR_CYCLE_SPEED_BASE

        # Twist State (controlled by Arrows)
        self.twist = LAYER_TWIST_FACTOR

    def get_poly_points(self, sides, radius, rotation, star_mode=False):
        """
        Generates points for polygons.
        If star_mode is True, it generates a star by alternating radii.
        """
        points = []
        step = (2 * math.pi) / sides

        if star_mode:
            # Double the steps for inner and outer vertices
            star_sides = sides * 2
            step = (2 * math.pi) / star_sides
            for i in range(star_sides):
                # Alternate between full radius and half radius
                r = radius if i % 2 == 0 else radius * 0.4
                angle = (step * i) + rotation
                x = self.center[0] + r * math.cos(angle)
                y = self.center[1] + r * math.sin(angle)
                points.append((x, y))
        else:
            # Regular Polygon
            for i in range(sides):
                angle = (step * i) + rotation
                x = self.center[0] + radius * math.cos(angle)
                y = self.center[1] + radius * math.sin(angle)
                points.append((x, y))

        return points

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.running = False
                if event.key == pygame.K_SPACE: self.base_rotation = 0

                # --- SHAPE SELECTION (1-0) ---
                if event.key == pygame.K_1: self.shape_index = 0 # Triangle
                if event.key == pygame.K_2: self.shape_index = 1 # Square
                if event.key == pygame.K_3: self.shape_index = 2 # Pentagon
                if event.key == pygame.K_4: self.shape_index = 3 # Hexagon
                if event.key == pygame.K_5: self.shape_index = 4 # Octagon
                if event.key == pygame.K_6: self.shape_index = 5 # Circle (30-gon)
                if event.key == pygame.K_7: self.shape_index = 6 # Star 5-point
                if event.key == pygame.K_8: self.shape_index = 7 # Star 6-point (David)
                if event.key == pygame.K_9: self.shape_index = 8 # Diamond
                if event.key == pygame.K_0: self.shape_index = 9 # X-Shape

                # --- LAYERING (Q/W) ---
                if event.key == pygame.K_q:
                    self.num_layers = max(1, self.num_layers - 1)
                if event.key == pygame.K_w:
                    self.num_layers = min(MAX_LAYERS, self.num_layers + 1)

                # --- THICKNESS (A/S) ---
                if event.key == pygame.K_a:
                    self.thickness = max(1, self.thickness - 1)
                if event.key == pygame.K_s:
                    self.thickness = min(50, self.thickness + 1)

                # --- COLOR MODE ---
                if event.key == pygame.K_c:
                    self.auto_color = not self.auto_color

        # --- ARROW KEYS (Continuous hold) ---
        keys = pygame.key.get_pressed()

        # LEFT/RIGHT: Adjust Twist (Vortex effect)
        if keys[pygame.K_LEFT]:
            self.twist -= 0.005
        if keys[pygame.K_RIGHT]:
            self.twist += 0.005

        # UP/DOWN: Adjust Color Cycle Speed
        if keys[pygame.K_UP]:
            self.color_speed += 0.0001
        if keys[pygame.K_DOWN]:
            self.color_speed = max(0, self.color_speed - 0.0001)

    def update_parameters(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # 1. Radius (Mapped to Mouse X)
        # Normalize 0 to 1
        norm_x = mouse_x / self.w
        # Max radius is 90% of half screen height
        max_r = (self.h / 2) * 0.95
        # Base radius calculation
        self.current_radius = max_r * (0.05 + (0.95 * norm_x))

        # 2. Rotation (Mapped to Mouse Y)
        # Center screen = 0 speed. Top = fast left, Bottom = fast right.
        norm_y = (mouse_y / self.h) - 0.5
        # Apply config limiter
        rot_speed = norm_y * ROTATION_MAX_SPEED
        self.base_rotation += rot_speed

        # 3. Color Calculation
        if self.auto_color:
            self.hue += self.color_speed
            if self.hue > 1.0: self.hue -= 1.0

        r, g, b = colorsys.hsv_to_rgb(self.hue, COLOR_SATURATION, COLOR_VALUE)
        self.current_rgb = (int(r*255), int(g*255), int(b*255))

    def draw_shape_by_index(self, idx, radius, rotation, thickness):
        """ Switch to determine which math to use based on index """
        # 0: Triangle
        if idx == 0:
            pts = self.get_poly_points(3, radius, rotation - math.pi/6)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 1: Square
        elif idx == 1:
            pts = self.get_poly_points(4, radius, rotation + math.pi/4)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 2: Pentagon
        elif idx == 2:
            pts = self.get_poly_points(5, radius, rotation - math.pi/2)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 3: Hexagon
        elif idx == 3:
            pts = self.get_poly_points(6, radius, rotation)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 4: Octagon
        elif idx == 4:
            pts = self.get_poly_points(8, radius, rotation + math.pi/8)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 5: Circle (30 sides is smooth enough)
        elif idx == 5:
            pts = self.get_poly_points(30, radius, rotation)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 6: 5-Point Star
        elif idx == 6:
            pts = self.get_poly_points(5, radius, rotation - math.pi/2, star_mode=True)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 7: Star of David (Two Triangles)
        elif idx == 7:
            # Triangle 1
            p1 = self.get_poly_points(3, radius, rotation - math.pi/6)
            pygame.draw.lines(self.screen, self.current_rgb, True, p1, thickness)
            # Triangle 2 (Rotated 180)
            p2 = self.get_poly_points(3, radius, rotation - math.pi/6 + math.pi)
            pygame.draw.lines(self.screen, self.current_rgb, True, p2, thickness)

        # 8: Diamond
        elif idx == 8:
            pts = self.get_poly_points(4, radius, rotation)
            pygame.draw.lines(self.screen, self.current_rgb, True, pts, thickness)

        # 9: The X (Two crossed lines, slightly fancy)
        elif idx == 9:
            # Line 1
            l = radius
            x1 = self.center[0] + l * math.cos(rotation + math.pi/4)
            y1 = self.center[1] + l * math.sin(rotation + math.pi/4)
            x2 = self.center[0] + l * math.cos(rotation + 5*math.pi/4)
            y2 = self.center[1] + l * math.sin(rotation + 5*math.pi/4)
            pygame.draw.line(self.screen, self.current_rgb, (x1,y1), (x2,y2), thickness)
            # Line 2
            x3 = self.center[0] + l * math.cos(rotation + 3*math.pi/4)
            y3 = self.center[1] + l * math.sin(rotation + 3*math.pi/4)
            x4 = self.center[0] + l * math.cos(rotation + 7*math.pi/4)
            y4 = self.center[1] + l * math.sin(rotation + 7*math.pi/4)
            pygame.draw.line(self.screen, self.current_rgb, (x3,y3), (x4,y4), thickness)


    def run(self):
        print("--- PROJECTOR PRO CONTROLS ---")
        print("MOUSE X     : Zoom / Size")
        print("MOUSE Y     : Rotation Speed")
        print("KEYS 1-0    : Change Base Shape")
        print("Q / W       : Remove / Add nested layers (Tunnel depth)")
        print("A / S       : Thinner / Thicker Lines")
        print("ARROWS L/R  : Twist Tunnel (Vortex Effect)")
        print("ARROWS U/D  : Change Color Cycle Speed")
        print("C           : Toggle Color Cycling")
        print("SPACE       : Reset Rotation")
        print("ESC         : Quit")

        while self.running:
            self.handle_input()
            self.update_parameters()

            self.screen.fill(BG_COLOR)

            # Draw Loops (Nesting)
            # We draw from outside in, or inside out?
            # Inside out (smallest first) usually handles overwrite better,
            # but for lines it doesn't matter much.

            for i in range(self.num_layers):
                # Calculate layer specific variables

                # Decreasing radius for inner layers
                # Formula: r = r_max * (ratio ^ i) gives exponential tunnel look
                # Formula: r = r_max - (i * gap) gives linear look
                # Let's use linear ratio for cleaner geometric look

                scale = math.pow(LAYER_SPACING_RATIO, i)
                layer_radius = self.current_radius * scale

                # Stop drawing if shape is too small
                if layer_radius < 2: break

                # Apply twist offset
                layer_rotation = self.base_rotation + (i * self.twist)

                self.draw_shape_by_index(
                    self.shape_index,
                    layer_radius,
                    layer_rotation,
                    self.thickness
                )

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    app = ProjectorVisuals()
    app.run()
