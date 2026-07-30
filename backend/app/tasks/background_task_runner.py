"""
Faz 0 görev runner implementasyonu — FastAPI BackgroundTasks.

ADR-006: Faz 0'da Celery + Redis kurulmaz.
  Bu sınıf AbstractTaskRunner'ı FastAPI'nin yerleşik BackgroundTasks
  mekanizmasıyla uygular. Faz 1'de bu sınıf silinmez;
  yalnızca dependency injection noktasında CeleryTaskRunner ile değiştirilir.

Kullanım (endpoint içinde):
    from fastapi import BackgroundTasks, Depends
    from app.tasks.background_task_runner import BackgroundTaskRunner
    from app.tasks.pdf_tasks import process_pdf_file

    @router.post("/upload")
    def upload_pdf(
        file: UploadFile,
        background_tasks: BackgroundTasks,
    ):
        runner = BackgroundTaskRunner(background_tasks)
        runner.run(process_pdf_file, file_path=saved_path, raw_file_id=raw_id)
        return {"status": "queued"}

Faz 1 swap (tek değişiklik):
    runner = CeleryTaskRunner()  # BackgroundTaskRunner yerine
    runner.run(process_pdf_file, ...)  # imza aynı kalır
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks

from app.tasks.base_task import AbstractTaskRunner


class BackgroundTaskRunner(AbstractTaskRunner):
    """FastAPI BackgroundTasks ile AbstractTaskRunner implementasyonu.

    HTTP yanıtı döndükten hemen sonra, aynı process içinde çalışır.
    Redis veya worker process gerektirmez.

    Sınırlama:
      Uygulama yeniden başlatılırsa kuyruktaki görevler kaybolur.
      Tek kullanıcılı yerel senaryoda (Faz 0) bu kabul edilebilirdir.
    """

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        """
        Args:
            background_tasks: FastAPI'nin endpoint'e inject ettiği
                              BackgroundTasks örneği.
        """
        self._bg = background_tasks

    def run(
        self,
        func: Callable[..., Any],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Fonksiyonu FastAPI BackgroundTasks kuyruğuna ekler.

        HTTP yanıtı istemciye gönderildikten sonra çalışır.
        """
        self._bg.add_task(func, *args, **kwargs)
