"""Fetch Creality Print K2 profiles from the public CrealityPrint repo and resolve 'inherits'."""
import json, sys, urllib.parse, urllib.request, pathlib
BASE = "https://raw.githubusercontent.com/CrealityOfficial/CrealityPrint/master/resources/profiles/"
out = pathlib.Path(sys.argv[1]); raw = out / "raw"; raw.mkdir(parents=True, exist_ok=True)
index = json.load(open(out / "Creality.json"))
paths = {e["name"]: e["sub_path"] for k in ("machine_list","machine_model_list","process_list","filament_list") for e in index.get(k, [])}

def get(name):
    sub = paths[name]; f = raw / sub.replace("/", "__")
    if not f.exists():
        url = BASE + "Creality/" + urllib.parse.quote(sub)
        f.write_bytes(urllib.request.urlopen(url, timeout=30).read())
    return json.load(open(f))

def resolve(name, chain=None):
    chain = chain or []
    d = get(name); chain.append(name)
    parent = d.get("inherits")
    base = resolve(parent, chain)[0] if parent else {}
    base.update({k: v for k, v in d.items() if k != "inherits"})
    return base, chain

for name in sys.argv[2:]:
    d, chain = resolve(name)
    (out / (name.replace(" ", "_").replace("@", "at_") + ".resolved.json")).write_text(json.dumps(d, indent=1))
    print(f"{name}: {len(d)} keys, chain = {' <- '.join(chain)}")
