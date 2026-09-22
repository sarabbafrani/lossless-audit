"""Command line interface."""

import argparse
import json
import os
import sys

from . import engine, i18n

CHART_ROWS = 22
CHART_WIDTH = 46


def default_language():
    env = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "")
    return "fa" if env.lower().startswith("fa") else "en"


def draw_chart(result):
    data = result["chart"]
    n = len(data)
    lines = []
    for i in range(CHART_ROWS):
        k0 = int(i * n / CHART_ROWS)
        k1 = max(k0 + 1, int((i + 1) * n / CHART_ROWS))
        level = max(x[1] for x in data[k0:k1])
        filled = max(0, min(CHART_WIDTH,
                            int(round((level + 120.0) / 120.0 * CHART_WIDTH))))
        lines.append("   %6.1f kHz |%s| %6.1f dB"
                     % (data[k0][0], "#" * filled + "." * (CHART_WIDTH - filled),
                        level))
    return "\n".join(lines)


def report(result, lang, chart):
    print("=" * 70)
    print(result.get("name", "?"))
    print("=" * 70)

    if "error" in result:
        detail = result.get("detail")
        print("  %s%s\n" % (i18n.t(lang, result["error"]),
                            " (%s)" % detail if detail else ""))
        return

    r = engine.localise(result, lang)
    minutes, seconds = divmod(int(r["duration"]), 60)
    print("  %s / %s / %d Hz / %d ch / %d:%02d / %.1f MB"
          % (r["container"], r["subtype"], r["rate"], r["channels"],
             minutes, seconds, r["size"] / 1048576.0))
    print()
    print("  %d / 100   %s — %s" % (r["total"], r["grade_text"], r["tag_text"]))
    for p in r["parts"]:
        print("    %-22s %5.1f / %-3d  %s"
              % (p["name"], p["got"], p["max"], p["note_text"]))
    if chart:
        print()
        print(draw_chart(r))
    print()


def build_parser():
    p = argparse.ArgumentParser(
        prog="lossless-audit",
        description="Check whether a lossless audio file is genuine or was "
                    "re-encoded from a lossy source such as MP3 or AAC.")
    p.add_argument("paths", nargs="+", metavar="FILE|DIR",
                   help="files or folders to check (folders are walked)")
    p.add_argument("--lang", choices=i18n.LANGUAGES, default=default_language(),
                   help="output language (default: from your locale)")
    p.add_argument("--no-chart", action="store_true",
                   help="skip the spectrum plot")
    p.add_argument("--json", action="store_true",
                   help="machine-readable output, one object per file")
    p.add_argument("--fail-under", type=int, metavar="N", default=None,
                   help="exit non-zero if any file scores below N")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + __import__("losslessaudit").__version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    files = engine.collect(args.paths)
    if not files:
        print("no audio files found", file=sys.stderr)
        return 2

    results = []
    for path in files:
        r = engine.analyse(path)
        results.append(r)
        if not args.json:
            report(r, args.lang, not args.no_chart)

    if args.json:
        print(json.dumps([engine.localise(r, args.lang) for r in results],
                         ensure_ascii=False, indent=2))
    elif len(results) > 1:
        print("=" * 70)
        for r in results:
            print("  %3s   %s" % (r.get("total", "--"), r.get("name", "?")))

    if args.fail_under is not None:
        worst = [r for r in results
                 if r.get("total", 0) < args.fail_under or "error" in r]
        if worst:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
