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
    assert captured["profile_provider"] is provider


async def test_recompute_and_store_uses_artifact_and_report_versions(monkeypatch) -> None:
    from app.services.main import taste as taste_module
    from app.services.main.taste import TasteService

    artifact_repo = _FakeArtifactRepository()
    db = _RecordingDb()

    async def fake_for_user(self, user_id):  # noqa: ARG001
        return [object() for _ in range(10)]

    def fake_build_taste_refresh_artifacts(*args, **kwargs):  # noqa: ARG001
        return SimpleNamespace(
            report=_FakeReport(),
            entry_profiles=[_FakeEntryProfile()],
            user_profile=_FakeUserProfile(),
        )

    monkeypatch.setattr(taste_module.DiaryInputService, "for_user", fake_for_user)
    monkeypatch.setattr(
        taste_module,
        "build_taste_refresh_artifacts",
        fake_build_taste_refresh_artifacts,
    )
    monkeypatch.setattr(
        taste_module,
        "AlgorithmArtifactRepository",
        lambda db_session: artifact_repo,  # noqa: ARG005
        raising=False,
    )
    ctx = SimpleNamespace(db_session=db, profile_provider=object())

    await TasteService(ctx).recompute_and_store("u_versioned")

    assert artifact_repo.entry_profiles[0]["algorithm_version"] == "entry-v1"
    assert artifact_repo.user_profiles[0]["algorithm_version"] == "user-v1"
    assert db.added[0].algorithm_version == "report-v1"


class _FakeArtifactRepository:
    def __init__(self):
        self.entry_profiles = []
        self.user_profiles = []

    async def add_entry_profile(self, **kwargs):
        self.entry_profiles.append(kwargs)

    async def add_user_profile(self, **kwargs):
        self.user_profiles.append(kwargs)


class _RecordingDb:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


class _FakeEntryProfile:
    entry_id = "e_versioned"
    user_id = "u_versioned"

    def model_dump(self, *, mode: str) -> dict:  # noqa: ARG002
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "algorithm_version": "entry-v1",
        }


class _FakeUserProfile:
    user_id = "u_versioned"
    source_entry_count = 10
    algorithm_version = "user-v1"

    def model_dump(self, *, mode: str) -> dict:  # noqa: ARG002
        return {
            "user_id": self.user_id,
            "source_entry_count": self.source_entry_count,
            "long_term_embedding": [0.1] * 1024,
            "short_term_embedding": [0.2] * 1024,
            "algorithm_version": self.algorithm_version,
        }


class _FakeReport:
    has_enough_data = True
    algorithm_version = "report-v1"

    def model_dump(self, *, mode: str) -> dict:  # noqa: ARG002
        return {"has_enough_data": True, "algorithm_version": self.algorithm_version}
