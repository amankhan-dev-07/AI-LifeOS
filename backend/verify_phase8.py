"""
Phase 8 runtime verification.

Exercises the onboarding state against a real TestClient over the real app —
no mocks — so the checks below observe actual persistence rather than
simulating it.

Run:  python verify_phase8.py
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register(client: TestClient) -> tuple[str, int]:
    email = f"phase8_{uuid.uuid4().hex[:12]}@lifeos-probe.example.com"

    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Phase Eight Probe",
            "password": "Str0ng-Passw0rd!",
        },
    )
    assert res.status_code == 201, f"register failed: {res.status_code} {res.text}"

    user_id = res.json()["id"]

    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Str0ng-Passw0rd!"},
    )
    assert res.status_code == 200, f"login failed: {res.status_code} {res.text}"

    return res.json()["access_token"], user_id


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        raise AssertionError(label)


def main() -> None:
    with TestClient(app) as client:
        print("=== 1. Fresh account starts with onboarding incomplete ===")
        token_a, user_a = _register(client)

        res = client.get("/api/v1/preferences", headers=_headers(token_a))
        check("GET /preferences is 200", res.status_code == 200, str(res.status_code))
        prefs = res.json()
        check(
            "response carries onboarding_completed",
            "onboarding_completed" in prefs,
            str(sorted(prefs.keys())),
        )
        check(
            "onboarding_completed defaults to False",
            prefs["onboarding_completed"] is False,
            repr(prefs.get("onboarding_completed")),
        )
        check(
            "onboarding_version defaults to 1",
            prefs.get("onboarding_version") == 1,
            repr(prefs.get("onboarding_version")),
        )
        check(
            "timezone/time_format intact",
            prefs.get("timezone") and prefs.get("time_format"),
            f"{prefs.get('timezone')} / {prefs.get('time_format')}",
        )

        print("\n=== 2. A fresh account has no data (dashboard shows EmptyOnboarding) ===")
        res = client.get("/api/v1/intelligence", headers=_headers(token_a))
        check("GET /intelligence is 200", res.status_code == 200, str(res.status_code))
        intel = res.json()
        check("has_data is False for a fresh account", intel["has_data"] is False)

        print("\n=== 3. First action persists real data ===")
        res = client.post(
            "/api/v1/tasks",
            headers=_headers(token_a),
            json={"title": "Review PR #42", "priority": "high", "estimated_minutes": 30},
        )
        check("POST /tasks creates a task", res.status_code == 201, str(res.status_code))

        res = client.get("/api/v1/intelligence", headers=_headers(token_a))
        check("has_data is now True", res.json()["has_data"] is True)

        print("\n=== 4. Completion persists to the server ===")
        res = client.patch(
            "/api/v1/preferences",
            headers=_headers(token_a),
            json={"onboarding_completed": True},
        )
        check("PATCH /preferences is 200", res.status_code == 200, str(res.status_code))
        check("patch response is completed", res.json()["onboarding_completed"] is True)

        print("\n=== 5. State survives a fresh read (no client-side cache) ===")
        res = client.get("/api/v1/preferences", headers=_headers(token_a))
        check("re-read is still completed", res.json()["onboarding_completed"] is True)

        print("\n=== 6. Logout/login does not reset the flag ===")
        token_a2, _ = _relogin(client, user_a)
        res = client.get("/api/v1/preferences", headers=_headers(token_a2))
        check("after re-login the flag is still completed", res.json()["onboarding_completed"] is True)

        print("\n=== 7. Skip path: a second account can skip straight to the dashboard ===")
        token_b, user_b = _register(client)
        res = client.patch(
            "/api/v1/preferences",
            headers=_headers(token_b),
            json={"onboarding_completed": True},
        )
        check("skip persists", res.status_code == 200 and res.json()["onboarding_completed"] is True)
        res = client.get("/api/v1/intelligence", headers=_headers(token_b))
        check(
            "skipped account with no data still gets an empty dashboard",
            res.json()["has_data"] is False,
        )

        print("\n=== 8. Unauthenticated access is rejected ===")
        res = client.get("/api/v1/preferences")
        check("no token -> 401", res.status_code == 401, str(res.status_code))

        print("\n=== 9. No cross-user leakage ===")
        res = client.get("/api/v1/preferences", headers=_headers(token_a))
        check("A still completed", res.json()["onboarding_completed"] is True)
        check("A's prefs belong to A", res.json()["user_id"] == user_a, str(res.json()["user_id"]))

        res = client.get("/api/v1/preferences", headers=_headers(token_b))
        check("B's prefs belong to B", res.json()["user_id"] == user_b, str(res.json()["user_id"]))

        res = client.patch(
            "/api/v1/preferences",
            headers=_headers(token_b),
            json={"onboarding_completed": False},
        )
        check(
            "B flipping its own flag does not touch A",
            client.get("/api/v1/preferences", headers=_headers(token_a)).json()["onboarding_completed"] is True,
        )

        print("\n=== 10. Existing preferences are untouched by a partial patch ===")
        res = client.patch(
            "/api/v1/preferences",
            headers=_headers(token_a),
            json={"onboarding_completed": True},
        )
        body = res.json()
        check(
            "theme/timezone/time_format survive the onboarding patch",
            body["timezone"] and body["time_format"] and body["theme"],
            f"{body['theme']} / {body['timezone']} / {body['time_format']}",
        )
        check("reminder settings untouched", body["daily_briefing_enabled"] is True)

        print("\n=== 11. Invalid values are rejected, not silently stored ===")
        res = client.patch(
            "/api/v1/preferences",
            headers=_headers(token_a),
            json={"onboarding_version": "not-an-int"},
        )
        check("bad onboarding_version -> 422", res.status_code == 422, str(res.status_code))

        print("\nAll Phase 8 backend checks completed.")


def _relogin(client: TestClient, user_id: int) -> tuple[str, int]:
    """Re-authenticate as an already-registered user, to prove state survives login."""

    email = _email_for(user_id)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Str0ng-Passw0rd!"},
    )
    assert res.status_code == 200, f"re-login failed: {res.status_code} {res.text}"
    return res.json()["access_token"], user_id


def _email_for(user_id: int) -> str:
    from app.db.session import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return user.email


if __name__ == "__main__":
    main()