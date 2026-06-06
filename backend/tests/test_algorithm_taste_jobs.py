import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError


def test_taste_job_model_allows_historical_rows_per_user() -> None:
    from app.models.taste_job import TasteJobModel

    assert _unique_columns(TasteJobModel) == set()


def test_taste_jobs_migration_unique_index_only_covers_active_jobs() -> None:
    migration = _load_algorithm_migration()
    op = _RecordingMigrationOp()
    migration.op = op

    migration.upgrade()

    taste_job_constraints = op.tables["taste_jobs"]
    assert not any(
        isinstance(constraint, UniqueConstraint)
        and tuple(constraint.columns.keys()) == ("user_id",)
        for constraint in taste_job_constraints
    )
    active_index = op.indexes["uq_taste_jobs_active_user_id"]
    assert active_index.args == ("taste_jobs", ["user_id"])
    assert active_index.kwargs["unique"] is True
    assert str(active_index.kwargs["postgresql_where"]) == "state IN ('queued', 'running')"


async def test_repository_reuses_active_job_without_requeue() -> None:
    from app.models.taste_job import TasteJobModel
    from app.repositories.taste_job import TasteJobRepository

    job = TasteJobModel(id="tj_active", user_id="u_1", state="running")
    db = _TasteJobDb([job])

    repo = TasteJobRepository(db)
    returned, newly_queued = await repo.get_or_create_for_user("u_1")

    assert returned is job
    assert newly_queued is False
    assert job.id == "tj_active"
    assert db.added == []
    assert db.commits == 1


async def test_repository_creates_new_row_after_finished_job(monkeypatch) -> None:
    from app.models.taste_job import TasteJobModel
    from app.repositories import taste_job as taste_job_repo

    started_at = datetime(2026, 6, 1, 12, tzinfo=UTC)
    finished_at = datetime(2026, 6, 1, 12, 5, tzinfo=UTC)
    job = TasteJobModel(
        id="tj_old",
        user_id="u_1",
        state="failed",
        started_at=started_at,
        finished_at=finished_at,
        error="old failure",
    )
    monkeypatch.setattr(taste_job_repo, "make_id", lambda prefix: f"{prefix}_new")
    db = _TasteJobDb([job])

    returned, newly_queued = await taste_job_repo.TasteJobRepository(
        db
    ).get_or_create_for_user("u_1")

    assert returned is not job
    assert newly_queued is True
    assert returned.id == "tj_new"
    assert returned.user_id == "u_1"
    assert returned.state == "queued"
    assert returned.started_at is None
    assert returned.finished_at is None
    assert returned.error is None
    assert job.id == "tj_old"
    assert job.state == "failed"
    assert job.started_at == started_at
    assert job.finished_at == finished_at
    assert job.error == "old failure"
    assert db.added == [returned]
    assert db.commits == 1


async def test_repository_finds_job_by_id_and_user_scope() -> None:
    from app.models.taste_job import TasteJobModel
    from app.repositories.taste_job import TasteJobRepository

    job = TasteJobModel(id="tj_lookup", user_id="u_owner", state="queued")
    db = _TasteJobDb([job])

    repo = TasteJobRepository(db)
    found = await repo.find_for_user("tj_lookup", "u_owner")
    wrong_user = await repo.find_for_user("tj_lookup", "u_other")

    assert found is job
    assert wrong_user is None
    lookup_sql = [_compile_sql(stmt) for stmt in db.statements]
    assert all("taste_jobs.id =" in sql for sql in lookup_sql)
    assert all("taste_jobs.user_id =" in sql for sql in lookup_sql)


async def test_repository_returns_active_job_after_duplicate_insert_conflict(
    monkeypatch,
) -> None:
    from app.models.taste_job import TasteJobModel
    from app.repositories import taste_job as taste_job_repo

    active = TasteJobModel(id="tj_active", user_id="u_1", state="queued")
    monkeypatch.setattr(taste_job_repo, "make_id", lambda prefix: f"{prefix}_attempt")
    db = _InsertConflictDb(active)

    returned, newly_queued = await taste_job_repo.TasteJobRepository(
        db
    ).get_or_create_for_user("u_1")

    assert returned is active
    assert newly_queued is False
    assert db.rollbacks == 1
    assert [job.id for job in db.added] == ["tj_attempt"]
    lookup_sql = [_compile_sql(stmt) for stmt in db.statements]
    assert all("taste_jobs.state IN" in sql for sql in lookup_sql)


async def test_repository_marks_failed_with_error_text(monkeypatch) -> None:
    from app.models.taste_job import TasteJobModel
    from app.repositories import taste_job as taste_job_repo

    started_at = datetime(2026, 6, 1, 12, tzinfo=UTC)
    failed_at = datetime(2026, 6, 1, 12, 1, tzinfo=UTC)
    job = TasteJobModel(
        id="tj_fail",
        user_id="u_1",
        state="running",
        started_at=started_at,
    )
    monkeypatch.setattr(taste_job_repo, "utcnow", lambda: failed_at)

    await taste_job_repo.TasteJobRepository(_TasteJobDb([job])).mark_failed(
        "tj_fail",
        "u_1",
        "provider down",
    )

    assert job.state == "failed"
    assert job.started_at == started_at
    assert job.finished_at == failed_at
    assert job.error == "provider down"


async def test_refresh_endpoint_reuses_active_job_without_second_task(monkeypatch) -> None:
    from app.controllers import taste as taste_controller
    from app.models.taste_job import TasteJobModel

    job = TasteJobModel(id="tj_active", user_id="u_1", state="queued")
    repo = _FakeControllerRepo([(job, True), (job, False)])
    monkeypatch.setattr(taste_controller, "TasteJobRepository", lambda db: repo)

    background_tasks = _RecordingBackgroundTasks()
    request = SimpleNamespace(state=SimpleNamespace(context=object()))
    ctx = SimpleNamespace(db_session=object())
    user = SimpleNamespace(user_id="u_1")

    first = await taste_controller.refresh(background_tasks, request, ctx, user)
    second = await taste_controller.refresh(background_tasks, request, ctx, user)

    assert first.response.job_id == "tj_active"
    assert second.response.job_id == "tj_active"
    assert first.response.status == "queued"
    assert second.response.status == "queued"
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].args == (request.state.context, "u_1", "tj_active")


async def test_job_status_endpoint_returns_user_scoped_job(monkeypatch) -> None:
    from app.controllers import taste as taste_controller
    from app.models.taste_job import TasteJobModel

    started_at = datetime(2026, 6, 1, 12, tzinfo=UTC)
    job = TasteJobModel(
        id="tj_status",
        user_id="u_1",
        state="running",
        started_at=started_at,
    )
    repo = _FakeControllerRepo([], found=job)
    monkeypatch.setattr(taste_controller, "TasteJobRepository", lambda db: repo)

    response = await taste_controller.get_refresh_job(
        "tj_status",
        SimpleNamespace(db_session=object()),
        SimpleNamespace(user_id="u_1"),
    )

    assert response.response.job_id == "tj_status"
    assert response.response.status == "running"
    assert response.response.started_at == started_at
    assert response.response.finished_at is None
    assert response.response.error is None
    assert repo.find_requests == [("tj_status", "u_1")]


async def test_job_status_endpoint_404s_for_missing_job(monkeypatch) -> None:
    from app.config.http_errors import NotFoundError
    from app.controllers import taste as taste_controller

    repo = _FakeControllerRepo([], found=None)
    monkeypatch.setattr(taste_controller, "TasteJobRepository", lambda db: repo)

    with pytest.raises(NotFoundError):
        await taste_controller.get_refresh_job(
            "tj_missing",
            SimpleNamespace(db_session=object()),
            SimpleNamespace(user_id="u_1"),
        )


async def test_background_refresh_marks_failed_before_reraising(monkeypatch) -> None:
    from app.services.algorithm import taste_jobs

    events = []

    class FakeTasteJobRepository:
        def __init__(self, db):  # noqa: ARG002
            pass

        async def mark_running(self, job_id, user_id):
            events.append(("running", job_id, user_id))

        async def mark_done(self, job_id, user_id):
            events.append(("done", job_id, user_id))

        async def mark_failed(self, job_id, user_id, error):
            events.append(("failed", job_id, user_id, error))

    async def fail_recompute(self, user_id):  # noqa: ARG001
        raise RuntimeError("provider down")

    monkeypatch.setattr(taste_jobs, "TasteJobRepository", FakeTasteJobRepository)
    monkeypatch.setattr(taste_jobs.TasteService, "recompute_and_store", fail_recompute)

    with pytest.raises(RuntimeError, match="provider down"):
        await taste_jobs.refresh_taste_for_user(
            _FakeInternal(_FakeDb()),
            "u_1",
            "tj_fail",
        )

    assert events == [
        ("running", "tj_fail", "u_1"),
        ("failed", "tj_fail", "u_1", "provider down"),
    ]


def _unique_columns(model) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _load_algorithm_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "db/versions/2026_06_06_0000-4c2f6f9b8a1d_algorithm_artifacts.py"
    )
    spec = importlib.util.spec_from_file_location("algorithm_artifacts_migration", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compile_sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def _compile_params(stmt) -> dict:
    return stmt.compile(dialect=postgresql.dialect()).params


class _TasteJobDb:
    def __init__(self, jobs=None):
        self.jobs = list(jobs or [])
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.refreshed = []
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        sql = _compile_sql(stmt)
        params = _compile_params(stmt)
        jobs = self.jobs
        if "taste_jobs.id =" in sql:
            jobs = [job for job in jobs if job.id == params["id_1"]]
        if "taste_jobs.user_id =" in sql:
            jobs = [job for job in jobs if job.user_id == params["user_id_1"]]
        if "taste_jobs.state IN" in sql:
            jobs = [job for job in jobs if job.state in params["state_1"]]
        return _ScalarResult(jobs[0] if jobs else None)

    def add(self, item):
        self.added.append(item)
        if item not in self.jobs:
            self.jobs.append(item)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, item):
        self.refreshed.append(item)


class _InsertConflictDb:
    def __init__(self, active_job):
        self.active_job = active_job
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.refreshed = []
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1:
            return _ScalarResult(None)
        return _ScalarResult(self.active_job)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1
        if self.commits == 1:
            raise IntegrityError("insert taste job", {}, Exception("duplicate active job"))

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, item):
        self.refreshed.append(item)


class _RecordingMigrationOp:
    def __init__(self):
        self.tables = {}
        self.indexes = {}

    def f(self, name):
        return name

    def create_table(self, name, *items):
        self.tables[name] = items

    def create_index(self, name, table_name, columns, **kwargs):
        self.indexes[name] = SimpleNamespace(args=(table_name, columns), kwargs=kwargs)


class _FakeDb:
    async def rollback(self):
        pass


class _ScalarResult:
    def __init__(self, item):
        self.item = item

    def scalar_one_or_none(self):
        return self.item


class _FakeControllerRepo:
    def __init__(self, queued_results, *, found=None):
        self.queued_results = list(queued_results)
        self.found = found
        self.find_requests = []

    async def get_or_create_for_user(self, user_id):  # noqa: ARG002
        return self.queued_results.pop(0)

    async def find_for_user(self, job_id, user_id):
        self.find_requests.append((job_id, user_id))
        return self.found


class _RecordingBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append(SimpleNamespace(func=func, args=args, kwargs=kwargs))


class _FakeSessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, traceback):  # noqa: ANN001
        return None


class _FakeSessionmaker:
    def __init__(self, db):
        self.db = db

    def __call__(self):
        return _FakeSessionContext(self.db)


class _FakeInternal:
    def __init__(self, db):
        self.db_sessionmaker = _FakeSessionmaker(db)
        self.http_client = object()
        self.s3 = object()
        self.profile_provider = object()
