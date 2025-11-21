 
import pygame
import math
import colorsys

# --- CONFIGURATION ---
FULLSCREEN = True          # Set to False for testing in windowed mode
background_color = (0, 0, 0)
FPS = 60                   # Locked FPS for smoothness

# Interaction Multipliers
MAX_SIZE_RATIO = 0.95      # Max size relative to screen height
ROTATION_SENSITIVITY = 0.1 # How fast mouse Y affects rotation

# --- SHAPE DEFINITIONS ---
class GeometryEngine:
    def __init__(self, center_x, center_y):
        self.cx = center_x
        self.cy = center_y
        self.time_ticker = 0

    def get_polygon_points(self, sides, radius, rotation_offset_rads):
        """ Generates (x,y) coordinates for a regular polygon """
        points = []
        for i in range(sides):
            angle = (2 * math.pi * i / sides) + rotation_offset_rads
            x = self.cx + radius * math.cos(angle)
            y = self.cy + radius * math.sin(angle)
            points.append((x, y))
        return points

    def draw_shape(self, surface, mode, radius, rotation, color, thickness):
        """
        Dispatches drawing based on mode.
        Modes: 0=Square, 1=Triangle, 2=Tunnel (Nested), 3=Star of David, 4=Hexagon
        """

        # MODE 0: Single Square
        if mode == 0:
            points = self.get_polygon_points(4, radius, rotation)
            pygame.draw.lines(surface, color, True, points, thickness)

        # MODE 1: Single Triangle
        elif mode == 1:
            # Offset rotation by -90 deg (pi/2) so triangle points up
            points = self.get_polygon_points(3, radius, rotation - (math.pi/2))
            pygame.draw.lines(surface, color, True, points, thickness)

        # MODE 2: Tunnel (10 squares nested)
        elif mode == 2:
            count = 10
            for i in range(count):
                # Determine step size. Using non-linear math creates a 'depth' effect
                step_radius = radius * ((count - i) / count)
                # Optional: twist inner shapes slightly for a vortex effect
                step_rot = rotation + (i * 0.05)
                points = self.get_polygon_points(4, step_radius, step_rot)
                pygame.draw.lines(surface, color, True, points, thickness)

        # MODE 3: Star of David (Two Triangles)
        elif mode == 3:
            # Triangle 1 (Point up)
            p1 = self.get_polygon_points(3, radius, rotation - (math.pi/2))
            pygame.draw.lines(surface, color, True, p1, thickness)
            # Triangle 2 (Point down - rotated 180 deg / pi radians)
            p2 = self.get_polygon_points(3, radius, rotation - (math.pi/2) + math.pi)
            pygame.draw.lines(surface, color, True, p2, thickness)

        # MODE 4: Octagon (Circle-ish)
        elif mode == 4:
            points = self.get_polygon_points(8, radius, rotation)
            pygame.draw.lines(surface, color, True, points, thickness)

        # MODE 5: The "Portal" (Nested Circles/Polygons with shifting colors)
        elif mode == 5:
            count = 12
            for i in range(count):
                step_radius = radius * ((count - i) / count)
                # Alternate shapes
                sides = 3 if i % 2 == 0 else 3
                rot_mod = math.pi if i % 2 == 0 else 0
                points = self.get_polygon_points(3, step_radius, -rotation + rot_mod)
                pygame.draw.lines(surface, color, True, points, thickness)


def main():
    pygame.init()

    # Setup Screen
    if FULLSCREEN:
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h
        screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False) # Hide cursor for projection
    else:
        w, h = 800, 600
        screen = pygame.display.set_mode((w, h))

    clock = pygame.time.Clock()
    engine = GeometryEngine(w // 2, h // 2)

    # State Variables
    running = True
    current_shape_mode = 2  # Start with nested squares

    # Dynamic Parameters
    base_rotation = 0.0
    hue = 0.0
    color_cycling = True

    # Configurable static thickness (or mapped to mouse if desired)
    line_thickness = 5

    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Number keys switch shapes
                if event.key == pygame.K_1: current_shape_mode = 0
                if event.key == pygame.K_2: current_shape_mode = 1
                if event.key == pygame.K_3: current_shape_mode = 2
                if event.key == pygame.K_4: current_shape_mode = 3
                if event.key == pygame.K_5: current_shape_mode = 4
                if event.key == pygame.K_6: current_shape_mode = 5
                # C toggles color cycling
                if event.key == pygame.K_c: color_cycling = not color_cycling
                # Spacebar resets rotation
                if event.key == pygame.K_SPACE: base_rotation = 0

        # 2. Inputs & Math Mapping
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Normalize Mouse X (0.0 to 1.0) -> Controls SIZE
        norm_x = mouse_x / w
        # Smooth clamp to ensure it doesn't vanish or go offscreen
        target_radius = (h / 2) * MAX_SIZE_RATIO * (0.1 + (0.9 * norm_x))

        # Normalize Mouse Y (0.0 to 1.0) -> Controls ROTATION SPEED
        # Center of screen is 0 speed. Up is left spin, Down is right spin.
        norm_y = (mouse_y / h) - 0.5
        rotation_speed = norm_y * ROTATION_SENSITIVITY

        # Apply Rotation
        base_rotation += rotation_speed

        # 3. Color Calculation
        final_color = (255, 255, 255) # Default White

        if color_cycling:
            # Increment hue slowly, but maybe modify speed based on mouse too?
            # Let's keep hue cycle constant for smooth visuals
            hue += 0.002
            if hue > 1.0: hue -= 1.0

            # Convert HSV to RGB (0-255)
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            final_color = (int(r * 255), int(g * 255), int(b * 255))

        # Optional: Map line thickness to mouse X (larger shape = thicker lines)
        # line_thickness = max(1, int(10 * norm_x))

        # 4. Rendering
        screen.fill(background_color)

        engine.draw_shape(
            surface=screen,
            mode=current_shape_mode,
            radius=target_radius,
            rotation=base_rotation,
            color=final_color,
            thickness=line_thickness
        )

        pygame.display.flip()

        # 5. Timing
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
