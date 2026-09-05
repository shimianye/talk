"""评测身份映射方案 1 的覆盖范围测试。"""
from unittest.mock import AsyncMock

from eval.identity import OWNER_BY_QUESTION_ID, identity_for_item


def test_owner_mapping_covers_exactly_the_eight_approved_samples():
    assert set(OWNER_BY_QUESTION_ID) == {81, 82, 83, 84, 85, 87, 88, 93}


async def test_non_identity_sample_stays_anonymous():
    identity = await identity_for_item(AsyncMock(), {"id": 1})
    assert identity.user_id is None
    assert identity.participates_in_owner_metric is False


async def test_explicit_order_owner_is_loaded_from_database():
    session = AsyncMock()
    session.scalar.return_value = "U6147"
    identity = await identity_for_item(session, {"id": 81})
    assert identity.user_id == "U6147"
    assert identity.participates_in_owner_metric is True
