from httpx import AsyncClient


async def test_submit_job(client: AsyncClient):
    r = await client.post(
        "/jobs/", json={"job_type": "work", "payload": {"duration": 0.1}}
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "queued"
    assert data["job_type"] == "work"


async def test_get_job(client: AsyncClient):
    create = await client.post("/jobs/", json={"job_type": "work", "payload": {}})
    job_id = create.json()["id"]
    r = await client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["id"] == job_id


async def test_get_nonexistent_job(client: AsyncClient):
    r = await client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_list_jobs(client: AsyncClient):
    await client.post("/jobs/", json={"job_type": "work", "payload": {}})
    await client.post("/jobs/", json={"job_type": "unreliable", "payload": {}})
    r = await client.get("/jobs/")
    assert r.status_code == 200
    assert len(r.json()) >= 2


async def test_stats(client: AsyncClient):
    await client.post("/jobs/", json={"job_type": "work", "payload": {}})
    r = await client.get("/jobs/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "queue_depth" in data
    assert data["total"] >= 1
