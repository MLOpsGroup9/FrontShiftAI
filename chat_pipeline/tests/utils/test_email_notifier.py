from chat_pipeline.utils import email_notifier


def test_send_email_returns_false_when_missing_creds(monkeypatch):
    monkeypatch.setattr(email_notifier, "_load_creds", lambda: (None, None, None))
    monkeypatch.setattr(email_notifier.smtplib, "SMTP_SSL", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not connect")))  # type: ignore[attr-defined]

    sent = email_notifier.send_email("subj", "msg")

    assert sent is False


def test_send_email_uses_smtp_ssl(monkeypatch):
    calls = {}

    class DummySMTP:
        def __init__(self, host, port, timeout):
            calls["init"] = (host, port, timeout)
            self.logged_in = None
            self.sent = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, sender, password):
            calls["login"] = (sender, password)

        def send_message(self, msg):
            calls["sent"] = msg

    monkeypatch.setattr(email_notifier.smtplib, "SMTP_SSL", DummySMTP)  # type: ignore[attr-defined]

    sent = email_notifier.send_email(
        "subj",
        "msg",
        sender="from@example.com",
        password="secret",
        receiver="to@example.com",
        smtp_host="smtp.test",
        smtp_port=465,
        timeout=5,
    )

    assert sent is True
    assert calls["init"] == ("smtp.test", 465, 5)
    assert calls["login"] == ("from@example.com", "secret")
    assert "sent" in calls


def test_send_email_starttls_path(monkeypatch):
    calls = {}

    class DummySMTP:
        def __init__(self, host, port, timeout):
            calls["init"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            calls["starttls"] = True

        def login(self, sender, password):
            calls["login"] = (sender, password)

        def send_message(self, msg):
            calls["sent"] = msg

    monkeypatch.setattr(email_notifier.smtplib, "SMTP", DummySMTP)  # type: ignore[attr-defined]

    sent = email_notifier.send_email(
        "subj",
        "msg",
        sender="from@example.com",
        password="secret",
        receiver="to@example.com",
        smtp_host="smtp.test",
        smtp_port=587,
        timeout=5,
    )

    assert sent is True
    assert calls["init"] == ("smtp.test", 587, 5)
    assert calls["starttls"] is True
    assert calls["login"] == ("from@example.com", "secret")
    assert "sent" in calls
