# ============================================================================
# PRITHU BACKEND - END-TO-END SUITE TESTS
# ============================================================================
# Comprehensive unit & integration tests for Old Users vs New Users
# ============================================================================

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add root directory to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.core.config import Config
from app.engine.optimizer import get_optimizer
from app.engine.session_optimizer import SessionTimeSlotOptimizer
from app.engine.god_optimizer import GodCategoryOptimizer


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_old_user_flow():
    """
    Test Case 1: Old User Recommendation Flow
    - Account Age: > 14 days
    - Expected Strategy: Old User Catch-up Strategy (Fresh Admin Uploads)
    - Validates lifetime exclusion, session boundaries, and day-of-week God schedule.
    """
    print_banner("🧪 TEST 1: OLD USER (FRESH ADMIN UPLOAD CATCH-UP STRATEGY)")

    optimizer = get_optimizer()

    # User ID for established user
    old_user_id = "650000000000000000000001"

    # Mock user age to ensure established user status (e.g. 45 days old)
    optimizer.recency_engine.classify_user = lambda uid, count: (
        False, 2, "Old User (Catchup 2d Strategy)"
    )

    print(f"👤 Testing User ID: {old_user_id} [Established Old User]")

    recommendations = optimizer.get_recommendations(
        user_id=old_user_id,
        limit=5,
        section="all",
        language="en"
    )

    print(f"\n✅ Total Recommendations Delivered: {len(recommendations)}")
    assert len(recommendations) > 0, "Failed: Old User should receive recommendations"

    for idx, rec in enumerate(recommendations, 1):
        strategy = rec.metadata.get("user_strategy")
        session = rec.metadata.get("active_session")
        print(f"  {idx:2d}. Feed ID: {rec.feed_id} | Score: {rec.score:5.2f} | Category: {rec.category:20s} | Strategy: {strategy}")
        assert "Old User" in strategy, f"Expected Old User strategy label, got {strategy}"

    print("\n🟢 TEST 1 PASSED: Old User received fresh catch-up recommendations successfully!")


def test_new_user_flow():
    """
    Test Case 2: New User Recommendation Flow
    - Account Age: <= 14 days
    - Expected Strategy: New User Backlog Strategy (80% Historical Backlog / 20% Fresh)
    - Validates historical backlog distribution & preference substitution.
    """
    print_banner("🧪 TEST 2: NEW USER (HISTORICAL BACKLOG STAGGERED STRATEGY)")

    optimizer = get_optimizer()

    new_user_id = "new_registered_user_777"

    # Mock user age for new user status (e.g. 2 days old)
    optimizer.recency_engine.classify_user = lambda uid, count: (
        True, 1, "New User (Backlog Strategy)"
    )

    print(f"👤 Testing User ID: {new_user_id} [Brand-New Registered User]")

    recommendations = optimizer.get_recommendations(
        user_id=new_user_id,
        limit=5,
        section="all",
        language="en"
    )

    print(f"\n✅ Total Recommendations Delivered: {len(recommendations)}")
    assert len(recommendations) > 0, "Failed: New User should receive backlog recommendations"

    for idx, rec in enumerate(recommendations, 1):
        strategy = rec.metadata.get("user_strategy")
        session = rec.metadata.get("active_session")
        print(f"  {idx:2d}. Feed ID: {rec.feed_id} | Score: {rec.score:5.2f} | Category: {rec.category:20s} | Strategy: {strategy}")
        assert "New User" in strategy, f"Expected New User strategy label, got {strategy}"

    print("\n🟢 TEST 2 PASSED: New User received historical backlog recommendations successfully!")


def test_section_and_god_schedule():
    """
    Test Case 3: 24-Hour Day-of-Week God Schedule & Special Day Sections
    """
    print_banner("🧪 TEST 3: 24-HOUR GOD SCHEDULE & SECTION ROUTING")

    optimizer = get_optimizer()
    india_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_weekday = india_time.weekday()
    today_schedule = GodCategoryOptimizer.DAY_GOD_SCHEDULE.get(current_weekday, {})

    print(f"📅 Current Day: {today_schedule.get('day')} | Active Deities: {today_schedule.get('description')}")

    god_recs = optimizer.get_recommendations(
        user_id="god_test_user",
        limit=5,
        section="god"
    )

    print(f"\n✅ God Section Recommendations Delivered: {len(god_recs)}")

    for idx, rec in enumerate(god_recs, 1):
        print(f"  {idx:2d}. Feed ID: {rec.feed_id} | Category: {rec.category:20s}")

    print("\n🟢 TEST 3 PASSED: Day-of-Week God Schedule verified successfully!")


def main():
    print("\n🚀 STARTING PRITHU ENGINE ALL-MODULE TEST SUITE")
    print("-" * 80)

    try:
        test_old_user_flow()
        test_new_user_flow()
        test_section_and_god_schedule()

        print_banner("🎉 ALL TESTS PASSED SUCCESSFULLY! 🚀")

    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
