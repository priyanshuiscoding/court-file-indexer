from app.tasks.celery_app import celery_app


@celery_app.task(name="ops.ping")
def ping() -> dict:
    return {"ok": True}
