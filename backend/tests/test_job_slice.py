from eval.job_slice import JOB_SIGNAL_EVAL_IDS, job_slice_hash, select_job_slice


def test_job_slice_is_fixed_unique_and_stratified_across_ranges():
    assert len(JOB_SIGNAL_EVAL_IDS) == 24
    assert len(set(JOB_SIGNAL_EVAL_IDS)) == 24
    assert any(item_id <= 30 for item_id in JOB_SIGNAL_EVAL_IDS)
    assert any(31 <= item_id <= 50 for item_id in JOB_SIGNAL_EVAL_IDS)
    assert any(51 <= item_id <= 65 for item_id in JOB_SIGNAL_EVAL_IDS)
    assert any(66 <= item_id <= 80 for item_id in JOB_SIGNAL_EVAL_IDS)
    assert any(81 <= item_id <= 90 for item_id in JOB_SIGNAL_EVAL_IDS)
    assert any(item_id >= 91 for item_id in JOB_SIGNAL_EVAL_IDS)


def test_job_slice_selection_order_and_hash_are_stable():
    items = [{"id": item_id, "question": f"q-{item_id}"} for item_id in range(1, 101)]
    selected = select_job_slice(items)
    assert [item["id"] for item in selected] == list(JOB_SIGNAL_EVAL_IDS)
    assert job_slice_hash(selected) == job_slice_hash(select_job_slice(list(reversed(items))))
