#!/usr/bin/env python3
# Build-time gate for the patch ledgers: a patch file and its PATCHES.md cannot drift. It fails on
# (1) a dir of patches with no PATCHES.md, (2) a patch of ours with no Carried entry, (3) an entry
# with no patch file, (4) a retired number that has a file again, (5) a number used twice in one
# component or across kernel/common and the SoC trees (one series), (6) a kernel/<soc>/sync-keep
# line its ledger's "Edits to synced files" does not name, (7) a ledger the root index lacks or
# whose Base differs from the index. Numbers are the leading digits of a patch's file name; in a
# SoC's synced 30-<soc> dir only 1000+ names are ours, less the ledger's "ROCKNIX 1000+" line.
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NUM = re.compile(r"^(\d{3,4})[-_]")
ENTRY = re.compile(r"^- \*\*([0-9][0-9, -]*)\*\*")
INDEX_ROW = re.compile(r"^\| [^|]+ \| \[([^\]]+/PATCHES\.md)\]\([^)]+\) \| (.+) \|$")


def tracked(root):
    out = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True, check=True)
    return out.stdout.split("\n")


def component(rel):
    parts = rel.split("/")
    return "/".join(parts[:2]) if parts[0] == "kernel" else os.path.dirname(rel)


def numbers(spec):
    """'1030, 1031' and '1032-1037' -> the numbers they name, as zero-padded strings."""
    out = []
    for part in spec.replace(" ", "").split(","):
        lo, _, hi = part.partition("-")
        if hi:
            out += [str(n).zfill(len(lo)) for n in range(int(lo), int(hi) + 1)]
        elif lo:
            out.append(lo)
    return out


def parse(path):
    """A ledger's sections, Carried entries with line numbers, and the first Base line."""
    led = {"sections": {}, "entries": [], "base": None}
    sec = None
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if line.startswith("## "):
                sec = line[3:].strip()
                led["sections"][sec] = ""
                continue
            if sec is None:
                continue
            led["sections"][sec] += line + "\n"
            if sec == "Base" and led["base"] is None and line.strip():
                led["base"] = line.strip()
            m = ENTRY.match(line) if sec == "Carried" else None
            if m:
                led["entries"] += [(x, n) for x in numbers(m.group(1))]
    return led


def scan(root, files):
    hits = []
    led_paths = sorted(f for f in files if f.endswith("/PATCHES.md"))
    ledgers = {os.path.dirname(p): parse(os.path.join(root, p)) for p in led_paths}
    ours = {}       # component -> [(number, rel)]
    synced = {}     # kernel/<soc> -> ROCKNIX numbers in our range
    for comp, led in ledgers.items():
        m = re.search(r"^ROCKNIX 1000\+ \(synced, not ours\): (.*)$", led["sections"].get("Base", ""), re.M)
        if m:
            synced[comp] = set(re.findall(r"\d{4}", m.group(1)))
    for rel in files:
        if not rel.endswith(".patch"):
            continue
        comp, name = component(rel), os.path.basename(rel)
        m = NUM.match(name)
        if not m:
            continue
        soc = comp.split("/")[1] if comp.startswith("kernel/") else None
        if soc and soc != "common":
            if not rel.startswith("%s/patches/30-%s/1" % (comp, soc)) or len(m.group(1)) != 4:
                continue
            if m.group(1) in synced.get(comp, set()):
                ours.setdefault("rocknix:" + comp, []).append((m.group(1), rel))
                continue
        ours.setdefault(comp, []).append((m.group(1), rel))

    for comp, pats in sorted(ours.items()):
        if comp.startswith("rocknix:"):
            continue
        led = ledgers.get(comp)
        if led is None:
            hits.append("%s: has patches but no PATCHES.md" % comp)
            continue
        have = {x for x, _ in led["entries"]}
        retired = set(re.findall(r"\b\d{3,4}\b", led["sections"].get("Retired numbers", "")))
        seen = {}
        for x, rel in pats:
            if x in seen:
                hits.append("%s: number %s used by %s and %s" % (comp, x, seen[x], rel))
            seen[x] = rel
            if x not in have:
                hits.append("%s: no Carried entry in %s/PATCHES.md" % (rel, comp))
            if x in retired:
                hits.append("%s: %s is a retired number in %s/PATCHES.md" % (rel, x, comp))
    for comp, led in sorted(ledgers.items()):
        files_here = {x for x, _ in ours.get(comp, [])}
        dup = set()
        for x, n in led["entries"]:
            if x not in files_here:
                hits.append("%s/PATCHES.md:%d: entry %s names no patch file of ours" % (comp, n, x))
            if x in dup:
                hits.append("%s/PATCHES.md:%d: entry %s is listed twice" % (comp, n, x))
            dup.add(x)
        for x in sorted(synced.get(comp, set()) - {x for x, _ in ours.get("rocknix:" + comp, [])}):
            hits.append("%s/PATCHES.md: ROCKNIX 1000+ lists %s, which has no file" % (comp, x))

    # One kernel series: a number names one patch across kernel/common and every SoC tree.
    owner = {}
    for comp, pats in sorted(ours.items()):
        tree = comp.replace("rocknix:", "")
        if not tree.startswith("kernel/"):
            continue
        for x, rel in pats:
            if x in owner and owner[x][0] != tree:
                hits.append("%s: kernel number %s is also %s" % (rel, x, owner[x][1]))
            owner.setdefault(x, (tree, rel))

    for comp, led in sorted(ledgers.items()):
        keep = os.path.join(root, comp, "sync-keep")
        if not comp.startswith("kernel/") or not os.path.isfile(keep):
            continue
        edits = led["sections"].get("Edits to synced files", "")
        with open(keep, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("-"):
                    p = line[1:].split("/")
                    want = "%s/%s" % (p[-2], NUM.match(p[-1]).group(1) if NUM.match(p[-1]) else p[-1])
                else:
                    want = "`%s/%s`" % (comp, line.lstrip("+"))
                if want not in edits:
                    hits.append("%s/PATCHES.md: Edits to synced files does not name %s (sync-keep: %s)"
                                % (comp, want.strip("`"), line))

    index = {}
    with open(os.path.join(root, "PATCHES.md"), encoding="utf-8") as f:
        for line in f:
            m = INDEX_ROW.match(line.rstrip("\n"))
            if m:
                index[os.path.dirname(m.group(1))] = m.group(2).strip()
    for comp, led in sorted(ledgers.items()):
        if comp not in index:
            hits.append("PATCHES.md: index has no row for %s/PATCHES.md" % comp)
        elif index[comp] != led["base"]:
            hits.append("PATCHES.md: %s base '%s' differs from its ledger's '%s'" % (comp, index[comp], led["base"]))
    return hits


def selftest():
    """Plant each kind of drift in a scratch copy: each must be caught, nothing else."""
    files = tracked(ROOT)
    tmp = tempfile.mkdtemp(prefix="check-patches-")
    try:
        for rel in files:
            if rel == "PATCHES.md" or rel.endswith("/PATCHES.md") or rel.endswith("/sync-keep"):
                os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
                shutil.copy2(os.path.join(ROOT, rel), os.path.join(tmp, rel))
        baseline = set(scan(tmp, files))  # drift the real tree has is the main run's to report
        socs = sorted(f for f in files if re.match(r"kernel/[^/]+/PATCHES\.md$", f) and "/common/" not in f)
        clash = next(e[-1][0] for e in (parse(os.path.join(ROOT, f))["entries"] for f in socs) if e)
        retired = re.findall(r"\d{4}", parse(os.path.join(ROOT, "packages/soc/gamescope/PATCHES.md"))["sections"]["Retired numbers"])[0]
        planted = ["packages/soc/gamescope/0099-planted-no-entry.patch",
                   "packages/soc/gamescope/%s-planted-retired.patch" % retired,
                   "packages/shared/selftest-pkg/0001-planted-no-ledger.patch",
                   "kernel/common/patches/%s-planted-clash.patch" % clash]
        with open(os.path.join(tmp, "packages/soc/gamescope/PATCHES.md"), "a", encoding="utf-8") as f:
            f.write("\n## Carried\n\n- **0098** planted entry with no file.\n- **%s** planted retired.\n" % retired)
        with open(os.path.join(tmp, "kernel/common/PATCHES.md"), "a", encoding="utf-8") as f:
            f.write("\n## Carried\n\n- **%s** planted clash.\n" % clash)
        hits = scan(tmp, sorted(set(files + planted)))
        for h in hits:
            print("  planted -> %s" % h)
        want = ["0099-planted-no-entry.patch: no Carried entry",
                "-planted-retired.patch: %s is a retired number" % retired,
                "packages/shared/selftest-pkg: has patches but no PATCHES.md",
                "entry 0098 names no patch file",
                "kernel number %s is also" % clash]
        missed = [w for w in want if not any(w in h for h in hits)]
        stray = [h for h in hits if h not in baseline and not any(w in h for w in want)]
        if missed or stray:
            print("selftest FAILED: missed %s; stray %s" % (missed, stray))
            return 1
        print("selftest: each planted drift caught, nothing else flagged")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if "--selftest" in argv:
        return selftest()
    hits = scan(ROOT, tracked(ROOT))
    for h in hits:
        print(h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
