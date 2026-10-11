"""Author complete indexed-color superkick poses; no source sprite pixels used.

Coordinates describe a right-facing wrestler with a fixed planted foot. The
native SNES palette supplies colors; each silhouette is drawn from joint and
outline geometry rather than rotating or cutting stock game artwork.
"""

import math
from PIL import Image, ImageDraw

# Shoulder, hip, kicking knee/ankle, supporting knee, guard hand, rear hand.
POSES = [
    ((-1, -24), (0, 0), (10, 13), (13, 32), (-3, 20), (13, -21), (-10, -9)),
    ((-8, -24), (0, 0), (18, -17), (9, -2), (-2, 20), (8, -22), (-20, -12)),
    ((-22, -14), (0, 0), (18, -18), (32, -27), (-2, 20), (-5, -15), (-34, -7)),
    ((-23, -14), (0, 0), (18, -18), (33, -27), (-2, 20), (-7, -13), (-35, -6)),
    ((-17, -20), (0, 0), (18, -16), (13, -4), (-2, 20), (0, -20), (-29, -10)),
    ((-9, -25), (0, 0), (12, -6), (17, 12), (-2, 20), (8, -23), (-22, -11)),
    ((-3, -26), (0, 0), (9, 12), (13, 30), (-2, 20), (13, -24), (-15, -10)),
    ((0, -26), (0, 0), (9, 19), (14, 34), (-2, 20), (14, -23), (-12, -10)),
]


def pose(index):
    image = Image.new("P", (96, 96), 0)
    draw = ImageDraw.Draw(image)
    origin = (44, 49)

    def p(point):
        return tuple(round(a + b) for a, b in zip(origin, point))

    def poly(points, color):
        draw.polygon([p(q) for q in points], fill=color)

    def segment(a, b, width, color, highlight):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        poly(
            [
                (a[0] + nx, a[1] + ny),
                (b[0] + nx, b[1] + ny),
                (b[0] - nx, b[1] - ny),
                (a[0] - nx, a[1] - ny),
            ],
            1,
        )
        draw.line([p(a), p(b)], fill=color, width=max(1, width - 2))
        draw.line(
            [p((a[0] - 1, a[1] - 1)), p((b[0] - 1, b[1] - 1))],
            fill=highlight,
            width=max(1, width // 3),
        )
        for q in [a, b]:
            x, y = p(q)
            rr = (width - 2) // 2
            draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color)

    shoulder, hip, knee, ankle, support, hand, rear = POSES[index]
    # Rear arm sits behind torso; complete limbs overlap at every joint.
    elbow = ((shoulder[0] + rear[0]) / 2 - 3, (shoulder[1] + rear[1]) / 2 + 5)
    segment(shoulder, elbow, 7, 7, 11)
    segment(elbow, rear, 5, 11, 15)
    # Supporting leg stays connected to the fixed sole throughout the sequence.
    segment((-3, 0), support, 10, 2, 3)
    segment(support, (-1, 32), 8, 2, 3)
    poly([(-6, 27), (3, 27), (4, 36), (9, 39), (9, 41), (-6, 41)], 1)
    poly([(-5, 28), (2, 28), (2, 36), (7, 39), (-5, 39)], 6)
    poly([(-3, 28), (1, 28), (1, 37), (5, 39), (-3, 38)], 8)
    # Side-on torso and hips, deliberately drawn for each pose.
    s = shoulder
    h = hip
    poly(
        [
            (s[0] - 5, s[1] - 3),
            (s[0] + 5, s[1] - 4),
            (h[0] + 7, -2),
            (h[0] + 5, 6),
            (h[0] - 6, 5),
            (s[0] - 6, s[1] + 7),
        ],
        1,
    )
    poly(
        [
            (s[0] - 4, s[1] - 2),
            (s[0] + 4, s[1] - 3),
            (h[0] + 5, -3),
            (h[0] + 3, 3),
            (h[0] - 4, 3),
            (s[0] - 4, s[1] + 6),
        ],
        7,
    )
    poly([(s[0], s[1] - 2), (s[0] + 4, s[1] - 2), (h[0] + 5, -4), (h[0], -2)], 11)
    draw.line([p((s[0] + 2, s[1])), p((h[0] + 2, -5))], fill=15, width=2)
    poly([(-6, -2), (6, -2), (7, 7), (-5, 7)], 2)
    poly([(-3, -1), (5, -1), (5, 6), (-2, 6)], 3)
    # Front leg is solid from hip to knee to boot, including flexed poses.
    segment((3, 2), knee, 10, 2, 3)
    segment(knee, ankle, 8, 2, 3)
    # Boot follows the shin axis; the sole faces the opponent at extension.
    dx, dy = ankle[0] - knee[0], ankle[1] - knee[1]
    ll = math.hypot(dx, dy)
    ux, uy = dx / ll, dy / ll
    nx, ny = -uy, ux

    def boot(t, n):
        return (ankle[0] + ux * t + nx * n, ankle[1] + uy * t + ny * n)

    poly(
        [boot(-9, -4), boot(-9, 4), boot(3, 4), boot(6, 8), boot(8, 8), boot(8, -4)], 1
    )
    poly([boot(-8, -3), boot(-8, 3), boot(4, 3), boot(6, 6), boot(6, -3)], 6)
    poly([boot(-7, -2), boot(-7, 1), boot(4, 1), boot(5, 4), boot(5, -2)], 8)
    for t in (-5, -2, 1):
        draw.line([p(boot(t, -2)), p(boot(t, 2))], fill=1)
    # Red tights highlights and dark kneepad remain attached to the drawn leg.
    draw.line([p((4, 2)), p((knee[0] + 1, knee[1]))], fill=3, width=2)
    x, y = p(knee)
    draw.ellipse((x - 4, y - 3, x + 4, y + 3), fill=1)
    # Neck and profile head are drawn upright even while the torso leans away.
    head = (shoulder[0] + 1, shoulder[1] - 10)
    segment(shoulder, (head[0], head[1] + 5), 5, 7, 11)
    hx, hy = head
    poly(
        [
            (hx - 5, hy - 5),
            (hx + 2, hy - 6),
            (hx + 5, hy - 2),
            (hx + 5, hy + 1),
            (hx + 7, hy + 2),
            (hx + 4, hy + 3),
            (hx + 3, hy + 7),
            (hx - 3, hy + 6),
            (hx - 5, hy + 1),
        ],
        9,
    )
    poly(
        [
            (hx, hy - 4),
            (hx + 3, hy - 3),
            (hx + 3, hy),
            (hx + 5, hy + 2),
            (hx + 3, hy + 3),
            (hx + 2, hy + 6),
            (hx - 1, hy + 5),
            (hx - 2, hy),
        ],
        11,
    )
    draw.line([p((hx + 1, hy - 2)), p((hx + 2, hy))], fill=15)
    draw.point(p((hx + 3, hy)), fill=1)
    poly(
        [
            (hx - 5, hy - 4),
            (hx - 2, hy - 6),
            (hx + 1, hy - 5),
            (hx - 1, hy - 2),
            (hx - 2, hy + 4),
            (hx - 3, hy + 10),
            (hx - 7, hy + 7),
            (hx - 5, hy + 1),
        ],
        10,
    )
    draw.line([p((hx - 3, hy - 4)), p((hx - 4, hy + 7))], fill=13, width=2)
    draw.line([p((hx - 1, hy - 4)), p((hx - 2, hy + 4))], fill=14)
    # Guard arm and hand complete the front silhouette.
    elbow = ((shoulder[0] + hand[0]) / 2 + 3, (shoulder[1] + hand[1]) / 2 + 7)
    segment((shoulder[0] + 3, shoulder[1] + 2), elbow, 7, 7, 11)
    segment(elbow, hand, 5, 11, 15)
    x, y = p(hand)
    draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=15)
    return image
