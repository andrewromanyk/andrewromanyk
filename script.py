import os
import json
import requests
import textwrap

# --- Configuration & Constants ---
URL = "https://api.github.com/graphql"
TOKEN = os.getenv("GH_TOKEN")
CONFIG_PATH = "config.json"
MAX_LANGUAGES = 5 

LANGUAGE_COLORS = {
    "Rust": "#dea584", "C++": "#f34b7d", "C": "#555555",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Python": "#3572A5",
    "Haskell": "#5e5086", "Prolog": "#74283c", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Go": "#00ADD8", "Shell": "#89e051",
    "HTML": "#e34c26", "CSS": "#563d7c", "Ruby": "#701516",
    "C#": "#178600", "PHP": "#4F5D95", "Swift": "#F05138"
}
FALLBACK_COLOR = "#8b949e"

# --- Panel Dimensions & Layout ---
PANEL_W_LEFT = 464  
PANEL_W_RIGHT = 120 
PANEL_PAD_X = 35
PANEL_GAP = 15
CANVAS_PAD = 5 # Padding to prevent the 3px stroke from clipping at the SVG bounds

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
    headers = {"Authorization": f"Bearer {TOKEN}"}
    stats = {}
    has_next_page = True
    cursor = None

    while has_next_page:
        variables = {"cursor": cursor}
        response = requests.post(URL, json={"query": QUERY, "variables": variables}, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        repo_data = data["data"]["viewer"]["repositories"]
        
        for repo in repo_data["nodes"]:
            if repo.get("primaryLanguage") and repo["primaryLanguage"]:
                lang = repo["primaryLanguage"]["name"]
                stats[lang] = stats.get(lang, 0) + 1
                
        has_next_page = repo_data["pageInfo"]["hasNextPage"]
        cursor = repo_data["pageInfo"]["endCursor"]
                
    return stats

def generate_panel_bg(w, h):
    return f'    <rect width="{w}" height="{h}" rx="15" ry="15" fill="#171717" stroke="#3ED9C9" stroke-width="3" class="animated-border"/>'

def build_profile_panel(data, x, y):
    title = data["title"]
    
    # Wrap text to ~48 characters to fit the scaled 464px width safely
    raw_desc = " ".join(data["description"])
    wrapped_desc = textwrap.wrap(raw_desc, width=48)
    
    height = 80 + (len(wrapped_desc) * 26) + 10
    
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(PANEL_W_LEFT, height))
    svg.append(f'    <text x="{PANEL_PAD_X}" y="40" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    
    svg.append(f'    <text x="{PANEL_PAD_X}" y="80" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="16">')
    for i, line in enumerate(wrapped_desc):
        dy = "0" if i == 0 else "26"
        svg.append(f'      <tspan x="{PANEL_PAD_X}" dy="{dy}">{line}</tspan>')
    svg.append('    </text>')
    svg.append('  </g>')
    
    return "\n".join(svg), height

def build_skills_panel(data, x, y):
    title = data["title"]
    items = data["items"]
    
    current_x = PANEL_PAD_X
    current_y = 70
    elements = []
    
    for item in items:
        item_w = item.get("width", 80)
        # Wrap logic bound to new 464px width
        if current_x + item_w > PANEL_W_LEFT - PANEL_PAD_X:
            current_x = PANEL_PAD_X
            current_y += 45
            
        elements.append(f'''    <g transform="translate({current_x}, {current_y})">
      <rect width="{item_w}" height="30" rx="15" fill="#1E1E1E" stroke="{item["color"]}" stroke-width="2"/>
      <text x="{item_w / 2}" y="16" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{item["name"]}</text>
    </g>''')
        current_x += item_w + 15
        
    height = current_y + 30 + 25 
    
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(PANEL_W_LEFT, height))
    svg.append(f'    <text x="{PANEL_PAD_X}" y="40" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    svg.extend(elements)
    svg.append('  </g>')
    
    return "\n".join(svg), height

def build_dynamic_bars_panel(stats, x, y, panel_height):
    svg = [f'  <g transform="translate({x}, {y})">']
    svg.append(generate_panel_bg(PANEL_W_RIGHT, panel_height))

    if not stats:
        svg.append('  </g>')
        return "\n".join(svg)

    all_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    global_total = sum(count for _, count in all_langs)
    processed_langs = all_langs[:MAX_LANGUAGES-1] + [("Others", sum(c for _, c in all_langs[MAX_LANGUAGES-1:]))] if len(all_langs) > MAX_LANGUAGES else all_langs

    total_bar_height = panel_height - 80 
    gap_size = 4
    num_langs = len(processed_langs)
    usable_height = total_bar_height - (gap_size * (num_langs - 1))

    # Inner group shifted for the bars layout inside the 120px panel
    svg.append('    <g transform="translate(15, 40)">')
    
    current_y = 0
    for i, (lang, count) in enumerate(processed_langs):
        percentage = (count / global_total) * 100
        color = LANGUAGE_COLORS.get(lang, FALLBACK_COLOR)
        
        segment_height = total_bar_height - current_y if i == num_langs - 1 else int((percentage / 100) * usable_height)
        midpoint_y = current_y + (segment_height / 2)
        bar_delay = i * 0.15
        text_delay = bar_delay + 0.3

        svg.append(f'''      <rect x="0" y="{midpoint_y}" width="8" height="0" rx="4" fill="{color}">
        <animate attributeName="height" from="0" to="{segment_height}" dur="0.6s" begin="{bar_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
        <animate attributeName="y" from="{midpoint_y}" to="{current_y}" dur="0.6s" begin="{bar_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
      </rect>
      <text x="16" y="{midpoint_y - 10}" fill="{color}" font-family="system-ui, sans-serif" font-size="15" font-weight="bold" dominant-baseline="middle" opacity="0">
        {lang}
        <animate attributeName="x" from="4" to="16" dur="0.5s" begin="{text_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>
      <text x="16" y="{midpoint_y + 10}" fill="{color}" font-family="system-ui, sans-serif" font-size="13" font-weight="normal" dominant-baseline="middle" opacity="0">
        {percentage:.1f}%
        <animate attributeName="x" from="4" to="16" dur="0.5s" begin="{text_delay}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" />
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{text_delay}s" fill="freeze" />
      </text>''')
        current_y += segment_height + gap_size
        
    svg.append('    </g>')
    svg.append('  </g>')

    return "\n".join(svg)

def main():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        
    project_stats = fetch_project_stats()
    
    components = []
    
    # 1. Calculate and build left column (y offsets increment cumulatively)
    curr_y = CANVAS_PAD
    
    me_svg, me_h = build_profile_panel(config["profile"], CANVAS_PAD, curr_y)
    components.append(me_svg)
    curr_y += me_h + PANEL_GAP
    
    lang_svg, lang_h = build_skills_panel(config["skill_columns"][0], CANVAS_PAD, curr_y)
    components.append(lang_svg)
    curr_y += lang_h + PANEL_GAP
    
    tech_svg, tech_h = build_skills_panel(config["skill_columns"][1], CANVAS_PAD, curr_y)
    components.append(tech_svg)
    
    # 2. Derive target height for right column and full SVG bounds
    # curr_y currently sits at the top of the tech panel. Add tech_h to get total left bounds.
    total_left_height = (curr_y + tech_h) - CANVAS_PAD
    
    # 3. Build right column horizontally offset
    right_x = CANVAS_PAD + PANEL_W_LEFT + PANEL_GAP
    perc_svg = build_dynamic_bars_panel(project_stats, right_x, CANVAS_PAD, total_left_height)
    components.append(perc_svg)

    # Calculate final canvas dimensions
    total_width = right_x + PANEL_W_RIGHT + CANVAS_PAD
    total_height = CANVAS_PAD + total_left_height + CANVAS_PAD

    final_svg = f'''<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
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