from types import SimpleNamespace

import pytest


class _EmptyScalars:
    def first(self):
        return None


class _EmptyResult:
    def scalars(self):
        return _EmptyScalars()


class _FakeDb:
    async def execute(self, stmt):  # noqa: ARG002
        return _EmptyResult()


@pytest.mark.parametrize(
    ("entry_count", "expected_payload"),
    [
        (3, {"has_enough_data": False}),
        (10, {"has_enough_data": True}),
    ],
)
async def test_get_profile_computes_payload_without_stored_report(
    monkeypatch,
    entry_count,
    expected_payload,
) -> None:
    from app.services.main import taste as taste_module
    from app.services.main.taste import TasteService

    async def fake_for_user(self, user_id):  # noqa: ARG001
        return [object() for _ in range(entry_count)]

    async def fake_compute_payload(self, user_id):  # noqa: ARG001
        return expected_payload

    monkeypatch.setattr(taste_module.DiaryInputService, "for_user", fake_for_user)
    monkeypatch.setattr(TasteService, "_compute_payload", fake_compute_payload)
    ctx = SimpleNamespace(db_session=_FakeDb(), profile_provider=object())

    payload = await TasteService(ctx).get_profile("u_taste")

    assert payload == expected_payload


async def test_compute_payload_passes_context_provider_to_taste_report(monkeypatch) -> None:
    from app.services.main import taste as taste_module
    from app.services.main.taste import TasteService

    provider = object()
    captured: dict[str, object] = {}

    async def fake_for_user(self, user_id):  # noqa: ARG001
        return [object()]

    class FakeReport:
        def model_dump(self, *, mode: str) -> dict:  # noqa: ARG002
            return {"has_enough_data": False}

    def fake_generate_taste_report(user_id, entries, **kwargs):  # noqa: ARG001
        captured.update(kwargs)
        return FakeReport()

    monkeypatch.setattr(taste_module.DiaryInputService, "for_user", fake_for_user)
    monkeypatch.setattr(taste_module, "generate_taste_report", fake_generate_taste_report)
    ctx = SimpleNamespace(db_session=_FakeDb(), profile_provider=provider)

    payload = await TasteService(ctx)._compute_payload("u_provider")

    assert payload == {"has_enough_data": False}
    assert captured["ml_provider"] is provider
