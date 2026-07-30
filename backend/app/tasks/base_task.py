"""
Asenkron görev kuyruğu soyutlama katmanı.

Bu modül, görev yürütme altyapısını iş mantığından ayırır (ADR-006, P4):

  Faz 0: BackgroundTaskRunner  → FastAPI BackgroundTasks (kurulum yok)
  Faz 1: CeleryTaskRunner      → Celery + Redis (swap = tek satır config)

Swap işlemi (Faz 1 geçişi):
  app/main.py veya deps.py içinde:
    # Faz 0:
    runner = BackgroundTaskRunner(background_tasks)
    # Faz 1:
    runner = CeleryTaskRunner()   ← aynı arayüz, farklı implementasyon

Servis ve endpoint kodları AbstractTaskRunner tipine bağlıdır;
hangi implementasyonun kullanıldığını bilmezler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class AbstractTaskRunner(ABC):
    """Tüm görev runner'larının uygulaması gereken soyut arayüz.

    Arayüz tek kasıtlı olarak basit tutulmuştur:
    Faz 0 → Faz 1 geçişini sürtünmesiz yapmak için imza değişmez.
    """

    @abstractmethod
    def run(
        self,
        func: Callable[..., Any],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Verilen fonksiyonu arka planda çalıştırır.

        Çağrı non-blocking olmalıdır: fonksiyonu kuyruğa alır veya
        arka planda başlatır; tamamlanmasını beklemez.

        Args:
            func:   Arka planda çalıştırılacak callable.
                    Serileştirilebilir olmalı (Celery için).
            *args:  Pozisyonel argümanlar.
            **kwargs: Anahtar kelime argümanları.

        Returns:
            None — görev ID'si veya future dönmez (basit arayüz).
            Durum takibi ileride ayrı bir `status()` metoduyla eklenebilir.

        Raises:
            TaskSubmissionError: Görev kuyruğa eklenemezse (örn. Redis bağlantı hatası).
        """
        ...
