import os
import json
import requests
import textwrap


# --- Configuration & Constants ---
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

CONFIG_PATH = "config.json"
OUTPUT_PATH = "image.svg"
MAX_LANGUAGES = 6


LANGUAGE_COLORS = {
    "Rust": "#dea584",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
    "Python": "#3572A5",
    "Haskell": "#5e5086",
    "Prolog": "#74283c",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Ruby": "#701516",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Elixir": "#6e4a7e",
}

FALLBACK_COLOR = "#8b949e"


# --- Layout Grid Definitions ---
CANVAS_WIDTH = 800
CANVAS_PAD = 25
PANEL_GAP = 15
ROW2_PANEL_W = (CANVAS_WIDTH - PANEL_GAP) // 2


QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    login
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
    ) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        primaryLanguage {
          name
        }
      }
    }
  }
}
"""


def fetch_project_stats(token: str) -> dict[str, int]:
    """Fetch public, non-fork repositories owned by GITHUB_USERNAME and count primary languages."""
    if not GITHUB_USERNAME:
        print("[ERROR] GITHUB_USERNAME environment variable is not set.")
        return {}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    stats: dict[str, int] = {}
    has_next_page = True
    cursor = None
    page = 1

    while has_next_page:
        variables = {
            "login": GITHUB_USERNAME,
            "cursor": cursor,
        }

        try:
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                json={"query": QUERY, "variables": variables},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[ERROR] GitHub API request failed: {exc}")
            if "response" in locals():
                print(response.text)
            return stats
        except ValueError:
            print("[ERROR] GitHub API returned invalid JSON.")
            print(response.text)
            return stats

        if "errors" in data:
            print("[ERROR] GitHub GraphQL request failed:")
            for error in data["errors"]:
                print(f"  - {error.get('type')}: {error.get('message')}")
            return stats

        user_data = data.get("data", {}).get("user")
        if not user_data:
            print("[ERROR] GitHub did not return user data.")
            print(data)
            return stats

        repo_data = user_data["repositories"]

        if page == 1:
            print(
                f"[DEBUG] Querying public repositories for '{user_data['login']}': "
                f"{repo_data['totalCount']} total"
            )

        for repo in repo_data["nodes"]:
            primary_language = repo.get("primaryLanguage")
            if primary_language and primary_language.get("name"):
                language = primary_language["name"]
                stats[language] = stats.get(language, 0) + 1

        has_next_page = repo_data["pageInfo"]["hasNextPage"]
        cursor = repo_data["pageInfo"]["endCursor"]
        page += 1

    print(f"[DEBUG] Language statistics: {stats}")
    return stats


def generate_panel_bg(width: int, height: int) -> str:
    return (
        f'    <rect width="{width}" height="{height}" rx="15" ry="15" '
        f'fill="#171717" stroke="#3ED9C9" stroke-width="3" '
        f'filter="url(#soft-shadow)" class="animated-border"/>'
    )


def build_profile_panel(data: dict, x: int, y: int, panel_width: int) -> tuple[str, int]:
    title = data["title"]
    raw_description = " ".join(data["description"])
    wrapped_description = textwrap.wrap(raw_description, width=95)

    height = 80 + len(wrapped_description) * 26 + 10

    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_width, height))
    svg.append(
        f'    <text x="35" y="40" fill="#E2E8F0" '
        f'font-family="system-ui, sans-serif" font-size="22" '
        f'font-weight="bold">{title}</text>'
    )

    svg.append(
        f'    <text x="35" y="80" fill="#94A3B8" '
        f'font-family="system-ui, sans-serif" font-size="16">'
    )

    for index, line in enumerate(wrapped_description):
        dy = "0" if index == 0 else "26"
        svg.append(f'      <tspan x="35" dy="{dy}">{line}</tspan>')

    svg.append("    </text>")
    svg.append("  </g>")

    return "\n".join(svg), height


def calc_skills_panel_height(items: list[dict], panel_width: int) -> int:
    """Calculate the height required by the skill-chip wrapping logic."""
    current_x = 35
    current_y = 70

    for item in items:
        item_width = item.get("width", 80)

        if current_x + item_width > panel_width - 35:
            current_x = 35
            current_y += 45

        current_x += item_width + 15

    return current_y + 30 + 25


def build_skills_panel(
    data: dict,
    x: int,
    y: int,
    panel_width: int,
    fixed_height: int,
) -> str:
    title = data["title"]
    items = data["items"]

    current_x = 35
    current_y = 70
    elements = []

    for item in items:
        item_width = item.get("width", 80)

        if current_x + item_width > panel_width - 35:
            current_x = 35
            current_y += 45

        elements.append(
            f'''    <g transform="translate({current_x}, {current_y})">
      <rect width="{item_width}" height="30" rx="15" fill="#1E1E1E" stroke="{item["color"]}" stroke-width="2"/>
      <text x="{item_width / 2}" y="16" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{item["name"]}</text>
    </g>'''
        )

        current_x += item_width + 15

    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_width, fixed_height))
    svg.append(
        f'    <text x="35" y="40" fill="#E2E8F0" '
        f'font-family="system-ui, sans-serif" font-size="22" '
        f'font-weight="bold">{title}</text>'
    )
    svg.extend(elements)
    svg.append("  </g>")

    return "\n".join(svg)


def build_horizontal_percentages(
    stats: dict[str, int],
    x: int,
    y: int,
    panel_width: int,
) -> tuple[str, int]:
    """Generate a proportional, animated, stacked horizontal language bar."""
    height = 140

    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_width, height))

    if not stats:
        svg.append(
            '    <text x="40" y="80" fill="#94A3B8" '
            'font-family="system-ui, sans-serif" font-size="16">'
            "No public repository language data available."
            "</text>"
        )
        svg.append("  </g>")
        return "\n".join(svg), height

    all_languages = sorted(
        stats.items(),
        key=lambda item: (-item[1], item[0]),
    )
    total_repositories = sum(count for _, count in all_languages)

    if total_repositories == 0:
        svg.append("  </g>")
        return "\n".join(svg), height

    if len(all_languages) > MAX_LANGUAGES:
        top_languages = all_languages[: MAX_LANGUAGES - 1]
        remaining_count = sum(
            count for _, count in all_languages[MAX_LANGUAGES - 1 :]
        )
        processed_languages = top_languages + [("Others", remaining_count)]
    else:
        processed_languages = all_languages

    bar_area_padding = 40
    total_bar_width = panel_width - bar_area_padding * 2
    gap_size = 4
    language_count = len(processed_languages)
    usable_width = total_bar_width - gap_size * (language_count - 1)

    svg.append(f'    <g transform="translate({bar_area_padding}, 40)">')

    current_x = 0

    for index, (language, count) in enumerate(processed_languages):
        percentage = count / total_repositories * 100
        color = LANGUAGE_COLORS.get(language, FALLBACK_COLOR)

        if index == language_count - 1:
            segment_width = total_bar_width - current_x
        else:
            segment_width = int(percentage / 100 * usable_width)

        midpoint_x = current_x + segment_width / 2
        animation_delay = index * 0.15
        text_delay = animation_delay + 0.3

        svg.append(
            f'''      <rect x="{midpoint_x}" y="0" width="0" height="12" rx="6" fill="{color}">
        <animate attributeName="width" from="0" to="{segment_width}" dur="0.6s" begin="{animation_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
        <animate attributeName="x" from="{midpoint_x}" to="{current_x}" dur="0.6s" begin="{animation_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
      </rect>
      <text x="{midpoint_x}" y="35" fill="{color}" font-family="system-ui, sans-serif" font-size="15" font-weight="bold" text-anchor="middle" dominant-baseline="middle" opacity="0">
        {language}
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>
      <text x="{midpoint_x}" y="55" fill="{color}" font-family="system-ui, sans-serif" font-size="13" font-weight="normal" text-anchor="middle" dominant-baseline="middle" opacity="0">
        {percentage:.1f}%
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>'''
        )

        current_x += segment_width + gap_size

    svg.append("    </g>")
    svg.append("  </g>")

    return "\n".join(svg), height


def main() -> None:
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise SystemExit(
            "[ERROR] GITHUB_TOKEN environment variable is not set."
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = json.load(file)

    project_stats = fetch_project_stats(token)
    components = []
    current_y = CANVAS_PAD

    # Row 1: Profile panel
    # profile_svg, profile_height = build_profile_panel(
    #     config["profile"], CANVAS_PAD, current_y, CANVAS_WIDTH
    # )
    # components.append(profile_svg)
    # current_y += profile_height + PANEL_GAP

    # Row 2: Skills panels
    language_items = config["skill_columns"][0]["items"]
    technology_items = config["skill_columns"][1]["items"]

    language_technology_difference = 50

    language_panel_width = ROW2_PANEL_W + language_technology_difference
    technology_panel_width = ROW2_PANEL_W - language_technology_difference

    language_required_height = calc_skills_panel_height(
        language_items,
        language_panel_width,
    )
    technology_required_height = calc_skills_panel_height(
        technology_items,
        technology_panel_width,
    )
    row_2_height = max(language_required_height, technology_required_height)

    language_svg = build_skills_panel(
        config["skill_columns"][0],
        CANVAS_PAD,
        current_y,
        language_panel_width,
        row_2_height,
    )

    technology_svg = build_skills_panel(
        config["skill_columns"][1],
        CANVAS_PAD + ROW2_PANEL_W + PANEL_GAP + language_technology_difference,
        current_y,
        technology_panel_width,
        row_2_height,
    )

    components.extend([language_svg, technology_svg])
    current_y += row_2_height + PANEL_GAP

    # Row 3: Language statistics panel
    statistics_svg, statistics_height = build_horizontal_percentages(
        project_stats,
        CANVAS_PAD,
        current_y,
        CANVAS_WIDTH,
    )
    components.append(statistics_svg)
    current_y += statistics_height + CANVAS_PAD

    total_width = CANVAS_WIDTH + CANVAS_PAD * 2
    total_height = current_y

    final_svg = f'''<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <!-- 1. Gradient defined FIRST to prevent parsing cascades -->
        <linearGradient id="maven-gradle-grad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#C71A36" /> 
        <stop offset="100%" stop-color="#1DC9B7" /> 
        </linearGradient>

        <!-- 2. Shadow rebuilt using universally supported primitives -->
        <filter id="soft-shadow" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="10" result="blur"/>
        <feOffset dx="0" dy="8" result="offsetBlur"/>
        <feFlood flood-color="#000000" flood-opacity="0.6" result="shadowColor"/>
        <feComposite in="shadowColor" in2="offsetBlur" operator="in" result="shadow"/>
        <feMerge>
            <feMergeNode in="shadow"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
        </filter>
    </defs>
    <style>
        .animated-border {{ stroke-dasharray: 20, 10; animation: dash-flow 2s linear infinite; }}
        @keyframes dash-flow {{ from {{ stroke-dashoffset: 30; }} to {{ stroke-dashoffset: 0; }} }}
    </style>

    {chr(10).join(components)}
    </svg>'''

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        file.write(final_svg)

    print(f"[INFO] Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()