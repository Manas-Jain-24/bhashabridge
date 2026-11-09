"""Import official Dakshina lexicons and aligned FLORES text without downloading 2 GB.

Only selected tar members are read. No archive paths are extracted to disk.
"""
import argparse
import hashlib
import json
import re
import tarfile
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/expanded"
OUT = ROOT / "data/processed/expanded"
LANGUAGES = {"bn": "bengali", "hi": "hindi", "mr": "marathi"}
FLORES = {"bengali": "ben_Beng", "hindi": "hin_Deva", "marathi": "mar_Deva", "english": "eng_Latn"}
DAKSHINA = "https://storage.googleapis.com/gresearch/dakshina/dakshina_dataset_v1.0.tar"
FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"


def norm(value):
    return " ".join("".join(c if unicodedata.category(c)[0] in "LMN" else " " for c in unicodedata.normalize("NFC", value).lower()).split())


def records(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temp.replace(path)


def get_range(url, start, size):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start+size-1}", "User-Agent": "BhashaBridge-dataset-import/1"})
            with urllib.request.urlopen(req, timeout=45) as response:
                content_range = response.headers.get("Content-Range", "")
                if response.status != 206 or not content_range.startswith(f"bytes {start}-"):
                    raise RuntimeError("Server did not honor a bounded range request")
                data = response.read(size + 1)
                if len(data) != size: raise RuntimeError("Truncated/oversized range response")
                return data
        except Exception:
            if attempt == 2: raise
            time.sleep(1)


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    wanted = {f"dakshina_dataset_v1.0/{iso}/lexicons/{iso}.translit.sampled.{split}.tsv": RAW / f"{iso}.{split}.tsv"
              for iso in LANGUAGES for split in ("train", "dev", "test")}
    missing = {name: path for name, path in wanted.items() if not path.exists()}
    offset = 0
    index_path = RAW / "dakshina_index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for name in list(missing):
        if name in index:
            info = index[name]
            missing.pop(name).write_bytes(get_range(DAKSHINA, info["offset"], info["size"]))
            print("Downloaded", name, flush=True)
    while missing:
        block = get_range(DAKSHINA, offset, 512)
        if not block.strip(b"\0"): raise RuntimeError("Archive ended before all lexicons were found")
        member = tarfile.TarInfo.frombuf(block, "utf-8", "surrogateescape")
        data_offset = offset + 512
        index[member.name] = {"offset": data_offset, "size": member.size}
        index_path.write_text(json.dumps(index, indent=2))
        if member.name in missing:
            if not member.isfile() or member.size > 10_000_000: raise RuntimeError("Unexpected lexicon member")
            missing.pop(member.name).write_bytes(get_range(DAKSHINA, data_offset, member.size))
            print("Downloaded", member.name, member.size, flush=True)
        offset = data_offset + ((member.size + 511) // 512) * 512
        if offset > 2_100_000_000: raise RuntimeError("Invalid tar offset")
    archive = RAW / "flores200.tar.gz"
    if not archive.exists():
        archive.write_bytes(get_range(FLORES_URL, 0, 25585843))
        print("Downloaded FLORES archive", flush=True)
    # Read only registered languages and splits; never use extractall.
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            for split in ("dev", "devtest"):
                for language, code in FLORES.items():
                    if member.name.endswith(f"/{split}/{code}.{split}"):
                        if member.size > 2_000_000: raise RuntimeError("Oversized FLORES member")
                        (RAW / f"{language}.{split}.txt").write_bytes(tar.extractfile(member).read())


def lexicon(iso, split):
    groups = defaultdict(Counter)
    for line in (RAW / f"{iso}.{split}.tsv").read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) != 3: continue
        native, roman, count = fields
        native, roman = unicodedata.normalize("NFC", native.strip()), norm(roman)
        if not native or not re.fullmatch(r"[a-z]+", roman) or len(roman) > 35: continue
        if not all(unicodedata.category(c)[0] in "LM" for c in native): continue
        groups[native][roman] += int(count)
    return [{"language": LANGUAGES[iso], "native": native, "roman": options.most_common(1)[0][0],
             "aliases": sorted(options), "attestations": sum(options.values()), "source": "Google Dakshina v1.0",
             "license": "CC-BY-SA-4.0", "source_split": split}
            for native, options in sorted(groups.items())]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    train, validation, test = [], [], []
    for iso in LANGUAGES:
        train.extend(lexicon(iso, "train")); validation.extend(lexicon(iso, "dev")); test.extend(lexicon(iso, "test"))
    # Include the project's earlier training corpus, but exclude every held-out
    # native word and Roman source before composing the new training dataset.
    legacy = ROOT / "data/processed/transliteration"
    old_eval = records(legacy / "validation.jsonl") + records(legacy / "test.jsonl")
    def language(row): return LANGUAGES.get(row.get("language"), row.get("language"))
    forbidden_native = {(row["language"], norm(row["native"])) for row in validation + test}
    forbidden_roman = {(row["language"], norm(alias)) for row in validation + test for alias in row["aliases"]}
    for row in old_eval:
        forbidden_native.add((language(row), norm(row.get("native", row.get("devanagari", "")))))
        forbidden_roman.add((language(row), norm(row["roman"])))
    train = [r for r in train if (r["language"], norm(r["native"])) not in forbidden_native and not any((r["language"], norm(a)) in forbidden_roman for a in r["aliases"])]
    write_rows(OUT / "lexicon.jsonl", train)
    combined = []
    for row in records(legacy / "train.jsonl"):
        native = row.get("native", row.get("devanagari", "")); lang = language(row)
        if (lang, norm(native)) in forbidden_native or (lang, norm(row["roman"])) in forbidden_roman: continue
        combined.append({"language": lang, "native": native, "roman": norm(row["roman"]), "source": row.get("source", "legacy_project_corpus")})
    combined.extend({**row, "roman": alias} for row in train for alias in row["aliases"])
    unique = {(r["language"], norm(r["native"]), norm(r["roman"])): r for r in combined}
    write_rows(OUT / "transliteration/train.jsonl", unique.values())
    write_rows(OUT / "transliteration/validation.jsonl", validation)
    write_rows(OUT / "transliteration/test.jsonl", test)

    parallel = {}
    for split in ("dev", "devtest"):
        columns = {lang: (RAW / f"{lang}.{split}.txt").read_text(encoding="utf-8").splitlines() for lang in FLORES}
        if len({len(col) for col in columns.values()}) != 1: raise ValueError("FLORES alignment length mismatch")
        parallel[split] = [{"id": f"flores200-{split}-{i+1}", "sentences": {lang: text[i].strip() for lang, text in columns.items()},
                            "source": "FLORES-200", "license": "CC-BY-SA-4.0", "source_split": split}
                           for i in range(len(next(iter(columns.values()))))]
    forbidden = {(lang, norm(text)) for row in parallel["devtest"] for lang, text in row["sentences"].items()}
    for row in records(ROOT / "data/processed/translation/test.jsonl"):
        forbidden.update((lang, norm(row[lang])) for lang in ("hindi", "marathi"))
    teaching = [row for row in parallel["dev"] if not any((lang, norm(text)) in forbidden for lang, text in row["sentences"].items())]
    write_rows(OUT / "translation/teaching.jsonl", teaching)
    directed = [{"id": row["id"] + f"-{source}-{target}", "source_language": source, "target_language": target,
                 "source_text": row["sentences"][source], "target_text": row["sentences"][target],
                 "source": "FLORES-200 dev", "license": "CC-BY-SA-4.0"}
                for row in teaching for source in LANGUAGES.values() for target in LANGUAGES.values() if source != target]
    write_rows(OUT / "translation/train.jsonl", directed)
    write_rows(OUT / "translation/test.jsonl", parallel["devtest"])
    # Teaching sentences are corpus references, never imported as reviewed app memory.
    counts = {"lexicon_words": dict(Counter(row["language"] for row in train)),
              "transliteration_train_pairs": len(unique), "transliteration_train_by_language": dict(Counter(r["language"] for r in unique.values())), "transliteration_validation_words": len(validation),
              "transliteration_test_words": len(test), "translation_teaching_multiway_rows": len(teaching),
              "translation_test_multiway_rows": len(parallel["devtest"]), "translation_train_directional_pairs": len(directed)}
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob("*.jsonl"))}
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "counts": counts, "sha256": hashes,
                "raw_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.glob("*")) if p.is_file() and p.suffix != ".json"},
                "sources": [{"name":"Google Dakshina v1.0", "url":DAKSHINA, "documentation":"https://github.com/google-research-datasets/dakshina", "license":"CC-BY-SA-4.0"},
                            {"name":"FLORES-200", "url":FLORES_URL,"documentation":"https://github.com/facebookresearch/flores/tree/main/flores200", "license":"CC-BY-SA-4.0"}],
                "notes": ["Teaching uses FLORES dev; benchmark uses devtest. Never evaluate on teaching examples.", "Lexicon entries are spelling/romanization pairs, not dictionary definitions.", "New corpora were downloaded, filtered and prepared; model weights have not been retrained.", "Legacy benchmark files and reviewed sentence memory are unchanged."]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(counts, indent=2), flush=True)
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline: download()
    build()
