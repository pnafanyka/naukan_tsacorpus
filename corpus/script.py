import json
import re
import sys
from pathlib import Path


def split_parts_with_delims(parts: str):
    """
    Split a parts string like "dokum'ent-vlä-m" or "r'ejs=ät"
    into (segments, delimiters), where:
      segments = ["dokum'ent", "vlä", "m"]
      delimiters = ["-", "-"]
    For "r'ejs=ät":
      segments = ["r'ejs", "ät"]
      delimiters = ["="]
    """
    pieces = re.split(r'(-|=)', parts)
    if not pieces:
        return [], []

    segments = [pieces[0]]
    delimiters = []
    for i in range(1, len(pieces), 2):
        if i + 1 >= len(pieces):
            break
        sep = pieces[i]
        seg = pieces[i + 1]
        segments.append(seg)
        delimiters.append(sep)
    return segments, delimiters


def tags_from_gloss(gloss: str, n_affixes: int):
    """
    Take gloss like "кончаться-NPST.3SG" or
    "спускаться-БЕСКОНЕЧНО-CVB.DELIM-3SG.S" and
    return a list of morphological tags to align with affixes.
    """
    if not gloss:
        return [""] * n_affixes

    pieces = gloss.split("-")
    morph_tags = pieces[1:] if len(pieces) > 1 else []

    if len(morph_tags) >= n_affixes:
        morph_tags = morph_tags[-n_affixes:]
    else:
        morph_tags = [""] * (n_affixes - len(morph_tags)) + morph_tags

    return [t.strip() for t in morph_tags]


def build_gloss_index(parts: str, gloss: str) -> str:
    """
    Build a gloss_index-style string.

    If there is no segmentation in `parts`, returns:  STEM{parts}-
    Otherwise:
      STEM{stem}-TAG{seg1}-TAG{seg2}-...
    with '='-segments marked as =TAG{seg}-.
    """
    parts = parts.strip()
    if not parts:
        return ""

    if "-" not in parts and "=" not in parts:
        return f"STEM{{{parts}}}-"

    segments, delimiters = split_parts_with_delims(parts)
    if not segments:
        return ""

    stem = segments[0]
    affixes = segments[1:]
    n_affixes = len(affixes)
    tags = tags_from_gloss(gloss, n_affixes)

    out = f"STEM{{{stem}}}-"

    for i, seg in enumerate(affixes):
        delim = delimiters[i] if i < len(delimiters) else "-"
        tag = tags[i] if i < len(tags) else ""

        if not tag:
            tag = "MORPH"

        prefix = "=" if delim == "=" else ""
        out += f"{prefix}{tag}{{{seg}}}-"

    return out


def enrich_ana(ana: dict):
    """
    Add all missing fields inside one 'ana' dict:
      - gloss_index
      - lex
      - trans_ru
      - gloss_ru
      - gloss_index_ru
      - gr.pos
    """
    parts = ana.get("parts", "") or ""
    gloss = ana.get("gloss", "") or ""

    # gloss_index (Latin-style)
    if "gloss_index" not in ana or not ana.get("gloss_index"):
        ana["gloss_index"] = build_gloss_index(parts, gloss)

    # lex: first segment of parts (before - or =)
    if "lex" not in ana or not ana.get("lex"):
        if parts:
            lex_candidate = re.split(r"[-=]", parts)[0]
        else:
            lex_candidate = ""
        ana["lex"] = lex_candidate

    # trans_ru: lexical Russian translation (before first '-')
    if "trans_ru" not in ana or not ana.get("trans_ru"):
        if gloss:
            trans = gloss.split("-")[0]
        else:
            trans = ""
        ana["trans_ru"] = trans

    # gloss_ru: keep Russian gloss as-is
    if "gloss_ru" not in ana or not ana.get("gloss_ru"):
        ana["gloss_ru"] = gloss

    # gloss_index_ru: placeholder – same pattern, based on Russian gloss
    if "gloss_index_ru" not in ana or not ana.get("gloss_index_ru"):
        ana["gloss_index_ru"] = build_gloss_index(parts, ana["gloss_ru"])

    # gr.pos: cannot be reliably inferred, so leave empty if absent
    if "gr.pos" not in ana:
        ana["gr.pos"] = ""


def add_word_indices(sent: dict):
    """
    Add off_start, off_end, next_word, sentence_index, sentence_index_neg
    to each word in a sentence.
    """
    text = sent.get("text", "") or ""
    words = sent.get("words", [])
    n = len(words)
    if n == 0:
        return

    # char-based search: move cursor through the text
    cursor = 0
    for word in words:
        wf = word.get("wf", "")
        if not wf:
            continue

        # try to find from current cursor
        idx = text.find(wf, cursor)
        if idx == -1:
            # fallback: search from beginning (may be imperfect but better than nothing)
            idx = text.find(wf)
        if idx == -1:
            # can't find: skip offsets
            continue

        off_start = idx
        off_end = idx + len(wf)
        cursor = off_end

        if "off_start" not in word:
            word["off_start"] = off_start
        if "off_end" not in word:
            word["off_end"] = off_end

    # sentence_index, sentence_index_neg, next_word
    for i, word in enumerate(words):
        # indices from both sides
        word.setdefault("sentence_index", i)
        word.setdefault("sentence_index_neg", n - 1 - i)
        # next_word: index of following word (can be == len(words) for last one)
        word.setdefault("next_word", i + 1)


def add_missing_fields(in_path: Path, out_path: Path):
    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for sent in data.get("sentences", []):
        # word-level indices
        add_word_indices(sent)

        # ana-level fields
        for word in sent.get("words", []):
            for ana in word.get("ana", []):
                enrich_ana(ana)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    base_dir = Path("corpus/naukan")
    for file in base_dir.iterdir():
        in_path = Path(file)
        out_path = Path(file)
        add_missing_fields(in_path, out_path)


if __name__ == "__main__":
    main()
