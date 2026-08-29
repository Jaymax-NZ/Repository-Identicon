#!/usr/bin/env python3
"""Generate the production system diagram for Repository-Identicon.

    python3 work-in-progress/system-diagram.py work-in-progress/system-diagram.html

One page per module. Every item is numbered `<page>.<item>` so it can be named
in a sentence; an off-page reference is a notched connector that links to the
item it names.

**Each item carries a signature, what it hands back, and one sentence.** That is
enforced here rather than left to judgement: `Col.box` takes exactly one `note`,
and a note that runs to a second sentence or overruns its column is reported on
stderr. The sentence says what the routine is *for*; what its terms *mean* is
the glossary's job, reachable by hovering any item.

Line numbers in the index are read from the sources at generation time, so they
cannot go stale silently.

Standard library only. Nothing here is imported by the tool.
"""

import html
import pathlib
import re
import sys

# ----------------------------------------------------------------- palette --
INK, MUTED, FAINT, LINE = "#15181c", "#6b7280", "#9aa2ab", "#5c636b"
BOXF, BOXS = "#f7f8fa", "#ccd2d9"
EXTF, EXTS = "#fdf6e7", "#a8761a"
DATF, DATS = "#eff1f4", "#aeb6bf"
REFF, REFS = "#eef1f5", "#7c8794"
VALF = "#15181c"
GRIDC, COLC = "#1d4ed8", "#c2410c"
WARN = "#b3261e"
BANDS = "#e4e9ee"

MONO_T, MONO_S, SANS_S = 6.9, 6.02, 5.2
SIG_H, LINE_H, PAD_T, PAD_B = 15.5, 12.6, 9, 9
NOTE_LIMIT = 130                      # characters; longer is not one sentence

NUM, ANCHOR, WHERE, TIPS = {}, {}, {}, {}
PAGES, WARNINGS = [], []

MARKS = {LINE: "a0", GRIDC: "a1", COLC: "a2", EXTS: "a3", VALF: "a4",
         FAINT: "a5", WARN: "a6"}


def esc(t):
    return html.escape(str(t), quote=True)


def _source_lines():
    """Where each top-level routine is written, read from the sources."""
    import ast
    here = pathlib.Path(__file__).resolve().parent
    found = {}
    for name in ("repository-identicon.py", "text-identicon.py"):
        path = here / name
        if not path.is_file():
            path = here.parent / name
        if not path.is_file():
            continue
        prefix = "" if name.startswith("repository") else "T:"
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                found[prefix + node.name] = (name, node.lineno)
    return found


LINES = _source_lines()


def _layout():
    """The hyphen-named layout module, loaded by path."""
    import importlib.util
    path = pathlib.Path(__file__).with_name("system-diagram-layout.py")
    spec = importlib.util.spec_from_file_location("diagram_layout", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_L = _layout()
COLUMNS, GROUPS, PLACED, ROUTES = _L.COLUMNS, _L.GROUPS, _L.PLACED, _L.ROUTES
PAGE_WIDTH = _L.PAGE_WIDTH

MAP_CAPTION = [
    "Reading the pages: 1 arrives at the key; 2 turns it into a pattern and a colour; "
    "3 turns it into names and canvas sizes; 4 turns those into bytes for six media, "
    "and 5 is the one of those",
    "six that lives in its own file. 6 and 7 are the two places the mark is put in "
    "front of a human. 8 is where the third one went. 9 touches none of the others: "
    "it runs somebody else's implementation",
    "and compares it with vectors.json.",
    "",
    "Hover any item for the meaning of the terms it uses. Out of scope and drawn "
    "nowhere: work-in-progress/, tests/ and reference/.",
]

# Items whose id is not the name of the routine they stand for. None means the
# item is a file, a value or a summary and has no single definition.
ALIAS = {"argh": "_key_from_args", "emit_seq": "cmd_emit", "hooks_cmd": "cmd_hooks",
         "t_text": "T:text", "t_encode": "T:_encode", "OCTANTS": None,
         "PALETTE": None, "RETURN_OF_CONTROL_EVENTS": None, "moved": None}


# ======================================================================= API =
class Page:
    def __init__(self, num, title, note, w=1400, h=600):
        self.num, self.title, self.note = num, title, note
        self.w, self.h = w, h
        self.nodes, self.edges, self.draw, self.over = {}, [], [], []
        self.links = []          # the logical edges, before routing
        self.groups = []         # (heading, note, [item key, ...]) in reading order
        self.captions = []       # (group heading or None, text)
        self.colx, self.gutter, self.n = [], 26, 0
        PAGES.append(self)

    # ------------------------------------------------------------- placing --
    def place(self, key, x, y, w, sig, ret="", note="", kind="fn", terms=(),
              effects=(), drives=(), number=True):
        """One item: a signature, what it hands back, and one sentence.

        The sentence is wrapped to the column here rather than by hand, so that
        rewording it never means re-flowing it. A note containing a newline is a
        listing laid out on purpose: it is split on its own breaks, left
        unwrapped, and exempt from the one-sentence rule.
        """
        sig = [sig] if isinstance(sig, str) else list(sig)
        laid_out = "\n" in note
        per = MONO_S if kind in ("ext", "data") else SANS_S
        room = int((w - 26) / per)

        def fold(text):
            if laid_out:
                return text.split("\n")
            out, line = [], ""
            for word in text.split():
                candidate = f"{line} {word}".strip()
                if len(candidate) > room and line:
                    out.append(line)
                    line = word
                else:
                    line = candidate
            return out + ([line] if line else [])

        # A routine with no `effects` is pure, and the absence is the statement:
        # nothing is drawn for it, so a page shows at a glance which routines
        # touch the world.
        body = ([f"→ {ret}"] if ret else []) + (fold(note) if note else [])
        body += [f"⊗ {e}" for e in effects]
        if drives:
            body.append("pages " + " · ".join(str(d) for d in drives))
        h = PAD_T + SIG_H * len(sig) + LINE_H * len(body) + PAD_B

        pad = 24 + (34 if number else 0)
        for s in sig:
            if len(s) * MONO_T + pad > w:
                WARNINGS.append(f"sig {key}: {len(s)}ch needs "
                                f"{len(s)*MONO_T+pad:.0f} > {w}")
        for line in body:
            if len(line) * per + 24 > w:
                WARNINGS.append(f"line {key}: {len(line)}ch needs "
                                f"{len(line)*per+24:.0f} > {w}  |{line}|")
        # The rule is one fact per sentence, not one sentence: a second short
        # fact -- usually a negation, "it does not open it" -- is clearer than
        # cramming both into a subordinate clause. Three is elaboration.
        if note and not laid_out:
            if len(note) > NOTE_LIMIT:
                WARNINGS.append(f"note {key}: {len(note)} chars, over {NOTE_LIMIT}")
            if len(re.findall(r"[.?!](?: |$)", note)) > 2:
                WARNINGS.append(f"note {key}: more than two sentences |{note}|")

        # `body` is wrapped for the column; `ret` and `note` are what was
        # written. Anything that is not laying out pixels wants the latter.
        node = dict(x=x, y=y, w=w, h=h, sig=sig, body=body, kind=kind, key=key,
                    terms=list(terms), ret=ret, note=note,
                    effects=list(effects), drives=list(drives))
        if self.groups:
            self.groups[-1][2].append(key)
        if number:
            self.n += 1
            NUM[key] = f"{self.num}.{self.n}"
            ANCHOR[key] = f"i{self.num}-{self.n}"
            node["label"] = NUM[key]
            node["anchor"] = ANCHOR[key]
            look = ALIAS.get(key, key)
            if look:
                src = LINES.get(look) or LINES.get("T:" + look)
                if src:
                    WHERE[key] = src
        self.nodes[key] = node
        return node

    def ref(self, key, target, direction, x, y, w, note=""):
        if len(note) * SANS_S + 92 > w:
            WARNINGS.append(f"ref {key}: {len(note)}ch too wide for {w}")
        self.nodes[key] = dict(x=x, y=y, w=w, h=34, kind="ref", target=target,
                               dir=direction, note=note, key=key, terms=[])
        if self.groups:
            self.groups[-1][2].append(key)
        return self.nodes[key]

    def group(self, heading, note=""):
        self.groups.append((heading, note, []))

    # -------------------------------------------------------------- edges ---
    def emit(self, d, colour=LINE, dash=None, wide=False):
        self.edges.append(dict(d=d, colour=colour, dash=dash, wide=wide))

    def at(self, key, side, t=0.5):
        n = self.nodes[key]
        if side == "l":
            return n["x"], round(n["y"] + n["h"] * t, 1)
        if side == "r":
            return n["x"] + n["w"], round(n["y"] + n["h"] * t, 1)
        if side == "t":
            return round(n["x"] + n["w"] * t, 1), n["y"]
        return round(n["x"] + n["w"] * t, 1), n["y"] + n["h"]

    def edge(self, a, aside, b, bside, colour=LINE, at=0.5, bt=0.5, dash=None,
             ext=18, mid=None, wide=False):
        self.links.append((a, b, aside + bside, colour, bool(dash),
                           dict(at=at, bt=bt, ext=ext, mid=mid, wide=wide)))
        (x1, y1), (x2, y2) = self.at(a, aside, at), self.at(b, bside, bt)
        hor = {"l", "r"}
        if aside in hor and bside in hor:
            if aside != bside and abs(y1 - y2) < 1.5:
                d = f"M{x1},{y1} L{x2},{y2}"
            elif aside != bside:
                m = mid if mid is not None else (x1 + x2) / 2
                d = f"M{x1},{y1} H{m} V{y2} H{x2}"
            else:
                m = mid if mid is not None else (
                    max(x1, x2) + ext if aside == "r" else min(x1, x2) - ext)
                d = f"M{x1},{y1} H{m} V{y2} H{x2}"
        elif aside not in hor and bside not in hor:
            if abs(x1 - x2) < 1.5:
                d = f"M{x1},{y1} L{x2},{y2}"
            elif aside != bside:
                m = mid if mid is not None else (y1 + y2) / 2
                d = f"M{x1},{y1} V{m} H{x2} V{y2}"
            else:
                m = mid if mid is not None else (
                    max(y1, y2) + ext if aside == "b" else min(y1, y2) - ext)
                d = f"M{x1},{y1} V{m} H{x2} V{y2}"
        elif aside in hor:
            d = f"M{x1},{y1} H{x2} V{y2}"
        else:
            d = f"M{x1},{y1} V{y2} H{x2}"
        self.emit(d, colour, dash, wide)

    # ------------------------------------------------------------- labels ---
    def gut(self, i):
        x, w = self.colx[i]
        return x + w + self.gutter / 2

    def head(self, x, y, text, note=""):
        self.draw.append(f'<text x="{x}" y="{y}" class="hd">{esc(text)}</text>')
        if note:
            self.draw.append(f'<text x="{x}" y="{y+14}" class="hn">{esc(note)}</text>')

    def caption(self, x, y, lines):
        """Loose prose on a page. Recorded against the group it follows, because
        the words are content even where the position is not."""
        self.captions.append((self.groups[-1][0] if self.groups else None,
                              " ".join(l for l in lines if l.strip())))
        for i, ln in enumerate(lines):
            self.draw.append(f'<text x="{x}" y="{y+i*12}" class="hn">{esc(ln)}</text>')

    def fit(self, margin=44):
        low = 0
        for n in self.nodes.values():
            low = max(low, n["y"] + n["h"])
        for d in self.draw:
            found = re.findall(r'y="([0-9.]+)"', d)
            if found:
                low = max(low, max(float(v) for v in found))
        self.h = round(low + margin)


class Col:
    def __init__(self, page, x, w, y):
        self.p, self.x, self.w, self.y = page, x, w, y

    def gap(self, n=15):
        self.y += n

    def box(self, key, sig, ret="", note="", kind="fn", terms=(), effects=(),
            drives=(), gap=10):
        n = self.p.place(key, self.x, self.y, self.w, sig, ret, note, kind,
                         terms, effects, drives)
        self.y += n["h"] + gap
        return n

    def ref(self, key, target, direction, note="", gap=10):
        n = self.p.ref(key, target, direction, self.x, self.y, self.w, note)
        self.y += n["h"] + gap
        return n

    def head(self, text, note="", gap=8):
        self.p.group(text, note)
        self.p.head(self.x, self.y + 11, text, note)
        self.y += 16 + (12 if note else 0)
        self.p.draw.append(f'<line x1="{self.x}" y1="{self.y+3}" '
                           f'x2="{self.x+self.w}" y2="{self.y+3}" class="rule"/>')
        self.y += gap


def cols(page, widths, y=40, gutter=26, x0=32):
    out, x = [], x0
    page.colx, page.gutter = [], gutter
    for w in widths:
        out.append(Col(page, x, w, y))
        page.colx.append((x, w))
        x += w + gutter
    page.w = max(page.w, x - gutter + x0)
    return out


# ================================================================ THE TERMS =
# The glossary. Every `terms=` on a box names rows from here, and those rows
# become that box's hover text -- which is why no item restates a definition.

TERMS = []          # filled from the `terms` section of the document



# ================================================================== SOURCE ==
#
# `system-diagram.mr` is the source of everything the diagram says.
# `system-diagram-layout.py` is the source of where it goes. Nothing below
# invents content, and nothing in the MarkRight document knows a pixel.
#
# The reader is written out here rather than importing MarkRight, because this
# repository is a specification and must stay standalone. The format it reads is
# the whole of MarkRight's line grammar: a rail of one repeated glyph, one
# marker, and the text.

HEAVY, LIGHT = "┋", "┊"
NODE, BLANK_NODE, META = "━", "┅", "┄"
SEPARATORS = set("          "
                 "  　\t")
SIGILS = {"⸈": "expansion", "⸋": "internal", "⸖": "external",
          "⸲": "comment", "⸆": "description"}


class MRNode:
    __slots__ = ("depth", "kind", "form", "text", "children")

    def __init__(self, depth, kind, form, text):
        self.depth, self.kind, self.form, self.text = depth, kind, form, text
        self.children = []

    # -- reading the metanodes hanging off this node ------------------------
    def attr(self, name, default=None):
        for child in self.children:
            if child.form == "external" and child.text.startswith(name + "="):
                return child.text[len(name) + 1:]
        return default

    def attrs(self, name):
        return [c.text[len(name) + 1:] for c in self.children
                if c.form == "external" and c.text.startswith(name + "=")]

    def notes(self):
        return [c.text for c in self.children if c.form == "description"]

    def kids(self):
        return [c for c in self.children if c.kind == "node"]


def read_markright(source):
    """The document as a forest of MRNode. Roots are the peer sections."""
    roots, stack = [], []
    for raw in source.splitlines():
        if not raw or raw[0] == "␁":
            continue
        depth = 0
        while depth < len(raw) and raw[depth] in (HEAVY, LIGHT):
            depth += 1
        rest = raw[depth:]
        while rest and rest[0] in SEPARATORS:
            rest = rest[1:]
        if not rest:
            continue
        marker, rest = rest[0], rest[1:]
        while rest and rest[0] in SEPARATORS:
            rest = rest[1:]
        if marker in (NODE, BLANK_NODE):
            kind, form = "node", None
        elif marker == META:
            kind = "metanode"
            form = SIGILS.get(rest[:1])
            if form:
                rest = rest[1:]
                while rest and rest[0] in SEPARATORS:
                    rest = rest[1:]
        else:
            continue                      # a break marker carries no structure
        node = MRNode(depth, kind, form, rest)
        while stack and stack[-1].depth >= depth:
            stack.pop()
        (stack[-1].children if stack else roots).append(node)
        stack.append(node)
    return roots


# ================================================================== BUILDING ==

KIND_OF = {"fn": "fn", "ext": "ext", "data": "data", "val": "val", "cmd": "cmd",
           "thin": "thin", "grid": "grid", "col": "col", "dead": "dead"}
CARRIES = {"calls": LINE, "grid": GRIDC, "colour": COLC, "io": EXTS,
           "weak": FAINT, "value": VALF, "raises": WARN}

SOURCE = pathlib.Path(__file__).with_name("system-diagram.mr")
DOC = read_markright(SOURCE.read_text(encoding="utf-8"))
SECTION = {n.attr("$section"): n for n in DOC if n.attr("$section")}

for group in SECTION["terms"].kids():
    entries = []
    for term in group.kids():
        entries.append((term.text, (term.notes() or [""])[0],
                        term.attrs("$defines")))
    TERMS.append((group.text, entries))
for _g, _entries in TERMS:
    for _t, _m, _ in _entries:
        TIPS[_t] = _m


def carries(value):
    return CARRIES.get(value.split()[0], LINE), "dashed" in value


def add_item(page, node, x, y, w):
    """One item from the document, at a position layout chose."""
    key = node.attr("$fn", node.text)
    offpage = node.attr("$offpage")
    if offpage:
        page.ref(key, node.attr("$target"), offpage, x, y, w,
                 (node.notes() or [""])[0])
        return
    module = node.attr("$module")
    if module:
        page.nodes[key] = dict(x=x, y=y, w=w, h=76, kind="module",
                               page=int(module), title=node.text,
                               note=(node.notes() or [""])[0], key=key, terms=[])
        return

    sig = [node.text] + node.attrs("$signature")
    ret, effects = "", []
    for child in node.kids():
        role = child.attr("$role")
        if role == "returns":
            ret = " · ".join(v.text for v in child.kids())
        elif role == "effects":
            effects = [v.text for v in child.kids()]
    note = "\n".join(node.notes())
    number = node.attr("$number")
    item = page.place(key, x, y, w, sig, ret, note,
                      KIND_OF.get(node.attr("$kind", "fn"), "fn"),
                      node.attrs("$term"), effects, node.attrs("$drives"),
                      number=False)
    if number:
        NUM[key] = number
        ANCHOR[key] = "i" + number.replace(".", "-")
        item["label"], item["anchor"] = number, ANCHOR[key]
        src = node.attr("$source")
        if src:
            WHERE[key] = tuple(src.rsplit(":", 1))


def add_edges(page, node):
    """The edges written under one item, routed by the layout table."""
    key = node.attr("$fn", node.text)
    targets = node.attrs("$edge")
    sides = node.attrs("$sides")
    kinds = node.attrs("$carries")
    seen = {}
    for target, side, kind in zip(targets, sides, kinds):
        seen[(key, target)] = seen.get((key, target), -1) + 1
        route = dict(ROUTES.get((page.num, key, target, seen[(key, target)]), {}))
        route.pop("sides", None)
        colour, dashed = carries(kind)
        if target not in page.nodes:
            WARNINGS.append(f"edge to a missing item: {page.num} {key} → {target}")
            continue
        page.edge(key, side[0], target, side[1], colour,
                  dash="4 3" if dashed else None, **route)


def build_process_pages():
    for pnode in SECTION["processes"].kids():
        num = int(pnode.attr("$page"))
        page = Page(num, pnode.text, (pnode.notes() or [""])[0], PAGE_WIDTH[num])
        columns = cols(page, COLUMNS[num])
        written = []
        for gnode in pnode.kids():
            column = columns[GROUPS[num][gnode.text]]
            notes = gnode.notes()
            column.head(gnode.text, notes[0] if notes else "")
            for item in gnode.kids():
                add_item(page, item, column.x, column.y, column.w)
                column.y += page.nodes[item.attr("$fn", item.text)]["h"] + 10
                written.append(item)
            for extra in notes[1:]:
                page.caption(column.x, column.y + 6, wrap_caption(extra, column.w))
                column.y += 12 * len(wrap_caption(extra, column.w))
        for item in written:
            add_edges(page, item)
        page.fit(56 if num == 4 else 44)


def build_map():
    """Page 0: the modules, and the command line, both hand-placed."""
    page = Page(0, "The map",
                "the modules, the seven subcommands, and which page each lands on",
                PAGE_WIDTH[0])
    placed = PLACED[0]
    for section, depth in (("subcommands", 2), ("overview", 1)):
        node = SECTION[section]
        for entry in node.kids():
            candidates = entry.kids() if depth == 2 else [entry]
            for item in candidates:
                key = item.attr("$fn", item.text)
                if key in placed:
                    add_item(page, item, *placed[key])
    hands = {}
    for entry in SECTION["overview"].kids():
        key = entry.attr("$fn")
        pairs = list(zip(entry.attrs("$hands"), entry.attrs("$carries")))
        hands[key] = pairs
    bypage = {n["page"]: k for k, n in page.nodes.items() if n["kind"] == "module"}
    for key, pairs in hands.items():
        seen = {}
        for to, kind in pairs:
            target = bypage[int(to)]
            seen[(key, target)] = seen.get((key, target), -1) + 1
            route = dict(ROUTES.get((0, key, target, seen[(key, target)]), {}))
            sides = route.pop("sides", "rl")
            colour, dashed = carries(kind)
            page.edge(key, sides[0], target, sides[1], colour,
                      dash="4 3" if dashed else None, **route)
    page.head(32, 268, "THE THROUGH-LINE")
    page.draw.append('<text x="378" y="326" class="elab">key</text>')
    page.draw.append('<text x="205" y="418" class="elab">key</text>')
    page.draw.append('<text x="948" y="424" class="elabg">grid, colour</text>')
    page.caption(32, 610, MAP_CAPTION)
    page.fit()


def wrap_caption(text, width):
    room = int((width - 12) / SANS_S)
    out, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if len(candidate) > room and line:
            out.append(line)
            line = word
        else:
            line = candidate
    return out + ([line] if line else [])


build_map()
build_process_pages()

# The one defect the diagram marks, and the only annotation that is neither
# content nor layout: a claim about the code that the code disagrees with.
_p4 = next(p for p in PAGES if p.num == 4)
_rl = _p4.nodes["render_line"]
_p4.over.append(f'<circle cx="{_rl["x"]+_rl["w"]-16}" cy="{_rl["y"]+16}" r="8" '
                f'fill="{WARN}"/>')
_p4.over.append(f'<text x="{_rl["x"]+_rl["w"]-16}" y="{_rl["y"]+20.5}" '
                f'class="wt">!</text>')
_p4.over.append(f'<text x="{_rl["x"]}" y="{_rl["y"]+_rl["h"]+13}" class="wn">'
                '! calls emoji_triple(colour) with one argument; 5.4 takes '
                '(rgb, grid)</text>')


# =================================================================== RENDER ==
def tooltip(n):
    """The glossary entries this item's terms name, as native hover text."""
    lines = []
    for term in n.get("terms", []):
        if term not in TIPS:
            WARNINGS.append(f"unknown term on {n['key']}: {term}")
            continue
        lines.append(f"{term} — {TIPS[term]}")
    if not lines:
        return ""
    return "<title>" + esc("\n".join(lines)) + "</title>"


def render_node(n):
    out, kind = [], n["kind"]
    if kind == "ref":
        num, anc = NUM.get(n["target"], "?"), ANCHOR.get(n["target"], "")
        x, y, w, h, notch = n["x"], n["y"], n["w"], n["h"], 12
        if n["dir"] == "out":
            d, tx = f"M{x},{y} H{x+w-notch} L{x+w},{y+h/2} L{x+w-notch},{y+h} H{x} Z", x + 12
        else:
            d, tx = f"M{x+notch},{y} H{x+w} V{y+h} H{x+notch} L{x},{y+h/2} Z", x + notch + 10
        out.append(f'<a href="#{anc}"><path d="{d}" class="bref"/>'
                   f'<text x="{tx}" y="{y+21}" class="refn">{esc(num)}</text>'
                   f'<text x="{tx+34}" y="{y+21}" class="reft">{esc(n["note"])}</text></a>')
        return out
    if kind == "module":
        x, y, w = n["x"], n["y"], n["w"]
        out.append(f'<a href="#page-{n["page"]}">'
                   f'<rect x="{x}" y="{y}" width="{w}" height="{n["h"]}" rx="6" class="bmod"/>'
                   f'<text x="{x+14}" y="{y+27}" class="modn">PAGE {n["page"]}</text>'
                   f'<text x="{x+14}" y="{y+48}" class="modt">{esc(n["title"])}</text>'
                   f'<text x="{x+14}" y="{y+65}" class="modx">{esc(n["note"])}</text></a>')
        return out

    cls, tcls, bcls = {
        "fn": ("bfn", "ti", "sb"), "ext": ("bext", "tie", "sbe"),
        "val": ("bval", "tiw", "sbw"), "cmd": ("bcmd", "ticm", "sb"),
        "thin": ("bthin", "ti", "sb"), "data": ("bdata", "tid", "sbd"),
        "grid": ("bgrid", "tig", "sb"), "col": ("bcol", "tic", "sb"),
    }[kind]
    rx = 10 if kind == "val" else (6 if kind == "cmd" else 5)
    anc = n.get("anchor", "")
    out.append(f'<g id="{anc}" class="item">' if anc else '<g class="item">')
    out.append(tooltip(n))
    out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" '
               f'rx="{rx}" class="{cls}"/>')
    tx = n["x"] + 12
    if "label" in n:
        out.append(f'<text x="{n["x"]+12}" y="{n["y"]+PAD_T+11}" '
                   f'class="{"badgew" if kind == "val" else "badge"}">{esc(n["label"])}</text>')
        tx = n["x"] + 12 + (34 if len(n["label"]) < 5 else 40)
    # A wrapped signature aligns under its own opening bracket. The document
    # stores the parameters, not the whitespace, so the indent is computed.
    hang = n["sig"][0].find("(") + 1
    for i, s in enumerate(n["sig"]):
        if i and hang > 0:
            s = " " * hang + s
        out.append(f'<text xml:space="preserve" x="{tx if i == 0 else n["x"]+12}" '
                   f'y="{n["y"]+PAD_T+11+i*SIG_H}" class="{tcls}">{esc(s)}</text>')
    y0 = n["y"] + PAD_T + SIG_H * len(n["sig"]) + 10
    for i, line in enumerate(n["body"]):
        cl = "ret" if line.startswith("→") else bcls
        out.append(f'<text xml:space="preserve" x="{n["x"]+12}" y="{y0+i*LINE_H}" '
                   f'class="{cl}">{esc(line)}</text>')
    out.append("</g>")
    return out


STYLE = f"""
 .hd {{ font-size: 12px; font-weight: 700; fill: {MUTED}; letter-spacing: .1em; }}
 .hn {{ font-size: 11px; fill: {FAINT}; }}
 .rule {{ stroke: {BANDS}; stroke-width: 1; }}
 .bfn {{ fill: {BOXF}; stroke: {BOXS}; stroke-width: 1; }}
 .bext {{ fill: {EXTF}; stroke: {EXTS}; stroke-width: 1; stroke-dasharray: 4 2.5; }}
 .bdata {{ fill: {DATF}; stroke: {DATS}; stroke-width: 1; }}
 .bval {{ fill: {VALF}; stroke: {VALF}; }}
 .bcmd {{ fill: #ffffff; stroke: {INK}; stroke-width: 1.3; }}
 .bthin {{ fill: #ffffff; stroke: {BOXS}; stroke-width: 1; }}
 .bgrid {{ fill: #eef2ff; stroke: {GRIDC}; stroke-width: 1.3; }}
 .bcol {{ fill: #fff3ea; stroke: {COLC}; stroke-width: 1.3; }}
 .bref {{ fill: {REFF}; stroke: {REFS}; stroke-width: 1.2; }}
 .bmod {{ fill: #ffffff; stroke: {INK}; stroke-width: 1.4; }}
 .item[data-t] {{ cursor: help; }}
 .modn {{ font-size: 11px; font-weight: 700; fill: {FAINT}; letter-spacing: .12em; }}
 .modt {{ font-size: 15px; font-weight: 650; fill: {INK}; }}
 .modx {{ font-size: 11px; fill: {MUTED}; }}
 .badge, .badgew, .refn, .ti, .tiw, .tie, .tid, .tig, .tic, .ticm, .sbe, .sbd, .ret, .wn
   {{ font-family: ui-monospace, "DejaVu Sans Mono", monospace; }}
 .badge {{ font-size: 11px; font-weight: 700; fill: {FAINT}; }}
 .badgew {{ font-size: 11px; font-weight: 700; fill: #7f8894; }}
 .refn {{ font-size: 12px; font-weight: 700; fill: {INK}; }}
 .reft {{ font-size: 11px; fill: {MUTED}; }}
 .ti {{ font-size: 11.5px; fill: {INK}; }}
 .tiw {{ font-size: 11.5px; fill: #ffffff; }}
 .tie {{ font-size: 11.5px; fill: #7a5510; }}
 .tid {{ font-size: 11.5px; fill: #4a515a; }}
 .tig {{ font-size: 11.5px; fill: {GRIDC}; font-weight: 600; }}
 .tic {{ font-size: 11.5px; fill: {COLC}; font-weight: 600; }}
 .ticm {{ font-size: 12.5px; fill: {INK}; font-weight: 600; }}
 .ret {{ font-size: 10.5px; fill: #3f6212; }}
 .sb {{ font-size: 10.5px; fill: {MUTED}; }}
 .sbw {{ font-size: 10.5px; fill: #b9c0c8; }}
 .sbe {{ font-size: 10px; fill: #8a6414; }}
 .sbd {{ font-size: 10px; fill: #667081; }}
 .wt {{ font-size: 11.5px; font-weight: 700; fill: #ffffff; text-anchor: middle; }}
 .wn {{ font-size: 10px; fill: {WARN}; }}
 .elab {{ font-family: ui-monospace, monospace; font-size: 10.5px; fill: {MUTED}; }}
 .elabg {{ font-family: ui-monospace, monospace; font-size: 10.5px; fill: {GRIDC}; }}
"""


def svg_for(p):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {p.w} {p.h}" '
             f'width="{p.w}" height="{p.h}" '
             f'font-family="ui-sans-serif, system-ui, sans-serif" class="sheet">', "<defs>"]
    for col, mid in MARKS.items():
        parts.append(f'<marker id="{mid}p{p.num}" viewBox="0 0 10 10" refX="9" refY="5" '
                     f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
                     f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    parts.append(f"</defs><style>{STYLE}</style>")
    parts.append(f'<rect width="{p.w}" height="{p.h}" fill="#ffffff"/>')
    parts.extend(p.draw)
    for e in p.edges:
        dash = f' stroke-dasharray="{e["dash"]}"' if e["dash"] else ""
        parts.append(f'<path d="{e["d"]}" fill="none" stroke="{e["colour"]}" '
                     f'stroke-width="{1.8 if e["wide"] else 1.15}"{dash} '
                     f'stroke-linejoin="round" marker-end="url(#{MARKS[e["colour"]]}p{p.num})"/>')
    for n in p.nodes.values():
        parts.extend(render_node(n))
    parts.extend(p.over)
    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------- the tables --
def term_where(numbers):
    """`$defines` names items by number, which is how a reader would cite them."""
    known = {number: key for key, number in NUM.items()}
    out = []
    for number in numbers:
        if number not in known:
            WARNINGS.append(f"glossary points at a missing item: {number}")
            continue
        out.append(f'<a href="#{ANCHOR[known[number]]}">{number}</a>')
    return " · ".join(out)


gloss = []
for group, entries in TERMS:
    gloss.append(f'<tr class="g"><td colspan="3">{esc(group)}</td></tr>')
    for term, meaning, keys in entries:
        gloss.append(f'<tr><td class="t">{esc(term)}</td><td class="d">{esc(meaning)}</td>'
                     f'<td class="n">{term_where(keys)}</td></tr>')

rows = []
for p in PAGES:
    for n in p.nodes.values():
        if "label" not in n:
            continue
        src = WHERE.get(n["key"])
        rows.append((n["label"], n["sig"][0].strip(),
                     f'{src[0]}:{src[1]}' if src else "—", n.get("anchor", "")))
rows.sort(key=lambda r: (int(r[0].split(".")[0]), int(r[0].split(".")[1])))

nav = " · ".join(f'<a href="#page-{p.num}">{p.num}. {esc(p.title)}</a>' for p in PAGES)
body = [f"""<h1>Repository-Identicon — the production system</h1>
<p class="lede">Every top-level routine in <code>repository-identicon.py</code> and
<code>text-identicon.py</code>, one page per module. Each item gives its signature, what it
hands back, and one sentence saying what it is <em>for</em>. What its terms <em>mean</em> is
the glossary's job — <strong>hover any item</strong> for the entries it uses, or read
<a href="#terms">Terms</a> straight through.</p>
<p class="lede">Items are numbered <code>page.item</code> so they can be named in a sentence.
A notched connector is an off-page reference: click it to jump to the item it names. An arrow
points the way the work goes. Out of scope and drawn nowhere:
<code>work-in-progress/</code>, <code>tests/</code> and <code>reference/</code>.</p>
<nav>{nav} · <a href="#terms">Terms</a> · <a href="#index">Index</a></nav>
<div class="key">
  <span><i class="k-fn"></i>a routine</span>
  <span><i class="k-data"></i>a table, or a summary</span>
  <span><i class="k-ext"></i>outside the program</span>
  <span><i class="k-val"></i>a value in flight</span>
  <span><svg width="30" height="16" viewBox="0 0 30 16"><path d="M0,0 H22 L30,8 L22,16 H0 Z"
      fill="{REFF}" stroke="{REFS}"/></svg>an off-page reference, and a link</span>
  <span><i class="k-l0"></i>calls, or hands on</span>
  <span><i class="k-l1"></i>carries the grid</span>
  <span><i class="k-l2"></i>carries the colour</span>
  <span><i class="k-l3"></i>reads or writes</span>
</div>"""]
for p in PAGES:
    body.append(f'<section id="page-{p.num}"><h2><span class="pn">{p.num}</span>'
                f'{esc(p.title)}</h2><p class="note">{esc(p.note)}</p>'
                f'<div class="scroll">{svg_for(p)}</div></section>')

body.append('<section id="terms"><h2><span class="pn">·</span>Terms</h2>'
            '<p class="note">the words this repository uses in a particular way. No item on '
            'a page restates one of these; it points at them instead.</p>'
            '<table class="gloss"><thead><tr><th>term</th><th>what it means here</th>'
            '<th>where</th></tr></thead><tbody>' + "\n".join(gloss) + '</tbody></table></section>')

trs = "\n".join(f'<tr><td class="n"><a href="#{a}">{esc(lbl)}</a></td>'
                f'<td class="s">{esc(sig)}</td><td class="w">{esc(where)}</td></tr>'
                for lbl, sig, where, a in rows)
body.append(f'<section id="index"><h2><span class="pn">·</span>Index</h2>'
            f'<p class="note">every numbered item, with where it is written</p>'
            f'<table><thead><tr><th>#</th><th>item</th><th>source</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></section>')

PAGE_CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 28px 32px 80px; background: #ffffff; color: {INK};
        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
h1 {{ font-size: 27px; margin: 0 0 12px; font-weight: 650; letter-spacing: -.01em; }}
.lede {{ max-width: 100ch; color: {MUTED}; font-size: 13.5px; line-height: 1.55;
         margin: 0 0 10px; }}
code {{ font-family: ui-monospace, "DejaVu Sans Mono", monospace; font-size: .92em;
        background: #f2f4f6; padding: 1px 4px; border-radius: 3px; }}
nav {{ margin: 16px 0 14px; font-size: 12.5px; line-height: 2; }}
nav a {{ color: {INK}; text-decoration: none; border-bottom: 1px solid #d5dae0; }}
nav a:hover {{ border-bottom-color: {INK}; }}
.key {{ display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: 11.5px; color: {MUTED};
        border-top: 1px solid {BANDS}; border-bottom: 1px solid {BANDS};
        padding: 10px 0; margin-bottom: 22px; }}
.key span {{ display: inline-flex; align-items: center; gap: 7px; }}
.key i {{ width: 24px; height: 14px; border-radius: 4px; display: inline-block; }}
.k-fn {{ background: {BOXF}; border: 1px solid {BOXS}; }}
.k-data {{ background: {DATF}; border: 1px solid {DATS}; }}
.k-ext {{ background: {EXTF}; border: 1px dashed {EXTS}; }}
.k-val {{ background: {VALF}; border-radius: 7px !important; }}
.k-l0 {{ height: 0 !important; border-top: 2px solid {LINE}; border-radius: 0 !important; }}
.k-l1 {{ height: 0 !important; border-top: 2px solid {GRIDC}; border-radius: 0 !important; }}
.k-l2 {{ height: 0 !important; border-top: 2px solid {COLC}; border-radius: 0 !important; }}
.k-l3 {{ height: 0 !important; border-top: 2px solid {EXTS}; border-radius: 0 !important; }}
section {{ margin: 0 0 44px; scroll-margin-top: 16px; }}
h2 {{ font-size: 19px; margin: 0 0 4px; font-weight: 650; display: flex;
      align-items: baseline; gap: 12px; }}
.pn {{ display: inline-block; min-width: 30px; text-align: center; font-size: 13px;
       font-weight: 700; color: #ffffff; background: {INK}; border-radius: 5px;
       padding: 2px 7px; }}
.note {{ color: {MUTED}; font-size: 12.5px; margin: 0 0 12px; max-width: 118ch; }}
.scroll {{ overflow-x: auto; border: 1px solid {BANDS}; border-radius: 8px; }}
svg.sheet {{ display: block; max-width: none; }}
svg a {{ cursor: pointer; }}
svg a:hover .bref {{ fill: #dde3ea; }}
g[id]:target rect {{ stroke: {WARN}; stroke-width: 2.4; }}
table {{ border-collapse: collapse; font-size: 12px; }}
th, td {{ text-align: left; padding: 3px 18px 3px 0; border-bottom: 1px solid #eef1f4; }}
th {{ color: {FAINT}; font-weight: 600; font-size: 11px; letter-spacing: .06em;
      text-transform: uppercase; }}
td.n {{ font-family: ui-monospace, monospace; font-weight: 700; white-space: nowrap; }}
td.n a {{ color: {INK}; text-decoration: none; }}
td.s {{ font-family: ui-monospace, monospace; }}
td.w {{ font-family: ui-monospace, monospace; color: {FAINT}; white-space: nowrap; }}
table.gloss {{ max-width: 130ch; }}
table.gloss tr.g td {{ padding-top: 18px; font-size: 11px; font-weight: 700;
      letter-spacing: .1em; text-transform: uppercase; color: {FAINT};
      border-bottom: 1px solid {BANDS}; }}
td.t {{ font-family: ui-monospace, monospace; font-weight: 600; white-space: nowrap;
        vertical-align: top; padding-top: 6px; }}
td.d {{ font-size: 12.5px; line-height: 1.5; color: {MUTED}; padding: 6px 24px 6px 0;
        max-width: 92ch; }}
table.gloss td.n {{ vertical-align: top; padding-top: 7px; font-weight: 400; }}
"""

doc = ("<title>Repository-Identicon system diagram</title>\n"
       f"<style>{PAGE_CSS}</style>\n" + "\n".join(body))


target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "system-diagram.html")
target.write_text(doc, encoding="utf-8")
print(f"wrote {target}  pages={len(PAGES)} items={len(rows)} terms={len(TIPS)}")
for w in WARNINGS:
    print("  !", w, file=sys.stderr)
