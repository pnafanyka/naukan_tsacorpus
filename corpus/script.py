#!/usr/bin/env python3
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
    # Split and keep delimiters
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
    Take gloss like "кончаться-NPST.3SG" or "спускаться-БЕСКОНЕЧНО-CVB.DELIM-3PL.O"
    and return a list of morphological tags to align with affixes.

    Strategy:
      - split on '-' → first piece = lexical meaning; rest = morph tags
      - if there are more tags than affixes → take the *last* n_affixes
      - if fewer → left-pad with "" to keep lengths equal
    """
    if not gloss:
        return [""] * n_affixes

    pieces = gloss.split("-")
    # everything after the first dash is morph tags
    morph_tags = pieces[1:] if len(pieces) > 1 else []

    if len(morph_tags) >= n_affixes:
        morph_tags = morph_tags[-n_affixes:]
    else:
        morph_tags = [""] * (n_affixes - len(morph_tags)) + morph_tags

    return [t.strip() for t in morph_tags]


def build_gloss_index(parts: str, gloss: str) -> str:
    """
    Build a gloss_index string in the spirit of your second file.
    """
    parts = parts.strip()
    if not parts:
        return ""

    # No segmentation: just give STEM{parts}-
    if "-" not in parts and "=" not in parts:
        return f"STEM{{{parts}}}-"

    segments, delimiters = split_parts_with_delims(parts)
    if not segments:
        return ""

    stem = segments[0]
    affixes = segments[1:]
    n_affixes = len(affixes)

    tags = tags_from_gloss(gloss, n_affixes)

    # Start with the stem
    out = f"STEM{{{stem}}}-"

    # Then each affix with its tag
    for i, seg in enumerate(affixes):
        delim = delimiters[i] if i < len(delimiters) else "-"
        tag = tags[i] if i < len(tags) else ""

        # If we don't have a clear tag, just leave it empty but keep structure
        if not tag:
            tag = "MORPH"

        prefix = "=" if delim == "=" else ""
        out += f"{prefix}{tag}{{{seg}}}-"

    return out


def add_gloss_index_to_file(in_path: Path, out_path: Path):
    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for sent in data.get("sentences", []):
        for word in sent.get("words", []):
            for ana in word.get("ana", []):
                parts = ana.get("parts", "")
                gloss = ana.get("gloss", "")

                # Don't overwrite if gloss_index already exists
                if "gloss_index" not in ana:
                    ana["gloss_index"] = build_gloss_index(parts, gloss)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    in_path = Path("corpus/naukan/DEA_raven and fox_240623.json")
    out_path = Path("corpus/DEA_raven and fox_240623_corrected.json")
    add_gloss_index_to_file(in_path, out_path)


if __name__ == "__main__":
    main()
