import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


async def _create_request(client):
    with patch("app.service.publish", new=AsyncMock()):
        resp = await client.post("/approval-requests/", json={
            "tenant_id": str(TENANT_A),
            "request_type": "procurement_po",
            "reference_id": str(uuid.uuid4()),
        })
    return resp.json()


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_request_builds_3_steps(client):
    body = await _create_request(client)
    assert body["status"] == "pending"
    assert len(body["steps"]) == 3
    roles = [s["approver_role"] for s in body["steps"]]
    assert roles == ["manager", "director", "cfo"]
    orders = [s["order_number"] for s in body["steps"]]
    assert orders == [1, 2, 3]


@pytest.mark.asyncio
async def test_create_request_publishes_created_event(client):
    with patch("app.service.publish", new=AsyncMock()) as mock_pub:
        await client.post("/approval-requests/", json={
            "tenant_id": str(TENANT_A),
            "request_type": "procurement_po",
            "reference_id": str(uuid.uuid4()),
        })
        mock_pub.assert_awaited_once()
        assert mock_pub.await_args.args[0] == "approval.request.created"


@pytest.mark.asyncio
async def test_get_request(client):
    body = await _create_request(client)
    resp = await client.get(f"/approval-requests/{body['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_get_request_not_found(client):
    resp = await client.get(f"/approval-requests/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_approval_chain_emits_approved(client):
    body = await _create_request(client)
    req_id = body["id"]
    steps = body["steps"]

    with patch("app.service.publish", new=AsyncMock()) as mock_pub, \
            patch("app.routers.approvals._publish_request_outcome", new=AsyncMock()) as mock_out:
        # Approve all 3 in order
        for i, step in enumerate(steps):
            resp = await client.post(
                f"/approval-requests/{req_id}/steps/{step['id']}/approve",
                json={"approver_id": "user-1", "message": f"ok {i}"},
            )
            assert resp.status_code == 200

        # Final state approved
        assert resp.json()["status"] == "approved"
        mock_out.assert_awaited_once()
        assert mock_out.await_args.args[1] == "approval.request.approved"


@pytest.mark.asyncio
async def test_reject_step_rejects_request(client):
    body = await _create_request(client)
    req_id = body["id"]
    first_step = body["steps"][0]

    with patch("app.routers.approvals._publish_request_outcome", new=AsyncMock()) as mock_out:
        resp = await client.post(
            f"/approval-requests/{req_id}/steps/{first_step['id']}/reject",
            json={"approver_id": "user-1", "message": "no budget"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
        mock_out.assert_awaited_once()
        assert mock_out.await_args.args[1] == "approval.request.rejected"


@pytest.mark.asyncio
async def test_steps_must_be_approved_in_order(client):
    body = await _create_request(client)
    req_id = body["id"]
    second_step = body["steps"][1]  # director, not next

    resp = await client.post(
        f"/approval-requests/{req_id}/steps/{second_step['id']}/approve",
        json={"approver_id": "user-1"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cannot_approve_finished_request(client):
    body = await _create_request(client)
    req_id = body["id"]
    first_step = body["steps"][0]

    with patch("app.routers.approvals._publish_request_outcome", new=AsyncMock()):
        await client.post(
            f"/approval-requests/{req_id}/steps/{first_step['id']}/reject",
            json={"approver_id": "user-1"},
        )
        # Request already rejected — approving next step should 409
        resp = await client.post(
            f"/approval-requests/{req_id}/steps/{body['steps'][1]['id']}/approve",
            json={"approver_id": "user-1"},
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_comment_persisted_on_approve(client, db_session):
    from app.models import ApprovalComment
    from sqlmodel import select

    body = await _create_request(client)
    req_id = body["id"]
    first_step = body["steps"][0]

    with patch("app.routers.approvals._publish_request_outcome", new=AsyncMock()):
        await client.post(
            f"/approval-requests/{req_id}/steps/{first_step['id']}/approve",
            json={"approver_id": "user-7", "message": "looks good"},
        )

    result = await db_session.execute(select(ApprovalComment))
    comments = result.scalars().all()
    assert len(comments) == 1
    assert comments[0].approver_id == "user-7"
    assert comments[0].message == "looks good"
