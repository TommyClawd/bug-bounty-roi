#!/usr/bin/env python3
"""
Bugcrowd full program scraper.
- Paginates all engagements
- Filters to cash-paying Bug Bounty programs
- Computes simple ROI-like score using scope rank/private flag proxy
- Writes full filtered dataset JSON
- Prints top 20 programs by max reward
"""

import json
import re
import time
import urllib.request
from typing import Any, Dict, List, Optional

BASE_URL = "https://bugcrowd.com/engagements.json"
OUT_PATH = "/home/riclewis/.openclaw/workspace/research/bugcrowd-full-dataset.json"


def fetch_page(page: int) -> Dict[str, Any]:
    url = f"{BASE_URL}?page={page}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TommyClawd-Research/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def parse_money(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    # Keep digits only: "$7,500" -> "7500"
    digits = re.sub(r"[^0-9]", "", str(value))
    if not digits:
        return None
    return int(digits)


def is_cash_program(eng: Dict[str, Any]) -> bool:
    reward = eng.get("rewardSummary") or {}
    min_reward = reward.get("minReward")
    max_reward = reward.get("maxReward")

    min_val = parse_money(min_reward)
    max_val = parse_money(max_reward)

    if min_val is None and max_val is None:
        return False

    # Defensive guard against non-cash representations
    blob = " ".join(
        [
            str(reward.get("summary") or ""),
            str(reward.get("compensationSummary") or ""),
            str(min_reward or ""),
            str(max_reward or ""),
        ]
    ).lower()
    if "point" in blob and "$" not in blob and "usd" not in blob:
        return False

    return True


def roi_score(max_reward: int, scope_rank: Optional[int], is_private: bool) -> float:
    # Lower scopeRank generally implies stronger target (and likely more competition).
    # Use it as a simple competition proxy; private programs get a small competition discount.
    rank = scope_rank if isinstance(scope_rank, int) and scope_rank > 0 else 5
    competition_proxy = max(1.0, float(rank))
    if is_private:
        competition_proxy *= 0.8
    return round(max_reward / competition_proxy, 2)


def main() -> None:
    all_programs: List[Dict[str, Any]] = []
    page = 1
    total_count = None
    limit = None

    while True:
        payload = fetch_page(page)
        engagements = payload.get("engagements", [])
        meta = payload.get("paginationMeta") or {}

        if total_count is None:
            total_count = meta.get("totalCount")
            limit = meta.get("limit")
            print(f"Total Bugcrowd programs reported: {total_count} (page size: {limit})")

        if not engagements:
            break

        all_programs.extend(engagements)
        print(f"  Page {page}: fetched {len(engagements)} (total so far: {len(all_programs)})")

        if total_count and len(all_programs) >= int(total_count):
            break

        page += 1
        time.sleep(0.25)

    print(f"\nFetched {len(all_programs)} total programs")

    filtered: List[Dict[str, Any]] = []
    for eng in all_programs:
        engagement_type = (eng.get("productEngagementType") or {}).get("label")
        if engagement_type != "Bug Bounty":
            continue
        if not is_cash_program(eng):
            continue

        reward = eng.get("rewardSummary") or {}
        min_reward = parse_money(reward.get("minReward")) or 0
        max_reward = parse_money(reward.get("maxReward")) or 0

        item = {
            "name": eng.get("name"),
            "briefUrl": eng.get("briefUrl"),
            "industryName": eng.get("industryName"),
            "accessStatus": eng.get("accessStatus"),
            "serviceLevel": eng.get("serviceLevel"),
            "isPrivate": bool(eng.get("isPrivate")),
            "scopeRank": eng.get("scopeRank"),
            "engagementType": engagement_type,
            "rewardSummaryText": reward.get("summary"),
            "minReward": min_reward,
            "maxReward": max_reward,
        }
        item["roiScore"] = roi_score(
            max_reward=max_reward,
            scope_rank=item.get("scopeRank"),
            is_private=item["isPrivate"],
        )
        filtered.append(item)

    filtered.sort(key=lambda x: (x.get("maxReward", 0), x.get("roiScore", 0)), reverse=True)

    for idx, p in enumerate(filtered, 1):
        p["maxRewardRank"] = idx

    out = {
        "scrapedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "https://bugcrowd.com/engagements.json",
        "totalPrograms": len(all_programs),
        "filteredPrograms": len(filtered),
        "filters": {
            "engagementType": "Bug Bounty",
            "cashRewardsOnly": True,
        },
        "programs": filtered,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Filtered cash bug bounty programs: {len(filtered)}")
    print(f"Dataset saved: {OUT_PATH}")

    print("\nTop 20 Bugcrowd programs by max reward:")
    print(f"{'Rank':>4} {'Program':35s} {'Min$':>8s} {'Max$':>10s} {'Scope':>6s} {'Private':>8s} {'ROI':>10s}")
    print("-" * 95)
    for i, p in enumerate(filtered[:20], 1):
        name = (p.get("name") or "")[:35]
        scope = p.get("scopeRank") if p.get("scopeRank") is not None else "-"
        private = "yes" if p.get("isPrivate") else "no"
        print(
            f"{i:>4} {name:35s} "
            f"{p.get('minReward', 0):>8,d} {p.get('maxReward', 0):>10,d} "
            f"{str(scope):>6s} {private:>8s} {p.get('roiScore', 0):>10,.2f}"
        )


if __name__ == "__main__":
    main()
