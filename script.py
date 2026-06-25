import os
import json
import requests
import textwrap

# --- Configuration & Constants ---
URL = "https://api.github.com/graphql"
TOKEN = os.getenv("GH_TOKEN")
CONFIG_PATH = "config.json"
MAX_LANGUAGES = 6

LANGUAGE_COLORS = {
    "Rust": "#dea584", "C++": "#f34b7d", "C": "#555555",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Python": "#3572A5",
    "Haskell": "#5e5086", "Prolog": "#74283c", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Go": "#00ADD8", "Shell": "#89e051",
    "HTML": "#e34c26", "CSS": "#563d7c", "Ruby": "#701516",
    "C#": "#178600", "PHP": "#4F5D95", "Swift": "#F05138",
    "Elixir": "#6e4a7e"
}
FALLBACK_COLOR = "#8b949e"

# --- Layout Grid Definitions ---
CANVAS_WIDTH = 800
CANVAS_PAD = 25
PANEL_GAP = 15
ROW2_PANEL_W = (CANVAS_WIDTH - PANEL_GAP) // 2

QUERY = """
query($cursor: String) {
  viewer {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        primaryLanguage {
          name
        }
      }
    }
  }
}
"""

def fetch_project_stats():
    """Fetches and aggregates language statistics from GitHub."""
    if not TOKEN: 
        print("[ERROR] GH_TOKEN environment variable is not set.")
        return {}
        
    headers = {"Authorization": f"Bearer {TOKEN}"}
    stats = {}
    has_next_page = True
    cursor = None

    while has_next_page:
        variables = {"cursor": cursor}
        response = requests.post(URL, json={"query": QUERY, "variables": variables}, headers=headers)
        
        if response.status_code != 200:
            print(f"[ERROR] GitHub API returned status {response.status_code}")
            return stats
            
        data = response.json()
        
        if "errors" in data:
            print("[ERROR] GraphQL execution failed.")
            return stats
            
        repo_data = data["data"]["viewer"]["repositories"]
        
        for repo in repo_data["nodes"]:
            if repo.get("primaryLanguage") and repo["primaryLanguage"]:
                lang = repo["primaryLanguage"]["name"]
                stats[lang] = stats.get(lang, 0) + 1
                
        has_next_page = repo_data["pageInfo"]["hasNextPage"]
        cursor = repo_data["pageInfo"]["endCursor"]
                
    return stats

def generate_panel_bg(w, h):
    return f'    <rect width="{w}" height="{h}" rx="15" ry="15" fill="#171717" stroke="#3ED9C9" stroke-width="3" filter="url(#soft-shadow)" class="animated-border"/>'

def build_profile_panel(data, x, y, panel_w):
    title = data["title"]
    
    raw_desc = " ".join(data["description"])
    wrapped_desc = textwrap.wrap(raw_desc, width=95)
    
    height = 80 + (len(wrapped_desc) * 26) + 10
    
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_w, height))
    svg.append(f'    <text x="35" y="40" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    
    svg.append(f'    <text x="35" y="80" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="16">')
    for i, line in enumerate(wrapped_desc):
        dy = "0" if i == 0 else "26"
        svg.append(f'      <tspan x="35" dy="{dy}">{line}</tspan>')
    svg.append('    </text>')
    svg.append('  </g>')
    
    return "\n".join(svg), height

def calc_skills_panel_height(items, panel_w):
    """Pre-computes the required height for a skill panel based on wrapping logic."""
    current_x = 35
    current_y = 70
    
    for item in items:
        item_w = item.get("width", 80)
        if current_x + item_w > panel_w - 35:
            current_x = 35
            current_y += 45
        current_x += item_w + 15
        
    return current_y + 30 + 25

def build_skills_panel(data, x, y, panel_w, fixed_height):
    title = data["title"]
    items = data["items"]
    
    current_x = 35
    current_y = 70
    elements = []
    
    for item in items:
        item_w = item.get("width", 80)
        if current_x + item_w > panel_w - 35:
            current_x = 35
            current_y += 45
            
        elements.append(f'''    <g transform="translate({current_x}, {current_y})">
      <rect width="{item_w}" height="30" rx="15" fill="#1E1E1E" stroke="{item["color"]}" stroke-width="2"/>
      <text x="{item_w / 2}" y="16" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{item["name"]}</text>
    </g>''')
        current_x += item_w + 15
        
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_w, fixed_height))
    svg.append(f'    <text x="35" y="40" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    svg.extend(elements)
    svg.append('  </g>')
    
    return "\n".join(svg)

def build_horizontal_percentages(stats, x, y, panel_w):
    """Generates a proportional, stacked horizontal bar graph."""
    height = 140
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(panel_w, height))

    if not stats:
        svg.append('  </g>')
        return "\n".join(svg), height

    all_langs = sorted(stats.items(), key=lambda k: (-k[1], k[0]))
    global_total = sum(count for _, count in all_langs)
    
    if global_total == 0:
        svg.append('  </g>')
        return "\n".join(svg), height

    processed_langs = all_langs[:MAX_LANGUAGES-1] + [("Others", sum(c for _, c in all_langs[MAX_LANGUAGES-1:]))] if len(all_langs) > MAX_LANGUAGES else all_langs

    # Horizontal stacked logic
    bar_area_padding = 40
    total_bar_width = panel_w - (bar_area_padding * 2)
    gap_size = 4
    num_langs = len(processed_langs)
    usable_width = total_bar_width - (gap_size * (num_langs - 1))

    svg.append(f'    <g transform="translate({bar_area_padding}, 40)">')
    
    current_x = 0
    for i, (lang, count) in enumerate(processed_langs):
        percentage = (count / global_total) * 100
        color = LANGUAGE_COLORS.get(lang, FALLBACK_COLOR)
        
        # Calculate proportional width. The last segment absorbs rounding discrepancies.
        segment_width = total_bar_width - current_x if i == num_langs - 1 else int((percentage / 100) * usable_width)
        midpoint_x = current_x + (segment_width / 2)
        
        anim_delay = i * 0.15
        text_delay = anim_delay + 0.3

        # Center-expanding animations correctly bounded to the horizontal axis
        svg.append(f'''      <rect x="{midpoint_x}" y="0" width="0" height="12" rx="6" fill="{color}">
        <animate attributeName="width" from="0" to="{segment_width}" dur="0.6s" begin="{anim_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
        <animate attributeName="x" from="{midpoint_x}" to="{current_x}" dur="0.6s" begin="{anim_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
      </rect>
      <text x="{midpoint_x}" y="35" fill="{color}" font-family="system-ui, sans-serif" font-size="15" font-weight="bold" text-anchor="middle" dominant-baseline="middle" opacity="0">
        {lang}
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>
      <text x="{midpoint_x}" y="55" fill="{color}" font-family="system-ui, sans-serif" font-size="13" font-weight="normal" text-anchor="middle" dominant-baseline="middle" opacity="0">
        {percentage:.1f}%
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>''')
        
        current_x += segment_width + gap_size
        
    svg.append('    </g>')
    svg.append('  </g>')

    return "\n".join(svg), height

def main():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        
    project_stats = fetch_project_stats()
    components = []
    
    curr_y = CANVAS_PAD
    
    # Row 1 (Profile Container)
    me_svg, me_h = build_profile_panel(config["profile"], CANVAS_PAD, curr_y, CANVAS_WIDTH)
    components.append(me_svg)
    curr_y += me_h + PANEL_GAP
    
    # Row 2 (Skills Grid)
    lang_items = config["skill_columns"][0]["items"]
    tech_items = config["skill_columns"][1]["items"]
    
    lang_req_h = calc_skills_panel_height(lang_items, ROW2_PANEL_W)
    tech_req_h = calc_skills_panel_height(tech_items, ROW2_PANEL_W)
    row2_target_h = max(lang_req_h, tech_req_h)
    
    lang_svg = build_skills_panel(config["skill_columns"][0], CANVAS_PAD, curr_y, ROW2_PANEL_W, row2_target_h)
    tech_svg = build_skills_panel(config["skill_columns"][1], CANVAS_PAD + ROW2_PANEL_W + PANEL_GAP, curr_y, ROW2_PANEL_W, row2_target_h)
    
    components.append(lang_svg)
    components.append(tech_svg)
    curr_y += row2_target_h + PANEL_GAP
    
    # Row 3 (Statistics Container)
    perc_svg, perc_h = build_horizontal_percentages(project_stats, CANVAS_PAD, curr_y, CANVAS_WIDTH)
    components.append(perc_svg)
    curr_y += perc_h + CANVAS_PAD

    # Canvas Compilation
    total_width = CANVAS_WIDTH + (CANVAS_PAD * 2)
    total_height = curr_y

    final_svg = f'''<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="soft-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity="0.6"/>
    </filter>

    <linearGradient id="maven-gradle-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#C71A36" /> 
      <stop offset="100%" stop-color="#1DC9B7" /> 
    </linearGradient>
  </defs>
  <style>
    .animated-border {{ stroke-dasharray: 20, 10; animation: dash-flow 2s linear infinite; }}
    @keyframes dash-flow {{ from {{ stroke-dashoffset: 30; }} to {{ stroke-dashoffset: 0; }} }}
  </style>

{chr(10).join(components)}
</svg>'''

    with open("image.svg", "w") as file: 
        file.write(final_svg)

if __name__ == "__main__":
    main()