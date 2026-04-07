#!/usr/bin/env python3
"""
HackerOne Full Program Scraper
Paginates through ALL programs via GraphQL cursor pagination.
Filters to bounty programs with data, scores them, outputs ranked JSON + CSV.
"""
import json
import urllib.request
import time
import sys

QUERY = """
query($cursor: String) {
  teams(first: 100, after: $cursor) {
    total_count
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        handle
        name
        offers_bounties
        average_bounty_lower_amount
        average_bounty_upper_amount
        top_bounty_lower_amount
        top_bounty_upper_amount
        minimum_bounty
        resolved_report_count
        reports_received_last_90_days
        response_efficiency_percentage
        participants_count
        submission_state
      }
    }
  }
}
"""

def fetch_page(cursor=None):
    variables = {"cursor": cursor} if cursor else {}
    data = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://hackerone.com/graphql",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "TommyClawd-Research/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def score_program(t):
    """V2 ROI scoring: EP × RQ × AH / CP"""
    avg = t.get("average_bounty_upper_amount", 0) or 0
    min_b = t.get("minimum_bounty", 0) or 0
    max_b = t.get("top_bounty_upper_amount", 0) or 0
    eff = t.get("response_efficiency_percentage", 0) or 0
    participants = t.get("participants_count", 1) or 1
    resolved = t.get("resolved_report_count", 0) or 0
    recent = t.get("reports_received_last_90_days", 0) or 0
    
    # Expected Payout
    ep = avg if avg > 0 else (min_b + max_b) / 4 if (min_b + max_b) > 0 else 0
    if ep == 0: return 0
    
    # Response Quality (0.5 to 1.2)
    rq = min(1.2, max(0.5, eff / 100 + (0.1 if eff > 95 else 0))) if eff > 0 else 0.5
    
    # Activity Health (0.5 to 2.0)
    ah = min(2.0, max(0.5, resolved / max(1, recent * 4)))
    
    # Competition Pressure
    from math import sqrt
    cp = sqrt(max(1, participants))
    
    return round((ep * rq * ah) / cp, 2)

def main():
    all_teams = []
    cursor = None
    page = 0
    total = None
    
    while True:
        page += 1
        result = fetch_page(cursor)
        teams_data = result["data"]["teams"]
        
        if total is None:
            total = teams_data["total_count"]
            print(f"Total programs on HackerOne: {total}")
        
        edges = teams_data["edges"]
        for edge in edges:
            all_teams.append(edge["node"])
        
        print(f"  Page {page}: fetched {len(edges)} (total so far: {len(all_teams)})")
        
        if not teams_data["pageInfo"]["hasNextPage"]:
            break
        
        cursor = teams_data["pageInfo"]["endCursor"]
        time.sleep(0.5)  # Be respectful
    
    print(f"\nFetched {len(all_teams)} total programs")
    
    # Filter and score
    bounty_programs = [t for t in all_teams if t.get("offers_bounties")]
    for t in bounty_programs:
        t["roi_score"] = score_program(t)
    
    bounty_programs.sort(key=lambda t: t["roi_score"], reverse=True)
    
    print(f"Bounty programs: {len(bounty_programs)}")
    print(f"\nTop 20 by ROI:")
    print(f"{'Rank':>4} {'Program':30s} {'Avg$':>7s} {'Top$':>8s} {'Eff%':>5s} {'People':>7s} {'Score':>7s}")
    print("-" * 75)
    for i, t in enumerate(bounty_programs[:20], 1):
        name = t["name"][:30]
        avg = t.get("average_bounty_upper_amount", 0) or 0
        top = t.get("top_bounty_upper_amount", 0) or 0
        eff = t.get("response_efficiency_percentage", 0) or 0
        ppl = t.get("participants_count", 0) or 0
        print(f"{i:>4} {name:30s} {avg:>7,d} {top:>8,d} {eff:>5d} {ppl:>7,d} {t['roi_score']:>7.1f}")
    
    # Save full dataset
    outpath = "/home/riclewis/.openclaw/workspace/research/hackerone-full-dataset.json"
    with open(outpath, "w") as f:
        json.dump({
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_programs": len(all_teams),
            "bounty_programs": len(bounty_programs),
            "programs": bounty_programs
        }, f, indent=2)
    
    print(f"\nFull dataset saved to {outpath}")
    print(f"  {len(bounty_programs)} bounty programs with ROI scores")

if __name__ == "__main__":
    main()
