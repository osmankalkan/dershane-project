"""
Mimari Sınır Testleri — Spaghetti Code Önleme Kalkanı

Bu testler, katmanlar arası yasa dışı import'ları otomatik olarak yakalar.
Her commit öncesinde pre-commit hook'u tarafından çalıştırılır.
Bir ihlal tespit edilirse commit engellenir ve ihlal detaylı gösterilir.

─────────────────────────────────────────────────────────────────────────────
İzin Verilen Katman İletişim Kuralları:
─────────────────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────┐
  │  API (api/)          → services/, schemas/, core/   │
  │                         repositories/ YASAK         │
  │                         models/ YASAK               │
  ├─────────────────────────────────────────────────────┤
  │  Services (services/)→ repositories/, schemas/,     │
  │                         models/, core/              │
  │                         api/ YASAK                  │
  ├─────────────────────────────────────────────────────┤
  │  Repositories        → models/, core/               │
  │  (repositories/)        services/ YASAK             │
  │                         api/ YASAK                  │
  │                         schemas/ YASAK              │
  ├─────────────────────────────────────────────────────┤
  │  Models (models/)    → base.py (kendi içi)          │
  │                         repositories/ YASAK         │
  │                         services/ YASAK             │
  │                         api/ YASAK                  │
  │                         schemas/ YASAK              │
  ├─────────────────────────────────────────────────────┤
  │  Schemas (schemas/)  → models/, core/               │
  │                         repositories/ YASAK         │
  │                         services/ YASAK             │
  │                         api/ YASAK                  │
  ├─────────────────────────────────────────────────────┤
  │  PDF Engine          → models/, core/               │
  │  (pdf_engine/)          api/ YASAK                  │
  │                         services/ YASAK             │
  │                         repositories/ YASAK         │
  ├─────────────────────────────────────────────────────┤
  │  Tasks (tasks/)      → services/, core/             │
  │                         api/ YASAK                  │
  │                         repositories/ YASAK (svc üzerinden) │
  └─────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────────────
Test başarısız olursa ne yapmalısın?
─────────────────────────────────────────────────────────────────────────────
  1. Hangi dosyanın ne import ettiğini oku.
  2. İlgili katman kuralına bak (yukarıdaki tablo).
  3. Import'u izin verilen katman üzerinden (genellikle servis) yeniden yaz.
  4. Kural gerçekten yanlışsa → mimari-sablon.md güncellenmeli ve bu test
     güncellenmeli. Kodu yamayıp testi geçiştirme.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _collect_imports(file_path: Path) -> list[str]:
    """Bir Python dosyasındaki tüm 'app.*' import'larını döndürür."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("app."):
                imports.append(module)
    return imports


def _files_in_layer(layer: str) -> list[Path]:
    """Verilen katman klasöründeki tüm .py dosyalarını döndürür."""
    layer_dir = APP_ROOT / layer
    if not layer_dir.exists():
        return []
    return list(layer_dir.rglob("*.py"))


def _check_layer(
    layer: str,
    forbidden_prefixes: list[str],
) -> list[str]:
    """
    Katmandaki her dosyayı tarar; yasaklı prefix'e sahip import varsa
    ihlali insan-okunabilir string olarak toplar ve döndürür.
    """
    violations: list[str] = []
    for py_file in _files_in_layer(layer):
        relative = py_file.relative_to(APP_ROOT.parent)
        for imp in _collect_imports(py_file):
            for forbidden in forbidden_prefixes:
                if imp.startswith(forbidden):
                    violations.append(
                        f"  IHLAL: {relative}\n         '{imp}' import edilmiş\n         → '{forbidden}*' bu katmanda yasak"
                    )
    return violations


# ── Test fonksiyonları ────────────────────────────────────────────────────────


class TestApiLayerBoundaries:
    """api/ katmanı: repositories ve models'e doğrudan erişemez."""

    def test_api_does_not_import_repositories(self) -> None:
        """API, repository'lere servis katmanını atlayarak ulaşamaz.

        Neden: Servis bypass edilirse iş kuralları uygulanmaz,
        veritabanı tutarsızlığı yaşanabilir.
        """
        violations = _check_layer("api", ["app.repositories"])
        assert not violations, (
            "\n\nAPI katmanı doğrudan repository import ediyor!\n"
            "Düzeltme: Repository'yi bir servis aracılığıyla kullan.\n\n" + "\n".join(violations)
        )

    def test_api_does_not_import_models_directly(self) -> None:
        """API, SQLAlchemy modellerine doğrudan erişemez; schemas kullanır.

        Neden: Model nesneleri DB oturumuna bağlıdır; API katmanına
        sızarsa oturum yönetimi karmaşıklaşır ve circular import riski artar.
        """
        violations = _check_layer("api", ["app.models"])
        assert not violations, (
            "\n\nAPI katmanı doğrudan model import ediyor!\nDüzeltme: Pydantic schema (schemas/) kullan.\n\n" + "\n".join(violations)
        )


class TestServiceLayerBoundaries:
    """services/ katmanı: api katmanını import edemez."""

    def test_services_do_not_import_api(self) -> None:
        """Servisler API katmanına bağımlı olamaz (circular import + katman kirliliği).

        Neden: Servis katmanı iş mantığını içerir; HTTP konseptlerine
        (Request, Response) bağımlı olmak servis testini zorlaştırır.
        """
        violations = _check_layer("services", ["app.api"])
        assert not violations, (
            "\n\nService katmanı API katmanını import ediyor!\n"
            "Bu circular dependency ve katman kirliliği yaratır.\n\n" + "\n".join(violations)
        )


class TestRepositoryLayerBoundaries:
    """repositories/ katmanı: sadece models/ ve core/ kullanabilir."""

    def test_repositories_do_not_import_services(self) -> None:
        """Repository, servisi çağıramaz — bu tersine bağımlılıktır.

        Neden: Repository → Service → Repository döngüsü circular import,
        sonsuz özyineleme ve test edilemez kod üretir.
        """
        violations = _check_layer("repositories", ["app.services"])
        assert not violations, (
            "\n\nRepository katmanı service import ediyor!\n"
            "Bu tersine bağımlılıktır; iş kuralı repository'ye gömülüyor.\n\n" + "\n".join(violations)
        )

    def test_repositories_do_not_import_api(self) -> None:
        """Repository, API katmanını hiçbir şekilde import edemez."""
        violations = _check_layer("repositories", ["app.api"])
        assert not violations, "\n\nRepository katmanı API import ediyor!\n\n" + "\n".join(violations)

    def test_repositories_do_not_import_schemas(self) -> None:
        """Repository, Pydantic schema'larına bağımlı olamaz.

        Neden: Repository'nin tek sorumluluğu DB CRUD'dur.
        Validation veya serialization bilgisi gerektirmez.
        """
        violations = _check_layer("repositories", ["app.schemas"])
        assert not violations, (
            "\n\nRepository katmanı schemas import ediyor!\nValidation servis katmanının sorumluluğundadır.\n\n" + "\n".join(violations)
        )


class TestModelLayerBoundaries:
    """models/ katmanı: sadece kendi içini import edebilir."""

    def test_models_do_not_import_repositories(self) -> None:
        """Model, repository'yi asla import edemez."""
        violations = _check_layer("models", ["app.repositories"])
        assert not violations, "\n\nModel katmanı repository import ediyor!\nModel sadece veri yapısını tanımlar.\n\n" + "\n".join(
            violations
        )

    def test_models_do_not_import_services(self) -> None:
        """Model, servisi asla import edemez."""
        violations = _check_layer("models", ["app.services"])
        assert not violations, "\n\nModel katmanı service import ediyor!\nİş mantığı modele gömülemez.\n\n" + "\n".join(violations)

    def test_models_do_not_import_api(self) -> None:
        violations = _check_layer("models", ["app.api"])
        assert not violations, "\n\nModel katmanı API import ediyor!\n\n" + "\n".join(violations)

    def test_models_do_not_import_schemas(self) -> None:
        violations = _check_layer("models", ["app.schemas"])
        assert not violations, "\n\nModel katmanı schemas import ediyor!\nModel ↔ Schema ayrımı bozulmamalıdır.\n\n" + "\n".join(
            violations
        )


class TestSchemaLayerBoundaries:
    """schemas/ katmanı: repositories, services, api import edemez."""

    def test_schemas_do_not_import_repositories(self) -> None:
        violations = _check_layer("schemas", ["app.repositories"])
        assert not violations, "\n\nSchema katmanı repository import ediyor!\n\n" + "\n".join(violations)

    def test_schemas_do_not_import_services(self) -> None:
        violations = _check_layer("schemas", ["app.services"])
        assert not violations, "\n\nSchema katmanı service import ediyor!\n\n" + "\n".join(violations)

    def test_schemas_do_not_import_api(self) -> None:
        violations = _check_layer("schemas", ["app.api"])
        assert not violations, "\n\nSchema katmanı API import ediyor!\n\n" + "\n".join(violations)


class TestPdfEngineLayerBoundaries:
    """pdf_engine/ katmanı: api, services, repositories'e erişemez."""

    def test_pdf_engine_does_not_import_api(self) -> None:
        """PDF engine, HTTP katmanını bilmez.

        Neden: PDF işleme saf bir iş mantığı modülüdür.
        HTTP konseptlerine bağımlı olursa servis dışında test edilemez.
        """
        violations = _check_layer("pdf_engine", ["app.api"])
        assert not violations, "\n\nPDF engine katmanı API import ediyor!\n\n" + "\n".join(violations)

    def test_pdf_engine_does_not_import_services(self) -> None:
        violations = _check_layer("pdf_engine", ["app.services"])
        assert not violations, (
            "\n\nPDF engine katmanı service import ediyor!\n"
            "PDF engine sadece ayrıştırma (parsing) yapar; iş kuralı uygulamaz.\n\n" + "\n".join(violations)
        )

    def test_pdf_engine_does_not_import_repositories(self) -> None:
        violations = _check_layer("pdf_engine", ["app.repositories"])
        assert not violations, (
            "\n\nPDF engine katmanı repository import ediyor!\n"
            "DB yazımı servis katmanının sorumluluğundadır.\n\n" + "\n".join(violations)
        )


class TestTaskLayerBoundaries:
    """tasks/ katmanı: api ve repositories'e doğrudan erişemez."""

    def test_tasks_do_not_import_api(self) -> None:
        """Task'lar HTTP katmanını import edemez."""
        violations = _check_layer("tasks", ["app.api"])
        assert not violations, "\n\nTask katmanı API import ediyor!\n\n" + "\n".join(violations)

    def test_tasks_do_not_import_repositories_directly(self) -> None:
        """Task'lar repository'lere servis üzerinden erişir.

        Neden: Task'ın doğrudan repository kullanması iş mantığını
        task dosyasına gömer ve test edilemez kod üretir.
        """
        violations = _check_layer("tasks", ["app.repositories"])
        assert not violations, (
            "\n\nTask katmanı doğrudan repository import ediyor!\n"
            "Düzeltme: Bir servis inject et, servisi çağır.\n\n" + "\n".join(violations)
        )
