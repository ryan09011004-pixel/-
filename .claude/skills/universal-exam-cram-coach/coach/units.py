# -*- coding: utf-8 -*-
"""Teaching units: the tutor teaches problem by problem, not page by page.

Each chapter becomes an ordered list of units. A unit is one course problem plus the
lecture pages it is the first to need, so every lecture idea is taught once, inside the
problem that uses it. Pages that no problem uses are read afterwards as plain slices.
Past-exam problems are kept for the quiz, unless a chapter has no other problems.
"""
import math
import re

from .index import BM25
from .text import pack, tokenize

UNITS_FILE = "units.json"
FORMULAS_FILE = "formulas.json"
PIECE_CHARS = 600      # lecture text is assigned in pieces of about this size (a few paragraphs)
MIN_COVER = 0.15       # overlap a problem needs with a piece to "use" it (idf-weighted overlap coefficient)
NEAR_BEST = 0.5        # among problems with at least this share of the best overlap, the earliest gets the piece


def unit_problems(chapter_n, bank):
    """Problems taught as units: everything except past exams, or the exams when nothing else exists."""
    own = [q for q in bank if q["chapter"] == chapter_n]
    taught = [q for q in own if q["source"].get("kind") != "exam"]
    return taught or own


def _problem_tokens(q):
    return tokenize(" ".join([q["question"] or "", " ".join(q.get("options") or []), q["answer"] or ""]))


_HEADING = re.compile(r"^\s*(?:#{1,6}\s|\d+(?:\.\d+){1,3}\s+\S|第\s*[0-9一二三四五六七八九十]+\s*[章节讲]|"
                      r"(?:section|chapter|lecture|part)\s+\d)", re.I)


def _sections(text):
    """Split a page at headings, so one piece never mixes two topics of a slide or a handout."""
    out, cur = [], []
    for line in (text or "").split("\n"):
        if _HEADING.match(line) and any(l.strip() and not _HEADING.match(l) for l in cur):
            out.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def lecture_pieces(blocks, size=PIECE_CHARS):
    """[(file, page, piece_index, text)] for a chapter's lecture blocks: one heading's text per
    piece, long sections cut into pieces of about `size` characters."""
    out = []
    for rel, page, text in blocks:
        i = 0
        for section in _sections(text):
            for piece in pack(section, size):
                if piece.strip():
                    out.append((rel, page, i, piece))
                    i += 1
    return out


def word_weights(token_sets):
    """idf over the whole course, so boilerplate shared by every file (headers, footers) weighs little."""
    df = {}
    for d in token_sets:
        for tok in d:
            df[tok] = df.get(tok, 0) + 1
    n = float(len(token_sets) or 1)
    return {tok: math.log(1 + n / c) for tok, c in df.items()}


def assign_pieces(problems, pieces, idf=None):
    """Map each lecture piece to the earliest problem that uses it: ({qid: [piece index]}, [unused]).

    Overlap is the idf-weighted overlap coefficient between the piece's words and the
    problem's words (question, options, reference answer): shared weight divided by the
    smaller of the two, so a short problem fully covered by a long piece still matches.
    Among the problems close to the best match, the earliest gets the piece, so each idea
    is taught at the first problem that needs it.
    """
    assign = {q["id"]: [] for q in problems}
    if not problems or not pieces:
        return assign, list(range(len(pieces)))
    psets = [set(_problem_tokens(q)) for q in problems]
    csets = [set(tokenize(p[3])) for p in pieces]
    idf = idf or word_weights(psets + csets)
    weight = lambda s: sum(idf.get(tok, 0.0) for tok in s)
    pw = [weight(s) for s in psets]
    unused = []
    for j, words in enumerate(csets):
        cw = weight(words)
        if not cw:
            unused.append(j)
            continue
        cover = [weight(words & ps) / min(cw, pw[i]) if pw[i] else 0.0 for i, ps in enumerate(psets)]
        best = max(cover)
        if best < MIN_COVER:
            unused.append(j)
            continue
        k = next(i for i, v in enumerate(cover) if v >= max(MIN_COVER, NEAR_BEST * best))
        assign[problems[k]["id"]].append(j)
    return assign, unused


def build_units(chapters, bank, size=PIECE_CHARS):
    """[{chapter, units: [{qid, pieces: [[file, page, i], ...]}], leftover: [[file, page, i], ...]}]"""
    all_pieces = {ch.number: lecture_pieces(ch.blocks, size) for ch in chapters}
    idf = word_weights([set(_problem_tokens(q)) for q in bank] +
                       [set(tokenize(p[3])) for ps in all_pieces.values() for p in ps])
    out = []
    for ch in chapters:
        pieces = all_pieces[ch.number]
        problems = unit_problems(ch.number, bank)
        assign, unused = assign_pieces(problems, pieces, idf)
        ref = lambda j: [pieces[j][0], pieces[j][1], pieces[j][2]]
        out.append({
            "chapter": ch.number,
            "units": [{"qid": q["id"], "pieces": [ref(j) for j in assign[q["id"]]]} for q in problems],
            "leftover": [ref(j) for j in unused],
        })
    return out


# ------------------------------------------------------------------ formula sheet

_FORMULA_LINE = re.compile(r"=|≈|∝|∫|∮|∑|∏|∇|√|\\frac|\\int|\\sum|→")


def formula_lines(sources):
    """Lines of the formula sheet(s) that state a formula: [{file, page, text}]."""
    out = []
    for s in sources:
        if s.kind != "formula" or s.error:
            continue
        for p in s.pages:
            for line in (p.text or "").split("\n"):
                line = line.strip()
                if 3 <= len(line) <= 200 and _FORMULA_LINE.search(line):
                    out.append({"file": s.rel, "page": p.number, "text": line})
    return out


def starting_formulas(q, formulas, k=3):
    """The formula-sheet lines most related to problem `q` (candidates for the first line of the solution)."""
    if not formulas:
        return []
    bm = BM25([tokenize(f["text"]) for f in formulas])
    return [formulas[i] for i, _ in bm.best(_problem_tokens(q), k)]
