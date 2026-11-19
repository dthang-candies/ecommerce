"""Forgotten password: request a one-time link by e-mail, then set a new password with it."""
import re
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from unicart.presentation.extended import deps
from unicart.presentation.wiring import build_services
from conftest import AN, SAMPLE_PASSWORD

NEW = "Moi@67890"


class Outbox:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))

    def token(self) -> str:
        return re.search(r"#token=([\w-]+)", self.sent[-1][2]).group(1)


@pytest.fixture()
def outbox(client):
    for budget in (deps.reset_budget, deps.reset_ip_budget):
        budget.hits.clear()
    deps.throttle.fails.clear()
    client.app.state.mailer = Outbox()
    return client.app.state.mailer


def forgot(client, email):
    return client.post("/api/auth/forgot-password", json={"email": email})


def reset(client, token, password=NEW):
    return client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def can_login(client, email, password) -> bool:
    return client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200


def test_reset_link_sets_a_new_password(client, outbox):
    assert forgot(client, "  An@Gmail.com ").status_code == 202
    assert [m[0] for m in outbox.sent] == [AN] and "/dat-lai-mat-khau#token=" in outbox.sent[0][2]
    assert reset(client, outbox.token()).status_code == 204
    assert can_login(client, AN, NEW) and not can_login(client, AN, SAMPLE_PASSWORD)


def test_unknown_and_locked_accounts_get_the_same_answer_and_no_mail(client, session, outbox):
    known = forgot(client, AN)
    session.execute(text("UPDATE account SET status='LOCKED' WHERE email='binh@gmail.com'"))
    session.commit()
    for email in ("nobody@example.com", "binh@gmail.com", "not-an-email"):
        r = forgot(client, email)
        assert (r.status_code, r.json()) == (known.status_code, known.json())
    assert [m[0] for m in outbox.sent] == [AN]


def test_link_works_only_once(client, outbox):
    forgot(client, AN)
    token = outbox.token()
    assert reset(client, token).status_code == 204
    r = reset(client, token, "Khac@11111")
    assert r.status_code == 400 and can_login(client, AN, NEW)


def test_a_newer_link_cancels_the_older_one(client, outbox):
    forgot(client, AN)
    old = outbox.token()
    forgot(client, AN)
    assert reset(client, old).status_code == 400
    assert reset(client, outbox.token()).status_code == 204


def test_expired_and_made_up_links_are_rejected(client, session, outbox):
    forgot(client, AN)
    session.execute(text("UPDATE password_reset SET expires_at=:t"), {"t": datetime.now() - timedelta(minutes=1)})
    session.commit()
    assert reset(client, outbox.token()).status_code == 400
    assert reset(client, "made-up-token").status_code == 400
    assert can_login(client, AN, SAMPLE_PASSWORD)


def test_weak_password_is_refused_without_using_up_the_link(client, outbox):
    forgot(client, AN)
    assert reset(client, outbox.token(), "short").status_code == 400
    assert reset(client, outbox.token()).status_code == 204


def test_only_the_hash_of_the_token_is_stored(client, session, outbox):
    forgot(client, AN)
    stored = session.execute(text("SELECT token_hash FROM password_reset")).scalar()
    assert len(stored) == 64 and stored != outbox.token()


def test_locking_the_account_after_the_request_blocks_the_link(client, session, outbox):
    forgot(client, AN)
    session.execute(text("UPDATE account SET status='LOCKED' WHERE email=:e"), {"e": AN})
    session.commit()
    assert reset(client, outbox.token()).status_code == 400


def test_mail_is_capped_per_mailbox_and_requests_per_client(client, outbox):
    for _ in range(5):
        assert forgot(client, AN).status_code == 202          # same answer, but ...
    assert len(outbox.sent) == 3                              # ... at most 3 mails per mailbox per 15 minutes
    for i in range(5):
        forgot(client, f"x{i}@example.com")
    assert forgot(client, "y@example.com").status_code == 429  # 10 requests per client address


def test_staff_can_reset_too_and_reset_clears_the_login_lockout(client, outbox):
    for _ in range(8):
        can_login(client, "admin@abc.vn", "wrong-password")
    assert client.post("/api/auth/login", json={"email": "admin@abc.vn", "password": SAMPLE_PASSWORD}).status_code == 429
    forgot(client, "admin@abc.vn")
    assert reset(client, outbox.token()).status_code == 204
    assert can_login(client, "admin@abc.vn", NEW)


def test_migration_creates_the_table_on_an_existing_database(db, session):
    from unicart.migrate import migrate
    session.execute(text("DROP TABLE password_reset"))
    session.commit()
    assert migrate(db) == ["password_reset"] and migrate(db) == []
    assert build_services(session).auth.request_password_reset(AN) is not None
