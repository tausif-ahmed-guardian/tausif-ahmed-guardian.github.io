#!/usr/bin/env python3
"""Refresh the live parts of Tausif's site (index.html) from GitHub. Standard library only.

    python3 tools/build_site.py --profile-repo <checkout of tausif-ahmed-guardian/tausif-ahmed-guardian>

index.html is the design itself; this script only rewrites what sits between its markers:
  <!--LEDGER:START--> ... <!--LEDGER:END-->   scoreboard + one ledger row per public item
  <!--ASOF:START--> ... <!--ASOF:END-->       the "as of" line under the ledger
The items come from the profile repo's own build_profile.upstream_items() (GitHub search, GitHub's
merged flag), so the site and the profile README can never show different numbers. Nothing about the
person is typed here. Writes index.html only when the items changed, so a quiet day makes no commit.
"""
import argparse
import datetime as dt
import html
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
LABEL = {"merged": "Merged", "accepted": "Accepted", "open": "In review", "proposed": "Proposed"}
DONE = ("merged", "accepted")


def e(s):
    return html.escape(str(s), quote=True)


def upstream(repo):
    spec = importlib.util.spec_from_file_location("build_profile", os.path.join(repo, "tools", "build_profile.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    prof = json.load(open(os.path.join(repo, "profile.json"), encoding="utf-8"))
    items = bp.upstream_items(prof, False)[0]
    if not items:
        raise SystemExit("GitHub returned no items: refusing to publish an empty ledger")
    return items


def day(iso):
    t = dt.date.fromisoformat(iso)
    return "%d %s %d" % (t.day, t.strftime("%b"), t.year)


def ledger(items):
    done = sum(i["status"] in DONE for i in items)
    projects = len({i["repo"] for i in items})
    out = ['    <div class="score" id="score">',
           '      <div><b id="scC">%d</b><span>contributions</span></div>' % len(items),
           '      <div><b id="scM">%d</b><span>merged or accepted</span></div>' % done,
           '      <div><b id="scP">%d</b><span>projects</span></div>' % projects,
           '    </div>',
           '    <p class="lg-head"><span>Ledger</span><span>Merged first, then newest</span></p>',
           '    <ol class="lg" id="lg">',
           '      <li class="lg-rail" id="lgRail" aria-hidden="true"></li>']
    order = sorted(sorted(items, key=lambda i: (i["date"], i["num"]), reverse=True), key=lambda i: i["status"] not in DONE)
    for i in order:
        ref = "%s #%d" % ("PR" if i["kind"] == "pull" else "Issue", i["num"])
        out.append(
            '      <li class="lg-row" data-status="%s" data-project="%s">\n'
            '        <span class="lg-dot" aria-hidden="true"></span>\n'
            '        <p class="lg-date">%s</p>\n'
            '        <div><h3>%s <span>#%d</span></h3>\n'
            '          <p class="t">%s</p></div>\n'
            '        <div class="lg-meta"><span class="pill">%s</span><a class="ext" href="%s" rel="noopener">%s '
            '<svg class="arr" aria-hidden="true"><use href="#i-ne"/></svg></a></div>\n'
            '      </li>' % (e(i["status"]), e(i["repo"]), e(day(i["date"])), e(i["repo"]), i["num"], e(i["title"]),
                            e(LABEL[i["status"]]), e(i["url"]), e(ref)))
    out.append('    </ol>')
    return "\n".join(out)


def put(s, tag, body):
    pat = re.compile(r"(<!--%s:START-->).*?(<!--%s:END-->)" % (tag, tag), re.S)
    if len(pat.findall(s)) != 1:
        raise SystemExit("marker %s missing or duplicated in index.html" % tag)
    return pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2) if tag == "LEDGER" else m.group(1) + body + m.group(2), s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile-repo", required=True)
    a = ap.parse_args()
    items = upstream(a.profile_repo)
    s = open(INDEX, encoding="utf-8").read()
    new = put(s, "LEDGER", ledger(items))
    if new == s:
        print("index.html unchanged: %d items" % len(items))
        return 0
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    new = put(new, "ASOF", "Ledger as of %s, read from GitHub (account tausif-ahmed-guardian) and rebuilt every two hours." % day(today))
    open(INDEX, "w", encoding="utf-8").write(new)
    print("index.html updated: %d items, %d merged or accepted" % (len(items), sum(i["status"] in DONE for i in items)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
