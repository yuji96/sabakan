import hashlib
from pathlib import Path

import plt
from colorutils import Color


def name2color(name):
    return "#" + hashlib.sha256(name.encode()).hexdigest()[:6]


# ------- debug ------------------------


def check_color(names):
    _, ax = plt.subplots(figsize=(5, len(names) * 0.7))
    data = []
    for i, name in enumerate(names):
        color = Color(hex=name2color(name))
        data.append(
            {
                "color": color.hex,
                "string": "black" if color.yiq[0] > 0.5 else "white",
                "hue": color.hsv[0],
                "name": name,
            }
        )
    for i, item in enumerate(sorted(data, key=lambda x: x["hue"])):
        ax.barh(i, 1, color=item["color"], edgecolor="none")
        ax.text(
            0.5,
            i,
            f'{item["name"]}: {item["color"]}',
            ha="center",
            va="center",
            color=item["string"],
            fontsize=14,
        )

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])

    # Show the plot
    plt.tight_layout()
    plt.savefig("sample/tmp.png")


if __name__ == "__main__":
    names = Path("./sample/users.txt").read_text().splitlines()
    check_color(names)
