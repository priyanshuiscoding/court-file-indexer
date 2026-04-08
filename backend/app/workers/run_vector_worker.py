import os

from app.workers.pipeline_worker import PipelineWorker


if __name__ == "__main__":
    os.environ.setdefault("WORKER_STAGE", "vectorize_document")
    PipelineWorker().run_forever()
