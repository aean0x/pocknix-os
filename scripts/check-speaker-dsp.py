#!/usr/bin/env python3
# Build-time gate for the speaker DSP profiles: a board naming a missing profile, a profile the
# renderer rejects or no board uses, or a README key list out of step with the parser must fail
# here; on a device each of those is a DSP that silently never starts.
import glob
import importlib.machinery
import importlib.util
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RENDER = os.path.join(ROOT, "packages/shared/pocknix-bsp-common/pocknix-speaker-dsp-render")
sys.dont_write_bytecode = True  # keep __pycache__ out of the package dir
_loader = importlib.machinery.SourceFileLoader("speaker_dsp_render", RENDER)
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
r = importlib.util.module_from_spec(_spec)
_loader.exec_module(r)

errors = []


def rel(path):
    return os.path.relpath(path, ROOT)


for bsp in sorted(glob.glob(os.path.join(ROOT, "devices/*/packages/pocknix-bsp-*"))):
    pdir = os.path.join(bsp, "root/usr/share/pocknix/speaker-dsp")
    used = set()
    for conf in sorted(glob.glob(os.path.join(bsp, "boards/*.conf"))):
        with open(conf, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*POCKNIX_SPEAKER_PROFILE=([^\s#]*)", line)
                if not m:
                    continue
                used.add(m.group(1))
                if not os.path.isfile(os.path.join(pdir, m.group(1) + ".conf")):
                    errors.append(f"{rel(conf)}: profile {m.group(1)!r} has no {rel(pdir)}/{m.group(1)}.conf")
    for prof in sorted(glob.glob(os.path.join(pdir, "*.conf"))):
        name = os.path.basename(prof)[:-len(".conf")]
        if name not in used:
            errors.append(f"{rel(prof)}: no board in {rel(bsp)}/boards names it")
        try:
            r.render(prof, "check_sink")
        except (OSError, ValueError) as e:
            errors.append(f"{rel(prof)}: {e}")

# The README's KEY=<...> block restates the parser's keys and defaults by hand.
with open(os.path.join(ROOT, "devices/README.md"), encoding="utf-8") as f:
    m = re.search(r"## Speaker DSP profiles.*?```\n(.*?)```", f.read(), re.S)
documented = {}
for line in (m.group(1) if m else "").splitlines():
    k = re.match(r"([A-Z_]+)=<[^>]*>.*?absent(?: or [^=]+)? = (\S+)", line)
    if k:
        documented[k.group(1)] = k.group(2)
if set(documented) != set(r.DEFAULTS):
    errors.append(f"devices/README.md speaker keys {sorted(documented)} != renderer {sorted(r.DEFAULTS)}")
for key, said in documented.items():
    try:
        if key in r.DEFAULTS and float(said) != r.DEFAULTS[key]:
            errors.append(f"devices/README.md: {key} absent = {said}, renderer default {r.DEFAULTS[key]:g}")
    except ValueError:
        pass  # worded defaults ("no high-pass") are not checked

for e in errors:
    print(e)
sys.exit(1 if errors else 0)
