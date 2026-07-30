"""
Result modeli — projenin ana veri tablosu.

Tablo:
  - results : Bir öğrencinin, bir sınavda, bir kazanım için aldığı sonuç.

─────────────────────────────────────────────────────────────────────────────
KRITIK: measured alanı (ADR-004)
─────────────────────────────────────────────────────────────────────────────
`measured = True`  → Bu kazanım sınavda ölçüldü; correct/wrong/blank geçerli.
`measured = False` → Bu kazanım sınavda ölçülmedi (soru yoktu).
                     correct/wrong/blank sıfır olabilir ama bu "%0 başarı"
                     anlamına GELMEZ. Analizlerde bu satırlar hariç tutulur.

NULL kullanmak yerine semantik Boolean tercih edildi:
  - "soru yoktu" ile "0 doğru yaptı" farkı veri tabanı seviyesinde garanti altında.
  - CHECK kısıtı: measured=True iken D+Y+B = total_questions zorunlu.

─────────────────────────────────────────────────────────────────────────────
UNIQUE kısıtı:
  (student_id, exam_id, learning_outcome_id) — çift kayıt olamaz.
─────────────────────────────────────────────────────────────────────────────
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Result(UUIDMixin, TimestampMixin, Base):
    """results tablosu — ana analitik veri kaynağı."""

    __tablename__ = "results"

    __table_args__ = (
        # Bir öğrencinin aynı sınavda aynı kazanım için iki kaydı olamaz.
        UniqueConstraint(
            "student_id", "exam_id", "learning_outcome_id",
            name="uq_result_student_exam_outcome",
        ),
        # measured=True ise D+Y+B toplamı total_questions'a eşit olmak zorunda.
        # measured=False ise kısıt uygulanmaz (kazanım ölçülmedi).
        CheckConstraint(
            "(correct + wrong + blank = total_questions) OR (NOT measured)",
            name="ck_result_counts_match_total",
        ),
        # Sayı alanları negatif olamaz.
        CheckConstraint("correct >= 0", name="ck_result_correct_nonneg"),
        CheckConstraint("wrong >= 0", name="ck_result_wrong_nonneg"),
        CheckConstraint("blank >= 0", name="ck_result_blank_nonneg"),
        CheckConstraint("total_questions > 0", name="ck_result_total_positive"),
    )

    # ── Dış anahtarlar ────────────────────────────────────────────────────────
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("exams.id", ondelete="RESTRICT"),
        nullable=False,
    )
    learning_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("learning_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Soru sayıları ─────────────────────────────────────────────────────────
    correct: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    wrong: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    blank: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # ── KRİTİK ALAN ───────────────────────────────────────────────────────────
    measured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        # True  → Kazanım bu sınavda ölçüldü; sayılar anlamlı.
        # False → Kazanım bu sınavda ölçülmedi; sayılar 0 olsa da
        #          "%0 başarı" DEĞİL, "veri yok" anlamına gelir.
        #          Analiz katmanı measured=False satırları hariç tutar.
    )

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    student: Mapped["Student"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="results"
    )
    exam: Mapped["Exam"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="results"
    )
    learning_outcome: Mapped["LearningOutcome"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="results"
    )

    # ── Yardımcı özellikler ───────────────────────────────────────────────────
    @property
    def net(self) -> float:
        """Net puan (YGS/LGS formülü: 1 doğru - 0.25 yanlış).

        measured=False ise net hesaplanamaz; None döner.
        """
        if not self.measured:
            return None  # type: ignore[return-value]
        return self.correct - (self.wrong * 0.25)

    @property
    def success_rate(self) -> float | None:
        """Başarı yüzdesi (0–100).

        measured=False veya total_questions=0 ise None döner.
        """
        if not self.measured or self.total_questions == 0:
            return None
        return round(self.correct / self.total_questions * 100, 2)

    def __repr__(self) -> str:
        return (
            f"<Result student={self.student_id} exam={self.exam_id} "
            f"correct={self.correct} measured={self.measured}>"
        )
