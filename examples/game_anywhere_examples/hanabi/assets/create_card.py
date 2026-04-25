import math
import random

from PIL import Image, ImageDraw

# --- Config ---
WIDTH, HEIGHT = 512, 768
BACKGROUND = (10, 20, 60)  # dark blue

COLOR_MAP = {
    "white": (240, 240, 240),
    "yellow": (255, 220, 50),
    "red": (220, 50, 50),
    "green": (50, 200, 100),
    "blue": (80, 140, 255),
}

# --- Shape drawing functions ---


def draw_filled(draw, x, y, size, color):
    draw.ellipse((x - size, y - size, x + size, y + size), fill=color)


def draw_outline(draw, x, y, size, color):
    draw.ellipse((x - size, y - size, x + size, y + size), outline=color, width=3)


def draw_cross(draw, x, y, size, color):
    draw.line((x - size, y, x + size, y), fill=color, width=3)
    draw.line((x, y - size, x, y + size), fill=color, width=3)


def draw_star(draw, x, y, size, color):
    points = []
    for i in range(5):
        angle = i * 72 - 90
        outer_x = x + size * 1.0 * math.cos(math.radians(angle))
        outer_y = y + size * 1.0 * math.sin(math.radians(angle))
        inner_angle = angle + 36
        inner_x = x + size * 0.5 * math.cos(math.radians(inner_angle))
        inner_y = y + size * 0.5 * math.sin(math.radians(inner_angle))
        points.extend([(outer_x, outer_y), (inner_x, inner_y)])
    draw.polygon(points, fill=color)


def draw_ring(draw, x, y, size, color):
    draw.ellipse((x - size, y - size, x + size, y + size), outline=color, width=6)


# Map color → style
STYLE_MAP = {
    "white": draw_outline,
    "yellow": draw_star,
    "red": draw_filled,
    "green": draw_cross,
    "blue": draw_ring,
}

# --- Main ---


def main():
    for color_name, color in COLOR_MAP.items():
        for number in range(1, 5 + 1):
            draw_func = STYLE_MAP[color_name]

            # Create image
            img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
            draw = ImageDraw.Draw(img)

            # Draw N shapes
            for _ in range(number):
                size = random.randint(20, 60)
                x = random.randint(size, WIDTH - size)
                y = random.randint(size, HEIGHT - size)

                draw_func(draw, x, y, size, color)

            # Save image
            filename = f"cards/{color_name}_{number}.png"
            img.save(filename)
            print(f"Saved {filename}")


if __name__ == "__main__":
    main()
