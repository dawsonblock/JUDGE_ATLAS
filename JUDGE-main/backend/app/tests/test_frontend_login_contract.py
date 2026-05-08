from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def test_login_page_posts_email_password_payload() -> None:
    content = (FRONTEND_ROOT / "app/login/page.tsx").read_text(encoding="utf-8")
    assert "JSON.stringify({ email, password })" in content
    assert "username: email" not in content


def test_login_route_forwards_received_body() -> None:
    content = (FRONTEND_ROOT / "app/api/auth/login/route.ts").read_text(
        encoding="utf-8"
    )
    assert "body = await req.json()" in content
    assert "body: JSON.stringify(body)" in content
