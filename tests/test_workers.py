from app.workers.task_handlers import handle_unreliable, handle_work


async def test_handle_work_succeeds():
    result = await handle_work({"duration": 0.01})
    assert result["status"] == "done"


async def test_handle_unreliable_sometimes_fails():
    """Run 20 times — statistically should see both success and failure."""
    results = []
    for _ in range(20):
        try:
            await handle_unreliable({})
            results.append("success")
        except RuntimeError:
            results.append("failure")
    assert "success" in results
    assert "failure" in results


async def test_handle_work_duration_respected():
    import time

    start = time.perf_counter()
    await handle_work({"duration": 0.1})
    assert time.perf_counter() - start >= 0.1
