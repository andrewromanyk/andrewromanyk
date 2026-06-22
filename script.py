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

# --- Panel Dimensions ---
PANEL_W_LEFT = 464  
PANEL_W_RIGHT = 120 
PANEL_PAD_X = 35
STROKE_OFFSET = 5 
README_GAP_PX = 15 

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

def wrap_svg(content, width, height):
    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
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
{content}
</svg>'''

def generate_panel_bg(w, h):
    return f'  <rect x="{STROKE_OFFSET}" y="{STROKE_OFFSET}" width="{w}" height="{h}" rx="15" ry="15" fill="#171717" stroke="#3ED9C9" stroke-width="3" class="animated-border"/>'

def build_profile_svg(data):
    title = data["title"]
    
    # Dynamically wrap the text array to fit the scaled panel width
    raw_desc = " ".join(data["description"])
    wrapped_desc = textwrap.wrap(raw_desc, width=48)
    
    height = 80 + (len(wrapped_desc) * 26) + 10
    
    svg = [generate_panel_bg(PANEL_W_LEFT, height)]
    svg.append(f'  <text x="{STROKE_OFFSET + PANEL_PAD_X}" y="{STROKE_OFFSET + 40}" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    
    svg.append(f'  <text x="{STROKE_OFFSET + PANEL_PAD_X}" y="{STROKE_OFFSET + 80}" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="16">')
    for i, line in enumerate(wrapped_desc):
        dy = "0" if i == 0 else "26"
        svg.append(f'    <tspan x="{STROKE_OFFSET + PANEL_PAD_X}" dy="{dy}">{line}</tspan>')
    svg.append('  </text>')
    
    return wrap_svg("\n".join(svg), PANEL_W_LEFT + (STROKE_OFFSET * 2), height + (STROKE_OFFSET * 2)), height

def build_skills_svg(data):
    title = data["title"]
    items = data["items"]
    
    current_x = PANEL_PAD_X
    current_y = STROKE_OFFSET + 70
    elements = []
    
    for item in items:
        item_w = item.get("width", 80)
        if current_x + item_w > PANEL_W_LEFT - PANEL_PAD_X:
            current_x = PANEL_PAD_X
            current_y += 45
            
        elements.append(f'''  <g transform="translate({STROKE_OFFSET + current_x}, {current_y})">
    <rect width="{item_w}" height="30" rx="15" fill="#1E1E1E" stroke="{item["color"]}" stroke-width="2"/>
    <text x="{item_w / 2}" y="16" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{item["name"]}</text>
  </g>''')
        current_x += item_w + 15
        
    height = (current_y - STROKE_OFFSET) + 30 + 25 
    
    svg = [generate_panel_bg(PANEL_W_LEFT, height)]
    svg.append(f'  <text x="{STROKE_OFFSET + PANEL_PAD_X}" y="{STROKE_OFFSET + 40}" fill="#E2E8F0" font-family="system-ui, sans-serif" font-size="22" font-weight="bold">{title}</text>')
    svg.extend(elements)
    
    return wrap_svg("\n".join(svg), PANEL_W_LEFT + (STROKE_OFFSET * 2), height + (STROKE_OFFSET * 2)), height

def build_dynamic_bars_svg(stats, panel_height):
    if not stats: 
        return wrap_svg(generate_panel_bg(PANEL_W_RIGHT, panel_height), PANEL_W_RIGHT + (STROKE_OFFSET*2), panel_height + (STROKE_OFFSET*2))

    all_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    global_total = sum(count for _, count in all_langs)

    processed_langs = all_langs[:MAX_LANGUAGES-1] + [("Others", sum(c for _, c in all_langs[MAX_LANGUAGES-1:]))] if len(all_langs) > MAX_LANGUAGES else all_langs

    total_bar_height = panel_height - 80 
    gap_size = 4
    num_langs = len(processed_langs)
    usable_height = total_bar_height - (gap_size * (num_langs - 1))

    svg = [generate_panel_bg(PANEL_W_RIGHT, panel_height)]
    
    svg.append(f'  <g transform="translate({STROKE_OFFSET + 15}, {STROKE_OFFSET + 40})">')
    
    current_y = 0
    for i, (lang, count) in enumerate(processed_langs):
        percentage = (count / global_total) * 100
        color = LANGUAGE_COLORS.get(lang, FALLBACK_COLOR)
        
        segment_height = total_bar_height - current_y if i == num_langs - 1 else int((percentage / 100) * usable_height)
        midpoint_y = current_y + (segment_height / 2)
        bar_delay = i * 0.15
        text_delay = bar_delay + 0.3

        svg.append(f'''    <rect x="0" y="{midpoint_y}" width="8" height="0" rx="4" fill="{color}">
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
        
    svg.append('  </g>')

    return wrap_svg("\n".join(svg), PANEL_W_RIGHT + (STROKE_OFFSET * 2), panel_height + (STROKE_OFFSET * 2))

def main():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        
    project_stats = fetch_project_stats()
    
    me_svg, me_h = build_profile_svg(config["profile"])
    lang_svg, lang_h = build_skills_svg(config["skill_columns"][0])
    tech_svg, tech_h = build_skills_svg(config["skill_columns"][1])
    
    # Calculate aggregate height integrating HTML margins and canvas stroke offsets
    # Left column: 3 SVGs (6 stroke offsets) + 2 HTML gaps
    # Right column: 1 SVG (2 stroke offsets) 
    # Delta adjustment: 4 stroke offsets (20px) added to normalize the interior container bounds
    total_left_height = me_h + lang_h + tech_h + (README_GAP_PX * 2) + (STROKE_OFFSET * 4)
    
    perc_svg = build_dynamic_bars_svg(project_stats, total_left_height)

    os.makedirs("svg", exist_ok=True)

    with open("svg/me.svg", "w") as file: file.write(me_svg)
    with open("svg/languages.svg", "w") as file: file.write(lang_svg)
    with open("svg/technologies.svg", "w") as file: file.write(tech_svg)
    with open("svg/percentages.svg", "w") as file: file.write(perc_svg)

if __name__ == "__main__":
    main()