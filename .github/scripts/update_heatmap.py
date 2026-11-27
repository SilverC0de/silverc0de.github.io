"""Regenerate asset/github-contributions.svg and the "Through" date in index.html."""
import datetime as dt
import json
import os
import re
import urllib.request

USER = "SilverC0de"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG_PATH = os.path.join(ROOT, "asset", "github-contributions.svg")
SVG_DARK_PATH = os.path.join(ROOT, "asset", "github-contributions-dark.svg")
HTML_PATH = os.path.join(ROOT, "index.html")

LIGHT = ["#f2f2f2", "#a3cbab", "#629c70", "#376e45", "#173d22"]
DARK = ["#1a1a1a", "#2d5537", "#468757", "#6fb680", "#a9e4b6"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionLevel } }
      }
    }
  }
}"""


def fetch_weeks():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        body = json.load(res)
    if "errors" in body:
        raise SystemExit(f"GitHub API error: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [w["contributionDays"] for w in cal["weeks"]]


def build_svg(weeks, palette, text_color):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} 100">'.format(len(weeks) * 12 - 2)]
    out += ["<style>", f"    text {{ font: 10px system-ui; fill: {text_color}; }}"]
    out += [f"    .level-{i} {{ fill: {c}; }}" for i, c in enumerate(palette)]
    out.append("</style>")
    out.append(f"<title>{USER}’s GitHub contribution calendar</title>")

    labels, last_label = [], -3
    for i, week in enumerate(weeks):
        x = i * 12
        for day in week:
            d = dt.date.fromisoformat(day["date"])
            lvl = LEVELS.get(day["contributionLevel"], 0)
            y = 18 + ((d.weekday() + 1) % 7) * 12  # Sunday first
            out.append(f'<rect class="level-{lvl}" x="{x}" y="{y}" width="10" height="10" '
                       f'rx="2" fill="{palette[lvl]}"><title>{day["date"]}</title></rect>')
            if d.day == 1 and i > 0 and i - last_label >= 3:
                labels.append(f'<text x="{x}" y="11">{d.strftime("%b")}</text>')
                last_label = i
    out += labels
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    weeks = fetch_weeks()
    last = dt.date.fromisoformat(weeks[-1][-1]["date"])
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(build_svg(weeks, LIGHT, "#363d37"))
    with open(SVG_DARK_PATH, "w", encoding="utf-8") as f:
        f.write(build_svg(weeks, DARK, "#cdd5ce"))

    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    stamp = f"Through {last.day} {last.strftime('%b %Y')}"
    html, n = re.subn(r'(<span class="heatmap__date">)[^<]*(</span>)', rf"\g<1>{stamp}\g<2>", html)
    if n != 1:
        raise SystemExit("Could not find the heatmap date in index.html")
    html = re.sub(r'(github-contributions(?:-dark)?\.svg)(\?v=\d+)?"', rf'\g<1>?v={last:%Y%m%d}"', html)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(stamp)


if __name__ == "__main__":
    main()
