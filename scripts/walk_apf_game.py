#!/usr/bin/env python3
"""
walk_apf_game.py -- play a whole APF game over real HTTP, end to end.

WHY THIS EXISTS AND THE UNIT TESTS DO NOT COVER IT. scripts/test_apf.py proves
the rhythm's rules in-process. This proves the ROUTES: that a room can be
created, dealt, played through four rounds and closed by full disclosure, and
that accusing the last face standing reaches the result screen. Session 42 found
one defect this way that no in-process test could have -- winning fired a live
Claude call, so a 401 took the whole win down with a 500.

ZERO API COST, AND NO API KEY NEEDED. Nothing here generates; it plays the
mystery already on disk. Run the server first:

    cd server && uvicorn main:app --port 8000
    python3 scripts/walk_apf_game.py

Exit: 0 = pass, 1 = failure.
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("CYM_SERVER", "http://localhost:8000")

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

fails = []
def ok(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f" -- {detail}"))
    if not cond:
        fails.append(name)

st, g = call("POST", "/games/create", {
    "mystery_slug": "the_neriin_in_the_pilchard_barrel",
    "host_name": "Ana", "difficulty": "MEDIUM"})
ok("room created with the accepted mystery", st == 200, f"{st} {g}")
gid, host = g["game_id"], g["player_id"]

ids = {"Ana": host}
for name in ("Ben", "Cora", "Dev"):
    st, j = call("POST", f"/games/{gid}/join", {"player_name": name})
    ids[name] = j["player_id"]

# One player cannot open a deal -- said plainly, not as an opaque deal failure.
st2, solo = call("POST", "/games/create", {
    "mystery_slug": "the_neriin_in_the_pilchard_barrel",
    "host_name": "Solo", "difficulty": "MEDIUM"})
st3, err = call("POST", f"/games/{solo['game_id']}/apf/open", {"player_id": solo["player_id"]})
ok("a one-player deal is refused, with the reason", st3 == 400 and "at least 2" in str(err), f"{st3} {err}")

st, opened = call("POST", f"/games/{gid}/apf/open", {"player_id": host})
ok("the deal opens", st == 200, f"{st} {opened}")
ok("and the game announces its length up front", opened.get("rounds") == 4, str(opened))
ok("and the whole share ladder with it", opened.get("share_ladder") == [1, 1, 2, 2], str(opened.get("share_ladder")))
ok("the chosen dealing has no monopoly on proof", opened["deal"]["monopoly"] == 0, str(opened["deal"]))

st, again = call("POST", f"/games/{gid}/apf/open", {"player_id": host})
ok("dealing twice is refused", st == 409, str(st))
st, denied = call("POST", f"/games/{gid}/apf/open", {"player_id": ids["Ben"]})
ok("a non-host cannot deal", st == 403, str(st))

for r in range(1, 5):
    st, rd = call("POST", f"/games/{gid}/apf/round/next", {"player_id": host})
    ok(f"round {r} deals", st == 200 and rd["round"] == r, f"{st} {rd}")

    st, s = call("GET", f"/games/{gid}/apf/state?player_id={host}")
    ok(f"round {r}: the hand holds {r}", len(s["hand"]) == r, str(len(s["hand"])))
    if r == 1:
        ok("round 1 asks for nothing", s["share_required"] == 0, str(s["share_required"]))
        ok("and no checkpoint is open", not s["checkpoint_open"])
        continue

    ok(f"round {r}: the requirement is sent, not derived", s["share_required"] >= 1)
    if r == 3:
        st, rd = call("POST", f"/games/{gid}/apf/round/next", {"player_id": host})
        ok("a round cannot outrun an open checkpoint", st == 409 and "checkpoint" in str(rd), f"{st} {rd}")

    for name, pid in ids.items():
        st, ps = call("GET", f"/games/{gid}/apf/state?player_id={pid}")
        need = ps["share_outstanding"]
        fresh = [f["id"] for f in ps["hand"] if not f["shared"]][:need]
        st, sh = call("POST", f"/games/{gid}/apf/share",
                      {"player_id": pid, "finding_ids": fresh})
        ok(f"round {r}: {name} shares {need}", st == 200 and sh["outstanding"] == 0, f"{st} {sh}")

    if r == 4:
        break

st, s = call("GET", f"/games/{gid}/apf/state?player_id={host}")
ok("by the last round the board has faces greyed out",
   any(row["cleared"] for row in s["board"]), str(s["board"]))
ok("each with a name against it",
   all(row["cleared_by"][0]["player_name"] in ids for row in s["board"] if row["cleared"]))
ok("and somebody is still standing", any(not row["cleared"] for row in s["board"]))
held_back = sum(1 for f in s["hand"] if not f["shared"])
ok("the host is still sitting on a stash", held_back == 2, str(held_back))

# Nothing leaks.
blob = json.dumps(s)
ok("the payload names no culprit", "culprit" not in blob)
ok("the hand stops at the current round", len(s["hand"]) == 4)

st, bad = call("POST", f"/games/{gid}/apf/share",
               {"player_id": host, "finding_ids": ["E:NOPE"]})
ok("sharing a finding nobody dealt you is refused", st == 400, f"{st} {bad}")

st, d = call("POST", f"/games/{gid}/apf/disclose", {"player_id": host})
ok("full disclosure closes the case", st == 200 and d["disclosed"], f"{st}")
ok("and names everyone who sat on something",
   all(p["withheld"] == 2 for p in d["by_player"]), str(d["by_player"]))
ok("the withheld list is what the reveal screen is for", len(d["withheld"]) == 8, str(len(d["withheld"])))
standing = [row["name"] for row in d["board"] if not row["cleared"]]
ok("and the board resolves to exactly one name", len(standing) == 1, str(standing))

st, acc = call("POST", f"/games/{gid}/accuse",
               {"player_id": host, "culprit_name": standing[0]})
ok("accusing the last face standing wins", st == 200 and acc["correct"], f"{st} {acc}")

st, closed = call("POST", f"/games/{gid}/apf/share",
                  {"player_id": host, "finding_ids": []})
ok("the closed case refuses further shares", st == 400, str(st))

print()
if fails:
    print(f"FAILED ({len(fails)}): " + ", ".join(fails))
    sys.exit(1)
print("A whole four-round APF game plays over HTTP, and it ends on the right name.")
