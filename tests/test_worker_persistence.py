import os
from sqlalchemy import create_engine
from services.api import database as db_mod
from services.api import db_utils
from services.playwright_worker.tasks import process_request_task


def setup_module(module):
    # Rebind engine to SQLite for test isolation (no external postgres dependency)
    test_url = "sqlite:///./test_worker.db"
    if os.path.exists("test_worker.db"):
        os.remove("test_worker.db")
    engine = create_engine(test_url, connect_args={"check_same_thread": False})
    db_mod.engine.dispose()
    db_mod.engine = engine  # type: ignore[attr-defined]
    db_mod.SessionLocal.configure(bind=engine)  # type: ignore[attr-defined]
    db_mod.Base.metadata.create_all(bind=engine)


def teardown_module(module):  # pragma: no cover - cleanup best effort
    try:
        db_mod.Base.metadata.drop_all(bind=db_mod.engine)
    except Exception:
        pass


def test_process_request_task_persists_sources(monkeypatch):
    os.environ['PLAYWRIGHT_SKIP'] = '1'

    # Create initial task row
    db = db_mod.SessionLocal()
    db_utils.create_scraping_task(db, task_id='t1', url='https://example.com/jobs', user_prompt='хочу линки работ отсюда')
    db.close()

    # Monkeypatch LLM to deterministic outputs
    class DummyLLM:
        def chat(self, messages, **kwargs):  # noqa: D401
            # Return minimal valid JSON for regex generation / intent phases
            content = messages[-1]['content']
            if 'Produce JSON with keys' in content:
                return '{"regex": "(Python Developer)", "flags": "i", "extraction_mode": "findall", "explanation": "", "confidence": 0.9}'
            if 'REFINE' in content:
                return '{"regex": "(Python Developer)", "flags": "i", "extraction_mode": "findall", "explanation": "", "confidence": 0.9}'
            # Intent extraction path
            return '{"target": "job links", "original_input": "хочу линки работ отсюда", "keywords": ["job", "links"], "constraints": [], "output_shape": "list", "confidence": 0.8}'

    monkeypatch.setattr('shared.llm_client.LLMClient.from_env', lambda: DummyLLM())

    # Execute pipeline
    result = process_request_task('t1', 'https://example.com/jobs', 'хочу линки работ отсюда')
    assert result['task_id'] == 't1'

    # Validate persistence
    db2 = db_mod.SessionLocal()
    stored = db_utils.get_scraping_task(db2, 't1')
    assert stored is not None
    assert getattr(stored, 'page_content') is not None and len(getattr(stored, 'page_content')) > 0
    # network_requests stored (even if empty list from PLAYWRIGHT_SKIP path)
    assert getattr(stored, 'network_requests') is not None
    # intent fields should be persisted
    assert getattr(stored, 'intent_target') is not None
    assert getattr(stored, 'intent_keywords') is not None
    db2.close()
