#!/usr/bin/env python3
"""
seat_players.py -- fill the other seats at the table so one person can walk APF.

WHY THIS EXISTS. APF needs at least two players: constraint 2 says no single
casefile may solve the case alone, and at one player the only casefile IS the
whole assignment. So the round screen cannot be walked solo -- and the phone
client cannot help yet, because server/static/mobile.html is built for the
pre-APF gather loop and calls /share-phase rather than /apf/share. A phone
would join, never meet the round-2 checkpoint, and the host screen would
correctly refuse to open round 3. The walk would stall two rounds in.

WHAT THIS IS NOT. It is not a bot player and it is not an AI opponent. It joins
seats and pays each share checkpoint with the bare minimum the server asks for,
which is the most withholding-heavy legal play. It never accuses, never opens a
round and never closes the case -- those are the host's, and the host is you.

So what you are walking is the real server, the real rhythm and the real board,
with the social half stubbed out. That is exactly the half a checker cannot
test anyway.

Run it while the host is sitting in the LOBBY, before they press "Begin the
investigation" -- open_session snapshots who is in the room, so anyone who
arrives after the assignment is not in it.

    python3 scripts/seat_players.py ABCD1234            # 3 extra seats
    python3 scripts/seat_players.py ABCD1234 --seats 1  # just one

Zero API cost, no API key. Ctrl-C to stop.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("CYM_SERVER", "http://localhost:8000")
NAMES = ["Bardsley", "Chen", "Okonjo", "Vance", "Ferreira"]


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except ValueError:
            return e.code, {"detail": raw.decode("utf-8", "replace")[:200]}
    except urllib.error.URLError as e:
        return 0, {"detail": f"cannot reach {BASE}: {e.reason}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("room", help="the room code shown on the host screen")
    ap.add_argument("--seats", type=int, default=3,
                    help="how many extra players to seat (default 3, so a table of 4)")
    ap.add_argument("--poll", type=float, default=2.0, help="seconds between checks")
    args = ap.parse_args()

    room = args.room.strip().upper()
    if not 1 <= args.seats <= len(NAMES):
        print(f"--seats must be between 1 and {len(NAMES)}")
        return 2

    seated = []
    for name in NAMES[:args.seats]:
        status, body = call("POST", f"/games/{room}/join", {"player_name": name})
        if status != 200:
            print(f"could not seat {name}: {status} {body.get('detail', body)}")
            return 1
        seated.append({"name": name, "id": body["player_id"]})
        print(f"  seated {name}")

    print(f"\n{len(seated)} seat(s) filled in room {room}.")
    print("Now press \"Begin the investigation\" on the host screen.\n")
    print("Each of these will share the MINIMUM the server asks of them, which is the")
    print("most withholding-heavy legal play -- so the board fills slowly and there is")
    print("something left for full disclosure to reveal.\n")

    announced = False
    last_round = -1
    while True:
        status, state = call("GET", f"/games/{room}/apf/state?player_id={seated[0]['id']}")
        if status == 409:
            time.sleep(args.poll)          # not assigned yet -- host is still in the lobby
            continue
        if status != 200:
            print(f"lost the table: {status} {state.get('detail', state)}")
            return 1

        if not announced:
            print(f"The investigation runs {state['rounds']} rounds. "
                  f"Share ladder: {state['share_ladder']}\n")
            announced = True

        rnd = state["round"]
        if rnd != last_round:
            print(f"--- round {rnd} of {state['rounds']} ---")
            last_round = rnd

        for seat in seated:
            s, mine = call("GET", f"/games/{room}/apf/state?player_id={seat['id']}")
            if s != 200:
                continue
            owed = mine["share_outstanding"]
            if owed <= 0:
                continue
            # Share findings not already on the table. Sharing from the front of
            # the list without this check pays nothing: sharing is idempotent.
            fresh = [f["id"] for f in mine["casefile"] if not f["shared"]][:owed]
            if not fresh:
                continue
            s2, res = call("POST", f"/games/{room}/apf/share",
                           {"player_id": seat["id"], "finding_ids": fresh})
            if s2 == 200:
                titles = [f["title"] for f in mine["casefile"] if f["id"] in fresh]
                print(f"  {seat['name']} puts {len(fresh)} on the table: "
                      + "; ".join(t[:40] for t in titles))
            else:
                print(f"  {seat['name']} could not share: {res.get('detail', res)}")

        if state.get("disclosed"):
            print("\nThe case is closed and everything is on the table. "
                  "Nothing left for these seats to do.")
            return 0
        time.sleep(args.poll)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nstopped.")
        sys.exit(0)
