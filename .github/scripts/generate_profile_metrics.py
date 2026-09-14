#!/usr/bin/env python3
"""Generate self-hosted SVG profile metrics using GitHub's own APIs."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"


def request_json(url: str, token: str, payload: dict | None = None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "self-hosted-profile-metrics",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_profile(username: str, token: str):
    profile = request_json(f"{API}/users/{urllib.parse.quote(username)}", token)
    repos = []
    for page in range(1, 12):
        batch = request_json(
            f"{API}/users/{urllib.parse.quote(username)}/repos?type=owner&sort=updated&per_page=100&page={page}",
            token,
        )
        repos.extend(batch)
        if len(batch) < 100:
            break
    return profile, repos


def load_contributions(username: str, token: str):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=364)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount weekday }
            }
          }
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "login": username,
            "from": start.isoformat(),
            "to": now.isoformat(),
        },
    }
    result = request_json(GRAPHQL, token, payload)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    return calendar["totalContributions"], calendar["weeks"], days


def streaks(days: list[dict]):
    ordered = sorted(days, key=lambda d: d["date"])
    longest = running = 0
    for day in ordered:
        if int(day["contributionCount"]) > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    current = 0
    rev = list(reversed(ordered))
    if rev and int(rev[0]["contributionCount"]) == 0:
        rev = rev[1:]
    for day in rev:
        if int(day["contributionCount"]) > 0:
            current += 1
        else:
            break
    return current, longest


def intensity_levels(days: list[dict]):
    positives = sorted(int(d["contributionCount"]) for d in days if int(d["contributionCount"]) > 0)
    if not positives:
        return (1, 2, 3)
    def pick(frac):
        return positives[min(len(positives) - 1, int((len(positives) - 1) * frac))]
    return (max(1, pick(.35)), max(2, pick(.65)), max(3, pick(.88)))


def level(count: int, thresholds):
    if count <= 0: return 0
    if count <= thresholds[0]: return 1
    if count <= thresholds[1]: return 2
    if count <= thresholds[2]: return 3
    return 4


def svg_shell(width, height, title, description, inner):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#080d18"/><stop offset="1" stop-color="#11152b"/></linearGradient>
  <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#22d3ee"/><stop offset=".52" stop-color="#60a5fa"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
  <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#93c5fd" stroke-opacity=".04"/></pattern>
</defs>
<style>.base{{font-family:Arial,Helvetica,sans-serif}}.mono{{font-family:Consolas,'Courier New',monospace}}</style>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" fill="url(#bg)" stroke="#273652"/>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" fill="url(#grid)"/>
<rect x="26" y="23" width="112" height="4" rx="2" fill="url(#accent)"/>
{inner}</svg>'''


def overview_svg(username, profile, repos, total_contrib, current_streak, longest_streak, updated):
    owned = [r for r in repos if not r.get("fork")]
    stars = sum(int(r.get("stargazers_count", 0)) for r in owned)
    languages = Counter(r.get("language") for r in owned if r.get("language"))
    lang_text = "  ·  ".join(f"{name} {count}" for name, count in languages.most_common(6)) or "Repositories are being indexed"
    metrics = [
        (str(profile.get("public_repos", len(owned))), "PUBLIC REPOS", "Projects and experiments"),
        (str(stars), "STARS EARNED", "Across owned repositories"),
        (str(profile.get("followers", 0)), "FOLLOWERS", "Developer network"),
        (f"{total_contrib:,}" if total_contrib is not None else "—", "CONTRIBUTIONS", "Last 12 months"),
        (str(longest_streak) if longest_streak is not None else "—", "LONGEST STREAK", "Consecutive active days"),
    ]
    boxes=[]
    for i,(value,label,note) in enumerate(metrics):
        x=28+i*232
        boxes.append(f'''<g><rect x="{x}" y="85" width="214" height="126" rx="14" fill="#0d1527" stroke="#273652"/><text x="{x+18}" y="129" class="base" font-size="32" font-weight="800" fill="#f8fafc">{escape(value)}</text><text x="{x+18}" y="158" class="base" font-size="13" font-weight="800" letter-spacing="1.2" fill="#67e8f9">{escape(label)}</text><text x="{x+18}" y="187" class="base" font-size="13" fill="#7f91aa">{escape(note)}</text></g>''')
    inner=f'''<text x="28" y="58" class="base" font-size="25" font-weight="800" fill="#f8fafc">GitHub engineering signal</text><text x="1172" y="55" text-anchor="end" class="mono" font-size="13" fill="#7f91aa">updated {escape(updated)}</text>{''.join(boxes)}<text x="30" y="246" class="base" font-size="13" font-weight="800" letter-spacing="1.2" fill="#a78bfa">PRIMARY REPOSITORY LANGUAGES</text><text x="30" y="274" class="base" font-size="15" fill="#cbd5e1">{escape(lang_text)}</text>'''
    return svg_shell(1200,300,f"{username} GitHub engineering signal","Self-hosted GitHub profile metrics refreshed daily",inner)


def activity_svg(username, weeks, days, current_streak, longest_streak, updated):
    thresholds=intensity_levels(days)
    palette=["#151c2a","#0b6e5f","#0ea577","#22d3a6","#67e8f9"]
    cells=[]
    visible=weeks[-53:]
    for wi,week in enumerate(visible):
        by_weekday={int(d["weekday"]):d for d in week["contributionDays"]}
        for weekday in range(7):
            d=by_weekday.get(weekday)
            count=int(d["contributionCount"]) if d else 0
            x=30+wi*14.7; y=94+weekday*14.7
            cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="11" height="11" rx="2.5" fill="{palette[level(count,thresholds)]}"><title>{count} contributions</title></rect>')
    active=sum(1 for d in days if int(d["contributionCount"])>0)
    total=sum(int(d["contributionCount"]) for d in days)
    best=max((int(d["contributionCount"]) for d in days), default=0)
    inner=f'''<text x="28" y="58" class="base" font-size="25" font-weight="800" fill="#f8fafc">Contribution momentum</text><text x="1172" y="55" text-anchor="end" class="mono" font-size="13" fill="#7f91aa">rolling 12 months · {escape(updated)}</text><g>{''.join(cells)}</g><text x="30" y="226" class="base" font-size="13" fill="#7f91aa">Less</text><rect x="67" y="216" width="11" height="11" rx="2" fill="#151c2a"/><rect x="84" y="216" width="11" height="11" rx="2" fill="#0b6e5f"/><rect x="101" y="216" width="11" height="11" rx="2" fill="#0ea577"/><rect x="118" y="216" width="11" height="11" rx="2" fill="#22d3a6"/><rect x="135" y="216" width="11" height="11" rx="2" fill="#67e8f9"/><text x="153" y="226" class="base" font-size="13" fill="#7f91aa">More</text><rect x="838" y="82" width="334" height="166" rx="16" fill="#0d1527" stroke="#273652"/><text x="864" y="112" class="base" font-size="13" font-weight="800" letter-spacing="1.2" fill="#a78bfa">ACTIVITY SNAPSHOT</text><text x="864" y="154" class="base" font-size="29" font-weight="800" fill="#f8fafc">{current_streak}</text><text x="912" y="151" class="base" font-size="13" fill="#94a3b8">current streak</text><text x="864" y="190" class="base" font-size="29" font-weight="800" fill="#f8fafc">{longest_streak}</text><text x="912" y="187" class="base" font-size="13" fill="#94a3b8">longest streak</text><text x="1028" y="154" class="base" font-size="29" font-weight="800" fill="#f8fafc">{active}</text><text x="1104" y="151" class="base" font-size="13" fill="#94a3b8">active days</text><text x="1028" y="190" class="base" font-size="29" font-weight="800" fill="#f8fafc">{best}</text><text x="1104" y="187" class="base" font-size="13" fill="#94a3b8">best day</text><text x="864" y="226" class="mono" font-size="13" fill="#67e8f9">{total:,} contributions recorded</text>'''
    return svg_shell(1200,275,f"{username} contribution momentum","Self-hosted contribution calendar and streak metrics",inner)


def demo_data():
    profile={"public_repos":74,"followers":3}
    repos=[]
    langs=["Python"]*24+["JavaScript"]*12+["TypeScript"]*10+["HTML"]*7+["CSS"]*6+["Java"]*3
    for i,lang in enumerate(langs): repos.append({"fork":False,"stargazers_count":1 if i<10 else 0,"language":lang})
    start=datetime.now(timezone.utc).date()-timedelta(days=364)
    days=[]; weeks=[]
    for w in range(53):
        wd=[]
        for d in range(7):
            day=start+timedelta(days=w*7+d)
            if day>datetime.now(timezone.utc).date(): continue
            count=((w*5+d*3)%9) if (w+d)%3 else 0
            item={"date":day.isoformat(),"contributionCount":count,"weekday":d}
            days.append(item); wd.append(item)
        weeks.append({"contributionDays":wd})
    return profile,repos,sum(d["contributionCount"] for d in days),weeks,days


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--username", default="adarsh-pathak-2006")
    parser.add_argument("--output", default="dist")
    parser.add_argument("--demo", action="store_true")
    args=parser.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    token=os.environ.get("GITHUB_TOKEN","")
    if args.demo:
        profile,repos,total,weeks,days=demo_data()
    else:
        if not token: raise SystemExit("GITHUB_TOKEN is required")
        profile,repos=load_profile(args.username,token)
        try:
            total,weeks,days=load_contributions(args.username,token)
        except Exception as exc:
            print(f"Contribution API unavailable: {exc}")
            total,weeks,days=None,[],[]
    current,longest=streaks(days) if days else (0,0)
    updated=datetime.now(timezone.utc).strftime("%d %b %Y UTC")
    (out/"profile-overview.svg").write_text(overview_svg(args.username,profile,repos,total,current,longest,updated),encoding="utf-8")
    (out/"profile-activity.svg").write_text(activity_svg(args.username,weeks,days,current,longest,updated),encoding="utf-8")
    print(f"Generated self-hosted metrics in {out}")

if __name__=="__main__": main()
