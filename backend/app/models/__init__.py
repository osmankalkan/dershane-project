"""
SQLAlchemy model paketi.

Burası tek import noktasıdır. Alembic ve diğer modüller
modelleri doğrudan dosyalardan değil, buradan içe aktarır:

    from app.models import Base, Institution, Student, Result ...

Import sırası bağımlılık zincirini takip eder:
  Base → Institution/User → Class → Student → Exam → Result → RawFile → ReviewQueue
"""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.exam import Exam, LearningOutcome, Subject, Topic
from app.models.institution import Class, Institution
from app.models.raw_file import RawExtraction, RawFile, ReviewQueue
from app.models.result import Result
from app.models.student import Student
from app.models.user import User

__all__ = [
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # Kurum hiyerarşisi
    "Institution",
    "Class",
    # Kullanıcılar
    "User",
    # Öğrenciler
    "Student",
    # Sınav hiyerarşisi
    "Subject",
    "Topic",
    "LearningOutcome",
    "Exam",
    # Ana veri tablosu
    "Result",
    # Ham veri katmanı (asla silinmez — ADR-003)
    "RawFile",
    "RawExtraction",
    "ReviewQueue",
]
