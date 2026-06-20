import os
import requests

URL = "https://api.github.com/graphql"
TOKEN = os.getenv("GH_TOKEN")
MAX_LANGUAGES = 5 

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
    "Swift": "#F05138"
}
FALLBACK_COLOR = "#8b949e"

QUERY = """
{
  viewer {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
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
    response = requests.post(URL, json={"query": QUERY}, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    repos = data["data"]["viewer"]["repositories"]["nodes"]
    
    stats = {}
    for repo in repos:
        if repo.get("primaryLanguage") and repo["primaryLanguage"]:
            lang = repo["primaryLanguage"]["name"]
            stats[lang] = stats.get(lang, 0) + 1
                
    return stats

def generate_svg_elements(stats):
    if not stats:
        return ""

    all_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    global_total_projects = sum(count for _, count in all_langs)
    
    if global_total_projects == 0:
        return ""

    processed_langs = []
    
    if len(all_langs) > MAX_LANGUAGES:
        top_langs = all_langs[:MAX_LANGUAGES - 1]
        others_count = sum(count for _, count in all_langs[MAX_LANGUAGES - 1:])
        
        processed_langs.extend(top_langs)
        processed_langs.append(("Others", others_count))
    else:
        processed_langs = all_langs

    total_height = 500
    gap_size = 4
    num_langs = len(processed_langs)
    usable_height = total_height - (gap_size * (num_langs - 1))

    svg_elements = []
    current_y = 0

    for i, (lang, count) in enumerate(processed_langs):
        percentage = (count / global_total_projects) * 100
        color = LANGUAGE_COLORS.get(lang, FALLBACK_COLOR)
        
        if i == num_langs - 1:
            segment_height = total_height - current_y
        else:
            segment_height = int((percentage / 100) * usable_height)

        rect = f'<rect x="0" y="{current_y}" width="8" height="{segment_height}" rx="4" fill="{color}" />'
        
        midpoint_y = current_y + (segment_height / 2)
        text_name_y = midpoint_y - 10
        text_perc_y = midpoint_y + 10

        text_name = f'<text x="20" y="{text_name_y}" fill="{color}" font-family="sans-serif" font-size="16" font-weight="bold" dominant-baseline="middle">{lang}</text>'
        text_perc = f'<text x="20" y="{text_perc_y}" fill="{color}" font-family="sans-serif" font-size="13" font-weight="normal" dominant-baseline="middle">{percentage:.1f}%</text>'

        svg_elements.extend([rect, text_name, text_perc])
        current_y += segment_height + gap_size

    return "\n    ".join(svg_elements)

def main():
    project_stats = fetch_project_stats()
    dynamic_svg_content = generate_svg_elements(project_stats)
    
    with open("image.template.svg", "r") as file:
        template = file.read()
        
    final_svg = template.format(dynamic_bars=dynamic_svg_content)
    
    with open("image.svg", "w") as file:
        file.write(final_svg)

if __name__ == "__main__":
    main()
