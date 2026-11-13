"""fourfold ceiling agent: a scripted cell that maps the grid as fast as the interface allows.

what it does    respond(system, prompt) -> reply text, in the harness's own tick and quiz formats.
                it is a pure function of the two prompt strings; all memory is the <protocol> notebook.
when to use     as the upper reference for fourfold quiz scores (the echo agent is the lower one).
what it means   a quiz score of 1.0 from this agent shows the scorer's maximum is reachable through
                the ports by that tick. it never states a link or a map cell it has not been told;
                unknowns are written as "not known yet" / "?".
test it passes  analysis/ceiling_check.py (prereg/ceiling.md C1-C6, prereg/ceiling_widths.md D1-D5).

the shared code. a port carries H hex characters per tick (32 at the default 128 bits), and each
message is spread over as many ticks as it needs:
  header   "f" + the port number it is written on + own id (8 hex)          ceil(10 / H) ticks, from tick 1
  star     the ids of the writer's other neighbours (up to 3), zero padded  ceil(24 / H) ticks, straight after
  square   four ids forming one unit square of the grid, in cycle order     32 / H ticks each, after that
between squares an all-zero tick means "nothing to send". a square whose every id starts with a
zero tick is sent as 32 "f" characters followed by the square with every character inverted.
"""

from __future__ import annotations

import itertools
import re

NOID = "0" * 8
DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))
UNKNOWN = "not known yet"
ESCAPE = "f" * 32
USE_ESCAPE = True  # analysis/ceiling_check.py turns this off to show the escape is needed


def phases(h: int) -> tuple:
    """(ticks for the header, ticks for the star) at h hex characters per tick."""
    return -(-10 // h), -(-24 // h)


def invert(s: str) -> str:
    return "".join(f"{15 - int(c, 16):x}" for c in s)


# ---------------------------------------------------------------- reading the prompts


def parse_prompt(system: str, prompt: str) -> dict:
    me = re.search(r"a random value has been assigned to you: ([0-9a-f]{8})", system)
    if not me:
        raise ValueError("system prompt carries no id")
    width = re.search(r"shown as (\d+) hex", system)
    if not width or 32 % int(width.group(1)):
        raise ValueError("system prompt carries no usable port width")
    h = int(width.group(1))
    quiz = "the evaluation is over" in prompt
    m = re.search(r"after tick (\d+)" if quiz else r"^tick (\d+)", prompt, re.M)
    if not m:
        raise ValueError("prompt carries no tick number")
    inputs = []
    for i in range(4):
        v = re.search(rf"^p{i} ([0-9a-f]{{{h}}})\b", prompt, re.M)
        if not v:
            raise ValueError(f"prompt carries no value for p{i}")
        inputs.append(v.group(1))
    p = re.search(r"\nprotocol:\n(.*?)\n\nrecent log:", prompt, re.S)
    if not p:
        raise ValueError("prompt carries no protocol section")
    return {"me": me.group(1), "h": h, "quiz": quiz, "t": int(m.group(1)), "inputs": inputs, "protocol": p.group(1).strip()}


# ---------------------------------------------------------------- the notebook


class Book:
    """everything the cell knows. ids are held in first-seen order; edges and squares use indices."""

    def __init__(self, me: str):
        self.ids = [me]
        self.ports: list = [None] * 4  # None = not known, "dead", or (neighbour id, its port)
        self.edges: set = set()  # frozenset({i, j})
        self.sent: list = [[] for _ in range(4)]  # square keys, most recent last
        self.got: list = [set() for _ in range(4)]
        self.rx: list = [""] * 4  # characters of the message now arriving on each port
        self.tx: list = [""] * 4  # characters of the message now leaving on each port, not yet written
        self.inv: list = [False] * 4  # the next square arriving on this port is inverted

    def idx(self, ident: str) -> int:
        if ident not in self.ids:
            self.ids.append(ident)
        return self.ids.index(ident)

    def link(self, a: str, b: str):
        if a != b:
            self.edges.add(frozenset((self.idx(a), self.idx(b))))

    def adj(self) -> dict:
        out: dict = {i: set() for i in range(len(self.ids))}
        for e in self.edges:
            a, b = tuple(e)
            out[a].add(b)
            out[b].add(a)
        return out

    def squares(self) -> dict:
        """every 4-cycle in the known links -> {sorted key: cycle order}. in a grid these are the unit squares."""
        adj, out = self.adj(), {}
        for a, c in itertools.combinations(range(len(self.ids)), 2):
            for b, d in itertools.combinations(sorted(adj[a] & adj[c]), 2):
                out.setdefault(tuple(sorted((a, b, c, d))), (a, b, c, d))
        return out

    def dump(self) -> str:
        key = lambda k: ".".join(map(str, k))
        lines = ["fourfold-ceiling notebook v2", f"me {self.ids[0]}"]
        for i, p in enumerate(self.ports):
            lines.append(f"p{i} " + ("?" if p is None else p if p == "dead" else f"{p[0]} {p[1]}"))
        lines.append("ids " + " ".join(self.ids))
        lines.append("edges " + " ".join(sorted("-".join(map(str, sorted(e))) for e in self.edges)))
        for i in range(4):
            lines.append(f"sent{i} " + " ".join(key(k) for k in self.sent[i]))
            lines.append(f"got{i} " + " ".join(sorted(key(k) for k in self.got[i])))
            if self.rx[i] or self.tx[i] or self.inv[i]:
                lines.append(f"wire{i} in:{self.rx[i] or '-'} out:{self.tx[i] or '-'} inverted:{int(self.inv[i])}")
        return "\n".join(l.rstrip() for l in lines)

    @classmethod
    def load(cls, me: str, text: str) -> "Book":
        b = cls(me)
        if not text or text == "(empty)":
            return b
        unkey = lambda s: tuple(int(x) for x in s.split("."))
        for line in text.splitlines():
            w = line.split()
            if not w:
                continue
            if w[0] == "me" and w[1] != me:
                raise ValueError("notebook belongs to another cell")
            if re.fullmatch(r"p[0-3]", w[0]):
                i = int(w[0][1])
                b.ports[i] = None if w[1] == "?" else "dead" if w[1] == "dead" else (w[1], int(w[2]))
            elif w[0] == "ids":
                b.ids = w[1:]
            elif w[0] == "edges":
                b.edges = {frozenset(int(x) for x in e.split("-")) for e in w[1:]}
            elif re.fullmatch(r"sent[0-3]", w[0]):
                b.sent[int(w[0][4])] = [unkey(s) for s in w[1:]]
            elif re.fullmatch(r"got[0-3]", w[0]):
                b.got[int(w[0][3])] = {unkey(s) for s in w[1:]}
            elif re.fullmatch(r"wire[0-3]", w[0]):
                i, part = int(w[0][4]), dict(x.split(":") for x in w[1:])
                b.rx[i] = "" if part["in"] == "-" else part["in"]
                b.tx[i] = "" if part["out"] == "-" else part["out"]
                b.inv[i] = part["inverted"] == "1"
        return b


def absorb(b: Book, inputs: list, written_at: int, h: int):
    """take in the four input values, read as what the neighbours wrote at tick `written_at`."""
    me = b.ids[0]
    head, star = phases(h)
    if written_at <= 0:
        return
    for i, v in enumerate(inputs):
        if written_at <= head:  # header. a dead port reads zero throughout; a live one starts with "f"
            b.rx[i] += v
            if written_at == head:
                got, b.rx[i] = b.rx[i], ""
                if not got.strip("0"):
                    b.ports[i] = "dead"
                elif got[0] == "f" and got[1] in "0123":
                    b.ports[i] = (got[2:10], int(got[1]))
                    b.link(me, got[2:10])
            continue
        if not isinstance(b.ports[i], tuple):
            continue
        if written_at <= head + star:  # star: the neighbour's other neighbours
            b.rx[i] += v
            if written_at == head + star:
                got, b.rx[i] = b.rx[i], ""
                for c in (got[k : k + 8] for k in range(0, 24, 8)):
                    if c != NOID:
                        b.link(b.ports[i][0], c)
            continue
        if not b.rx[i] and not v.strip("0"):  # an idle tick between squares
            continue
        b.rx[i] += v
        if len(b.rx[i]) < 32:
            continue
        got, b.rx[i] = b.rx[i], ""
        if got == ESCAPE:
            b.inv[i] = True
            continue
        if b.inv[i]:
            got, b.inv[i] = invert(got), False
        cells = [got[k : k + 8] for k in range(0, 32, 8)]
        if len(set(cells)) == 4 and NOID not in cells:
            for x, y in zip(cells, cells[1:] + cells[:1]):
                b.link(x, y)
            b.got[i].add(tuple(sorted(b.idx(c) for c in cells)))


# ---------------------------------------------------------------- writing the ports


def choose_squares(b: Book, free: list) -> list:
    """one square key (or None) per port, for the ports in `free`. a square the neighbour lacks goes
    first, and the ports are given different squares where possible; otherwise repeat the one sent
    longest ago."""
    sq = b.squares()
    fresh = {}
    for i in free:
        z = b.idx(b.ports[i][0])
        fresh[i] = [k for k in sorted(sq) if z not in k and k not in b.sent[i] and k not in b.got[i]][:5]
    busy = [i for i in free if fresh[i]]
    best: tuple = ()
    for combo in itertools.product(*(fresh[i] for i in busy)):
        if len(set(combo)) > len(set(best)) or not best:
            best = combo
    out: list = [None] * 4
    for i, k in zip(busy, best):
        out[i] = k
    for i in free:
        if out[i] is None:
            rest = [k for k in sorted(sq) if k not in b.got[i]]
            never = [k for k in rest if k not in b.sent[i]]
            again = [k for k in b.sent[i] if k in rest]
            out[i] = (never or again or [None])[0]
    return out


def frame(ids: list, h: int) -> str:
    """the 32 characters for one square. its first tick must not be all zero (that means idle), so
    start the cycle at an id that allows it; if none does, send the escape and the inverted square."""
    for r in range(4):
        s = "".join(ids[r:] + ids[:r])
        if s[:h].strip("0"):
            return s
    return ESCAPE + invert("".join(ids)) if USE_ESCAPE else "".join(ids)


def tick_reply(b: Book, t: int, h: int) -> str:
    me = b.ids[0]
    head, star = phases(h)
    live = [i for i in range(4) if isinstance(b.ports[i], tuple)]
    note = "continuing the messages in progress"
    if t == 1:
        b.tx = [("f" + str(i) + me).ljust(head * h, "0") for i in range(4)]
        note = "started writing my id and port number on every port"
    elif t == head + 1:
        nbrs = [p[0] if isinstance(p, tuple) else None for p in b.ports]
        for i in live:
            others = [n for j, n in enumerate(nbrs) if n and j != i]
            b.tx[i] = "".join(others + [NOID] * (3 - len(others))).ljust(star * h, "0")
        note = f"{len(live)} live ports; telling each neighbour who my other neighbours are"
    elif t > head + star:
        sq = b.squares()
        free = [i for i in live if not b.tx[i]]
        picks = choose_squares(b, free)
        for i, k in enumerate(picks):
            if k is not None:
                b.tx[i] = frame([b.ids[c] for c in sq[k]], h)
                if k in b.sent[i]:
                    b.sent[i].remove(k)
                b.sent[i].append(k)
        note = (
            f"know {len(b.ids)} cells, {len(b.edges)} links, {len(sq)} squares; "
            f"started a square on {sum(k is not None for k in picks)} ports"
        )
    outs = []
    for i in range(4):
        outs.append(b.tx[i][:h].ljust(h, "0"))
        b.tx[i] = b.tx[i][h:]
    body = "".join(f"<q{i}>{v}</q{i}>\n" for i, v in enumerate(outs))
    return f"<log>{note}</log>\n<protocol>\n{b.dump()}\n</protocol>\n{body}"


# ---------------------------------------------------------------- the map


def embed(b: Book) -> dict:
    """index -> (row, col), self at the origin, for every cell whose place is forced by the known
    links. orientation and mirror image are free, so the first free choice of each is taken; nothing
    else is guessed."""
    adj, cycles = b.adj(), list(b.squares().values())
    pos = {0: (0, 0)}
    add = lambda p, q: (p[0] + q[0], p[1] + q[1])
    sub = lambda p, q: (p[0] - q[0], p[1] - q[1])

    def on_line(a, c):
        """are all placed cells on the lattice line through positions a and c?"""
        d = sub(c, a)
        return all(
            (sub(p, a)[0] * d[1] - sub(p, a)[1] * d[0]) == 0 for p in pos.values()
        )

    def forced() -> bool:
        used = set(pos.values())
        for cyc in cycles:
            placed = [x for x in cyc if x in pos]
            if len(placed) == 3:
                k = next(i for i, x in enumerate(cyc) if x not in pos)
                p = sub(
                    add(pos[cyc[k - 1]], pos[cyc[(k + 1) % 4]]), pos[cyc[(k + 2) % 4]]
                )
                if p not in used:
                    pos[cyc[k]] = p
                    return True
            if len(placed) == 2:
                for k in range(4):
                    a, c, d, e = (
                        cyc[k],
                        cyc[(k + 1) % 4],
                        cyc[(k + 2) % 4],
                        cyc[(k + 3) % 4],
                    )
                    if (
                        a in pos and c in pos
                    ):  # a-c is a placed side; d sits beside c, e beside a
                        u = sub(pos[c], pos[a])
                        sides = [
                            n
                            for n in ((-u[1], u[0]), (u[1], -u[0]))
                            if add(pos[a], n) not in used and add(pos[c], n) not in used
                        ]
                        if len(sides) == 1 or (
                            len(sides) == 2 and on_line(pos[a], pos[c])
                        ):
                            pos[e], pos[d] = (
                                add(pos[a], sides[0]),
                                add(pos[c], sides[0]),
                            )
                            return True
        for x in sorted(pos):
            for y in sorted(adj[x] - set(pos)):
                cands = [add(pos[x], d) for d in DIRS if add(pos[x], d) not in used]
                cands = [
                    p
                    for p in cands
                    if all(
                        abs(p[0] - pos[z][0]) + abs(p[1] - pos[z][1]) == 1
                        for z in adj[y]
                        if z in pos
                    )
                ]
                if len(cands) == 1 or (cands and len(pos) == 1):
                    pos[y] = cands[0]
                    return True
        return False

    def corner_turn() -> bool:
        """a cell with exactly two links has them at right angles. only self's link count is certain."""
        nb = [b.idx(p[0]) for p in b.ports if isinstance(p, tuple)]
        if None in b.ports or len(nb) != 2 or len(pos) != 2:
            return False
        a, y = (nb[0], nb[1]) if nb[0] in pos else (nb[1], nb[0])
        if a not in pos or y in pos:
            return False
        u = sub(pos[a], pos[0])
        pos[y] = (-u[1], u[0])
        return True

    while forced() or corner_turn():
        pass
    r0, c0 = min(p[0] for p in pos.values()), min(p[1] for p in pos.values())
    return {k: (p[0] - r0, p[1] - c0) for k, p in pos.items()}


def quiz_reply(b: Book) -> str:
    pos = embed(b)
    rows = max(2, 1 + max(p[0] for p in pos.values()))
    cols = max(2, 1 + max(p[1] for p in pos.values()))
    at = {p: b.ids[k] for k, p in pos.items()}
    drawing = "\n".join(
        " ".join(f"{at.get((r, c), '?'):<8}" for c in range(cols)).rstrip()
        for r in range(rows)
    )
    seen = 1 + max(p[0] for p in pos.values()), 1 + max(p[1] for p in pos.values())
    size = (
        f"at least {seen[0]}x{seen[1]} from what has reached me"
        if len(pos) > 1
        else "size not known yet"
    )
    live = [p for p in b.ports if isinstance(p, tuple)]
    role = (
        UNKNOWN
        if None in b.ports
        else {2: "corner", 3: "edge", 4: "center"}.get(len(live), f"{len(live)} links")
    )
    out = [
        f"<count>{len(b.ids)}</count>",
        f"<arrangement>a grid, {size}. each cell links to the cells beside it.\n{drawing}</arrangement>",
        f"<position>{role}</position>",
    ]
    for kind, other in (("p", "q"), ("q", "p")):
        for i, p in enumerate(b.ports):
            says = (
                UNKNOWN
                if p is None
                else "nothing"
                if p == "dead"
                else f"{p[0]} {other}{p[1]}"
            )
            out.append(f"<{kind}{i}>{says}</{kind}{i}>")
    return "\n".join(out)


def respond(system: str, prompt: str) -> str:
    """the whole agent. system and prompt are the two strings the harness shows every cell."""
    turn = parse_prompt(system, prompt)
    book = Book.load(turn["me"], turn["protocol"])
    if turn["quiz"]:  # the quiz shows what the neighbours wrote last
        absorb(book, turn["inputs"], turn["t"], turn["h"])
        return quiz_reply(book)
    absorb(book, turn["inputs"], turn["t"] - 1, turn["h"])
    return tick_reply(book, turn["t"], turn["h"])
