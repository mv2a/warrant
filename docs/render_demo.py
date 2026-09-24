"""Regenerate docs/demo.svg from the real output of the pricing example.

Run it after changing anything the animation shows:  python3 docs/render_demo.py
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.svg"

# Every step runs for real, in order. Hidden steps are needed for later ones but aren't drawn.
STEPS = [
    ("run", "approve --by dana", False),
    ("comment", "Candidate A was written by a coding agent. It passes every check it can see.", True),
    ("run", "verify --workspace candidates/overfit --audience builder", True),
    ("run", "gate merge --workspace candidates/overfit", True),
    ("comment", "Candidate B was written by another agent.", True),
    ("run", "verify --workspace candidates/honest --audience builder", False),
    ("run", "gate merge --workspace candidates/honest", True),
]
SKIP_OUTPUT = ("Recorded in ledger entry",)

WIDTH, LINE, TOP, LEFT, FONT = 900, 19, 60, 22, 13
CHAR = FONT * 0.6  # typical monospace advance
TYPING, OUTPUT_GAP, PAUSE, HOLD = 0.035, 0.06, 1.0, 5.0
BACKGROUND, TITLE_BAR = "#0d1117", "#161b22"
STYLES = {
    "text": "#c9d1d9", "bright": "#e6edf3", "dim": "#8b949e",
    "green": "#3fb950", "red": "#f85149", "amber": "#d29922",
}


def capture() -> list[tuple[str, str]]:
    """Run the steps on a copy of the example and return the (kind, text) lines to draw."""
    lines: list[tuple[str, str]] = []
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "pricing"
        shutil.copytree(ROOT / "examples" / "pricing", project, ignore=shutil.ignore_patterns("ledger"))
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        for kind, text, shown in STEPS:
            if kind == "comment":
                if lines:
                    lines.append(("blank", ""))
                lines.append(("comment", f"# {text}"))
                continue
            result = subprocess.run(
                [sys.executable, "-m", "warrant", "-C", str(project), *text.split()],
                capture_output=True, text=True, env=env,
            )
            if result.returncode not in (0, 1):
                sys.exit(f"'warrant {text}' failed:\n{result.stderr}")
            if not shown:
                continue
            if lines and lines[-1][0] != "comment":
                lines.append(("blank", ""))
            lines.append(("command", f"$ warrant {text}"))
            lines += [("output", line) for line in result.stdout.rstrip("\n").split("\n") if not line.startswith(SKIP_OUTPUT)]
    return lines


def spans(kind: str, text: str) -> str:
    """Colour one line of output, the way a terminal would."""
    def span(style: str, part: str) -> str:
        return f'<tspan fill="{STYLES[style]}">{html.escape(part)}</tspan>'

    if kind == "comment":
        return span("dim", text)
    if kind == "command":
        return span("green", "$") + span("bright", text[1:])
    for word, style in (("PASS", "green"), ("FAIL", "red"), ("ERROR", "red"), ("DENIED", "red"), ("WARRANTED", "green")):
        before, found, after = text.partition(word)
        if found and (word not in ("PASS", "FAIL", "ERROR") or not before.strip()):
            return span("text", before) + f'<tspan font-weight="bold" fill="{STYLES[style]}">{word}</tspan>' + span("text", after)
    if text.strip().startswith(("hidden checks:", "Promises the hidden checks")):
        return span("amber", text)
    if text.strip().startswith("- "):
        return span("red", text)
    if text.startswith(("Re-read", "  caveat")):
        return span("dim", text)
    return span("text", text)


def render(lines: list[tuple[str, str]]) -> str:
    # When each line appears, and how long each command takes to type.
    moments, t = [], 0.5
    for kind, text in lines:
        if kind == "command":
            t += PAUSE
            typing = min(len(text) * TYPING, 1.8)
            moments.append((t, typing))
            t += typing + 0.5
        elif kind == "comment":
            t += 0.5
            moments.append((t, 0.0))
            t += 0.9
        else:
            moments.append((t, 0.0))
            t += OUTPUT_GAP
    total = t + HOLD
    height = TOP + LINE * len(lines) + 20

    def percent(seconds: float) -> str:
        return f"{seconds / total * 100:.3f}%"

    css, body = [], []
    for index, ((kind, text), (start, typing)) in enumerate(zip(lines, moments)):
        y = TOP + LINE * index
        shown = percent(start)
        css.append(
            f"@keyframes l{index}{{0%,{percent(max(start - 0.01, 0))}{{opacity:0}}"
            f"{shown},96%{{opacity:1}}98%,100%{{opacity:0}}}}"
        )
        body.append(f'<text class="l" style="animation-name:l{index}" x="{LEFT}" y="{y}">{spans(kind, text)}</text>')
        if typing:
            # A background-coloured cover slides right, one character at a time, to "type" the command.
            typed = CHAR * (len(text) - 2)
            css.append(
                f"@keyframes c{index}{{0%,{shown}{{transform:translateX(0);animation-timing-function:steps({len(text) - 2},end)}}"
                f"{percent(start + typing)},99.9%{{transform:translateX({typed:.1f}px)}}100%{{transform:translateX(0)}}}}"
            )
            body.append(
                f'<rect class="c" style="animation-name:c{index}" x="{LEFT + CHAR * 2:.1f}" y="{y - 14}" '
                f'width="{WIDTH}" height="{LINE}" fill="{BACKGROUND}"/>'
            )

    style = (
        f"text{{font:{FONT}px ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;white-space:pre}}"
        f".l,.c{{animation-duration:{total:.2f}s;animation-iteration-count:infinite}}.l{{opacity:0}}"
        # !important because each element names its animation inline, which would otherwise win.
        "@media (prefers-reduced-motion:reduce){.l{animation:none!important;opacity:1!important}.c{display:none!important}}"
        + "".join(css)
    )
    title = "Warrant demo: an agent-written implementation passes every visible check, hidden checks find two broken promises, and the merge is denied; a second implementation earns a warrant."
    dots = "".join(
        f'<circle cx="{22 + 20 * i}" cy="18" r="6" fill="{color}"/>'
        for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840"))
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
        f'role="img" aria-label="{html.escape(title)}" xml:space="preserve">\n'
        f"<title>{html.escape(title)}</title>\n<style>{style}</style>\n"
        f'<rect width="{WIDTH}" height="{height}" rx="10" fill="{BACKGROUND}"/>\n'
        f'<path d="M0 10a10 10 0 0 1 10-10h{WIDTH - 20}a10 10 0 0 1 10 10v26H0z" fill="{TITLE_BAR}"/>\n{dots}\n'
        f'<text x="{WIDTH / 2}" y="22" text-anchor="middle" fill="{STYLES["dim"]}">examples/pricing/demo.sh</text>\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


if __name__ == "__main__":
    OUT.write_text(render(capture()), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
