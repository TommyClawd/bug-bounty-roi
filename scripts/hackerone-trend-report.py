#!/usr/bin/env python3
"""
Weekly HackerOne ROI Trend Report
Compares current scrape against previous snapshot.
Identifies: new programs, rising/falling ROI, newly competitive programs.
"""
import json
import os
import sys
from datetime import datetime

SNAPSHOT_DIR = os.path.expanduser("~/.openclaw/workspace/research/hackerone-snapshots")
CURRENT = os.path.expanduser("~/.openclaw/workspace/research/hackerone-full-dataset.json")

def load_snapshot(path):
    with open(path) as f:
        d = json.load(f)
    return {p["handle"]: p for p in d.get("programs", d if isinstance(d, list) else [])}

def main():
    # Get sorted snapshots
    snapshots = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    
    if len(snapshots) < 2:
        print("Need at least 2 snapshots to compare. Run the scraper again next week.")
        return
    
    prev_path = os.path.join(SNAPSHOT_DIR, snapshots[-2])
    curr_path = os.path.join(SNAPSHOT_DIR, snapshots[-1])
    
    prev = load_snapshot(prev_path)
    curr = load_snapshot(curr_path)
    
    print(f"Comparing {snapshots[-2]} → {snapshots[-1]}")
    print(f"Previous: {len(prev)} programs | Current: {len(curr)} programs\n")
    
    # New programs
    new_programs = [h for h in curr if h not in prev and curr[h].get("roi_score", 0) > 0]
    if new_programs:
        print("🆕 NEW BOUNTY PROGRAMS:")
        for h in sorted(new_programs, key=lambda x: curr[x].get("roi_score", 0), reverse=True)[:10]:
            p = curr[h]
            print(f"  {p['name'][:30]:30s} avg=${p.get('average_bounty_upper_amount',0)} roi={p.get('roi_score',0):.1f}")
        print()
    
    # Biggest ROI changes
    changes = []
    for h in curr:
        if h in prev and curr[h].get("roi_score", 0) > 0 and prev[h].get("roi_score", 0) > 0:
            delta = curr[h]["roi_score"] - prev[h]["roi_score"]
            pct = delta / prev[h]["roi_score"] * 100 if prev[h]["roi_score"] else 0
            if abs(pct) > 10:  # >10% change
                changes.append((h, delta, pct))
    
    if changes:
        risers = sorted([c for c in changes if c[1] > 0], key=lambda x: x[2], reverse=True)
        fallers = sorted([c for c in changes if c[1] < 0], key=lambda x: x[2])
        
        if risers:
            print("📈 RISING ROI (>10% improvement):")
            for h, delta, pct in risers[:10]:
                p = curr[h]
                print(f"  {p['name'][:30]:30s} roi={p.get('roi_score',0):.1f} ({pct:+.0f}%)")
            print()
        
        if fallers:
            print("📉 FALLING ROI (>10% decline):")
            for h, delta, pct in fallers[:10]:
                p = curr[h]
                print(f"  {p['name'][:30]:30s} roi={p.get('roi_score',0):.1f} ({pct:+.0f}%)")
            print()
    
    # Programs that just got competitive (participant spike)
    crowding = []
    for h in curr:
        if h in prev:
            prev_ppl = prev[h].get("participants_count", 0) or 0
            curr_ppl = curr[h].get("participants_count", 0) or 0
            if prev_ppl > 0 and curr_ppl > prev_ppl * 1.2:
                crowding.append((h, prev_ppl, curr_ppl))
    
    if crowding:
        print("🚨 GETTING CROWDED (>20% participant increase):")
        for h, prev_ppl, curr_ppl in sorted(crowding, key=lambda x: x[2]/x[1], reverse=True)[:10]:
            p = curr[h]
            print(f"  {p['name'][:30]:30s} {prev_ppl}→{curr_ppl} participants")
        print()
    
    print("Done.")

if __name__ == "__main__":
    main()
