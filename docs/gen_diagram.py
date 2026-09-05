"""Generate docs/images/architecture-{light,dark}.svg for the README.

Every node carries the audit label it writes to the trail, so the design
principle is the picture: exactly one AI step, and clinical judgement stays
with a named human.

    python3 docs/gen_diagram.py
"""

import os

FONT = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

THEMES = {
    "light": dict(
        text="#1f2328", muted="#59636e", border="#d0d7de", panel="#f6f8fa", node="#ffffff",
        ai="#8250df", ai_fill="#fbf0ff", ai_border="#c297ff",
        rule="#1a7f37", rule_fill="#dafbe1", rule_border="#aceebb",
        human="#9a6700", human_fill="#fff8c5", human_border="#d4a72c",
        api="#0969da", api_fill="#ddf4ff", api_border="#b6e3ff",
        red="#cf222e", edge="#8c959f"),
    "dark": dict(
        text="#e6edf3", muted="#9198a1", border="#3d444d", panel="#151b23", node="#212830",
        ai="#ab7df8", ai_fill="#2a2139", ai_border="#5a3fa0",
        rule="#3fb950", rule_fill="#122117", rule_border="#2b5233",
        human="#d29922", human_fill="#272115", human_border="#6b5a1f",
        api="#4493f8", api_fill="#121d2f", api_border="#2b4a6f",
        red="#f85149", edge="#767d86"),
}

W, H = 1000, 640


def build(c):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}" '
         'role="img" aria-label="PlugPoint architecture. Forward path: a clinic note goes through '
         'exactly one AI step that extracts the action plan the clinician already made, then five '
         'deterministic rule checks. Routine plans go to a clinician for approval; blocked ones '
         'stop at a human decision — the system never guesses — and return once resolved. Only '
         'after approval do the mocked integrations act: orders, booking, patient message, EPR. '
         'Closing the loop: every item gets an expected-by date in the tracker, overdue items and '
         'at-risk appointments raise an alert to a named owner who chases, rebooks or resolves a '
         'hold, and the cycle repeats until results are reviewed and the loop closes. Every node '
         'carries the audit label it writes: AI, RULE, HUMAN, API or SYSTEM.">']
    s.append(
        '<defs>'
        + "".join(
            f'<marker id="a{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{v}"/></marker>'
            for k, v in (("", c["edge"]), ("g", c["rule"]), ("r", c["red"]), ("h", c["human"]))
        )
        + '</defs>'
    )

    def txt(x, y, t, size=11, fill=None, weight=None, anchor="start", mono=False, style=None):
        a = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"', f'fill="{fill or c["text"]}"']
        if weight: a.append(f'font-weight="{weight}"')
        if anchor != "start": a.append(f'text-anchor="{anchor}"')
        if mono: a.append(f'font-family="{MONO}"')
        if style: a.append(f'font-style="{style}"')
        s.append(f'<text {" ".join(a)}>{t}</text>')

    def panel(x, y, w, h, title):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
                 f'fill="{c["panel"]}" stroke="{c["border"]}"/>')
        txt(x + 18, y + 26, title, 11, c["muted"], "600")

    def node(cx, y, w, h, actor, title, sub=None):
        """actor: one of ai / rule / human / api / system"""
        if actor == "system":
            fill, stroke, acol = c["node"], c["border"], c["muted"]
        else:
            fill, stroke, acol = c[f"{actor}_fill"], c[f"{actor}_border"], c[actor]
        x = cx - w / 2
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                 f'fill="{fill}" stroke="{stroke}"/>')
        txt(cx, y + 19, actor.upper(), 9, acol, "700", "middle", mono=True)
        txt(cx, y + 39, title, 12.5, c["text"], "600", "middle")
        if sub:
            txt(cx, y + 56, sub, 10, c["muted"], anchor="middle")

    def line(pts, marker="a", col=None, dash=False):
        col = col or c["edge"]
        p = " ".join(f"{x},{y}" for x, y in pts)
        d = ' stroke-dasharray="5 4"' if dash else ""
        s.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="1.5"{d} '
                 f'marker-end="url(#{marker})"/>')

    # ── forward path ──────────────────────────────────────────────
    panel(16, 52, 968, 254, "THE FORWARD PATH &#183; NOTHING ACTS BEFORE APPROVAL")
    node(124, 104, 168, 68, "system", "Clinic note", "Tandem &#183; dictation")
    node(312, 104, 168, 68, "ai", "Extract the plan", "the one structured call")
    node(500, 104, 168, 68, "rule", "Five plan checks", "indication &#183; interval &#183; dates")
    node(688, 104, 168, 68, "human", "Approve", "editable &#183; one click")
    node(876, 104, 168, 68, "api", "Act", "orders &#183; booking &#183; SMS &#183; EPR")
    for gx in (208, 396) :
        line([(gx, 138), (gx + 32, 138)])
    line([(584, 138), (616, 138)], "ag", c["rule"])
    txt(600, 128, "routine", 9.5, c["rule"], "600", anchor="middle")
    line([(772, 138), (804, 138)], "ah", c["human"])
    txt(788, 128, "approved", 9.5, c["human"], "600", anchor="middle")

    # blocked branch
    line([(500, 172), (500, 208)], "ar", c["red"])
    txt(512, 194, "blocked", 9.5, c["red"], "600")
    node(500, 210, 220, 68, "human", "Decide", "choose interval &#183; add indication")
    line([(610, 244), (688, 244), (688, 176)], "ah", c["human"])
    txt(650, 236, "resolved", 9.5, c["human"], "600", anchor="middle")
    txt(190, 240, "&#10005; an ambiguous plan stops here.", 11, c["red"], "600", anchor="middle")
    txt(190, 258, "The system never guesses.", 11, c["red"], "600", anchor="middle")

    # ── closing the loop ──────────────────────────────────────────
    panel(16, 334, 968, 246, "CLOSING THE LOOP &#183; UNTIL THE RESULTS ARE REVIEWED")
    node(250, 392, 300, 68, "system", "Tracker",
         "expected-by dates &#183; overdue &#183; at risk &#183; on hold")
    node(560, 392, 240, 68, "human", "Alert to a named owner",
         "chase &#183; rebook &#183; resolve hold")
    node(860, 392, 200, 68, "rule", "Loop closed", "results reviewed")
    line([(400, 426), (438, 426)], "ah", c["human"])
    line([(680, 426), (758, 426)], "ag", c["rule"])
    # the chase cycle
    line([(560, 460), (560, 502), (250, 502), (250, 462)])
    txt(405, 496, "still open &#8212; chase again", 10, c["muted"], anchor="middle")
    txt(500, 546, "Every event is written to the audit trail with the label above it.",
        11, c["muted"], anchor="middle", style="italic")

    # ── rails, drawn last ─────────────────────────────────────────
    line([(876, 172), (876, 320), (250, 320), (250, 390)])
    txt(560, 314, "every item gets an expected-by date", 10, c["muted"], anchor="middle")

    txt(500, 614, "Exactly one AI step. Everything after it is rules, dates and state "
        "transitions &#8212; so the same note always behaves the same way.",
        12.5, c["ai"], "700", "middle")

    s.append("</svg>")
    return "\n".join(s)


os.makedirs("docs/images", exist_ok=True)
for name, pal in THEMES.items():
    p = f"docs/images/architecture-{name}.svg"
    open(p, "w", encoding="utf-8").write(build(pal))
    print("wrote", p)
