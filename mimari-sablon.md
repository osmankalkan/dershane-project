# Öğrenci Performans Analitik Platformu — Proje Şablonu & Mimari Referansı

> **Bu dosya projenin anayasasıdır.**
> Geliştirme süresince alınan her teknik karar bu belgede tanımlanan prensiplere uygun olmak zorundadır.
> Hiçbir şeyden sapılmaz. Bir şey değişecekse önce bu belge güncellenir.

---

## İçindekiler

1. [Mimari Prensipler](#1-mimari-prensipler)
2. [Teknoloji Yığını](#2-teknoloji-yığını)
3. [Genel Sistem Mimarisi](#3-genel-sistem-mimarisi)
4. [PDF Engine — Plugin Mimarisi](#4-pdf-engine--plugin-mimarisi)
5. [Veri Akışı (Ham → Normalize → Veritabanı)](#5-veri-akışı)
6. [Veritabanı Şeması](#6-veritabanı-şeması)
7. [Backend Katman Ayrımı](#7-backend-katman-ayrımı)
8. [Frontend Yapısı](#8-frontend-yapısı)
9. [Tam Klasör Ağacı](#9-tam-klasör-ağacı)
10. [Güvenlik Katmanı](#10-güvenlik-katmanı)
11. [Test Stratejisi](#11-test-stratejisi)
12. [Genişleme Noktaları](#12-genişleme-noktaları)
13. [Geliştirme Fazları](#13-geliştirme-fazları)
14. [Karar Kayıtları (ADR)](#14-karar-kayıtları-adr)

---

## 1. Mimari Prensipler

Bu prensipler projenin temel kurallarıdır. Teknik karar verirken her zaman bu listeye dönülür.

### 1.1 Temel 4 Kural

| # | Kural | Açıklama |
|---|---|---|
| P1 | **Modülerlik** | Her yayınevi / exam formatı kendi bağımsız modülünde yaşar. Biri değişince diğerleri etkilenmez. |
| P2 | **Ham veri asla silinmez** | Parser hata yapsa bile orijinal PDF ve çıkarılan ham veri saklanır, her zaman yeniden işlenebilir. |
| P3 | **Sessiz hata yok** | Şüpheli veya tutarsız veri hiçbir zaman otomatik kaydedilmez, her zaman insan onayına düşer. |
| P4 | **Katmanlar birbirine sızmaz** | PDF parsing mantığı DB koduna, DB kodu API koduna karışmaz. Katmanlar arası iletişim sadece tanımlı arayüzlerden geçer. |

### 1.2 Yazılım Tasarım Prensipleri

- **SOLID** prensiplerine uyulur; özellikle Tek Sorumluluk (S) ve Açık/Kapalı (O) ilkeleri.
- **Dependency Injection** kullanılır; servisler doğrudan bağımlılık oluşturmaz.
- **Repository Pattern** uygulanır; veritabanı erişimi servis katmanından izole edilir.
- **Fail-Fast** yaklaşımı benimsenir; hata erkenden yakalanır ve açıkça raporlanır.
- Her bir iş kuralı **servis katmanında** kodlanır, route ve model katmanlarına sızmaz.

### 1.3 Kodlama Kuralları

| Kural | Açıklama |
|---|---|
| **Dosya yolu işlemleri** | Kod boyunca tüm dosya/dizin yolu işlemlerinde `os.path` yerine **`pathlib.Path`** kullanılır. `str` tabanlı yol birleştirme (`"dir" + "/" + "file"`) kesinlikle yasaktır. |
| **Satır sonu (EOL)** | Tüm text dosyaları **LF** (`\n`) satır sonuyla saklanır. `.gitattributes` bu kuralı Git seviyesinde zorlar. Editör ayarlarında da LF seçilmelidir. |
| **String formatting** | f-string tercih edilir; `%` ve `.format()` yeni kodda kullanılmaz. |
| **Type hints** | Tüm fonksiyon imzalarında tip belirteci zorunludur (`-> None`, `str`, `Path` vb.). |
| **Import sırası** | `ruff` ile otomatik düzenlenir: stdlib → third-party → local. |

> **`pathlib` kullanım örneği:**
> ```python
> # ✅ Doğru
> from pathlib import Path
>
> upload_dir = Path(settings.UPLOAD_DIR)
> file_path  = upload_dir / raw_file_id / filename
> file_path.parent.mkdir(parents=True, exist_ok=True)
>
> # ❌ Yasak
> import os
> file_path = os.path.join(upload_dir, raw_file_id, filename)
> ```

---

## 2. Teknoloji Yığını

### 2.1 Backend

| Bileşen | Teknoloji | Versiyon | Gerekçe |
|---|---|---|---|
| Web Framework | **FastAPI** | >= 0.111 | Async destek, otomatik OpenAPI dokümantasyonu, Pydantic entegrasyonu |
| ORM | **SQLAlchemy** | >= 2.0 | Async destekli, güçlü migration ekosistemi |
| Migration | **Alembic** | >= 1.13 | SQLAlchemy ile entegre, versiyon kontrolü |
| Veritabanı | **PostgreSQL** | >= 16 | ACID garantisi, JSON sütun desteği, ölçeklenebilirlik |
| Validation | **Pydantic v2** | >= 2.7 | Tip güvenliği, performans |
| PDF İşleme | **pdfplumber** | >= 0.11 | Tablo çıkarma, metin konumlandırma |
| OCR (Fallback) | **pytesseract** | >= 0.3 | Taranmış PDF'ler için |
| Auth | **PyJWT + bcrypt** | — | JWT token yönetimi |
| Task Queue | **Celery + Redis** | — | Uzun süren PDF işlemleri için asenkron kuyruk |
| Container | **Docker + Compose** | — | Ortam tutarlılığı |

### 2.2 Frontend

| Bileşen | Teknoloji | Versiyon | Gerekçe |
|---|---|---|---|
| Framework | **React** | >= 18 | Bileşen bazlı, geniş ekosistem |
| Build Tool | **Vite** | >= 5 | Hızlı geliştirme ortamı |
| State Management | **Zustand** | >= 4 | Hafif, boilerplate az |
| HTTP Client | **Axios** | >= 1.6 | İstek interceptor desteği |
| Grafik | **Recharts** | >= 2.12 | React native, özelleştirilebilir |
| UI Components | **shadcn/ui** | — | Erişilebilir, headless |
| Stil | **Tailwind CSS** | >= 3 | Utility-first, tasarım tutarlılığı |
| Routing | **React Router** | >= 6 | Nested route desteği |

---

## 3. Genel Sistem Mimarisi

```
+-------------------------------------------------------------------------+
|                         FRONTEND (React + Vite)                         |
|                                                                         |
|   +--------------+  +--------------+  +---------------+  +-----------+  |
|   |  Dashboard   |  |  PDF Upload  |  | Öğrenci Analiz|  |  Onay     |  |
|   |  (Genel      |  |  (Sürükle    |  |  (Bireysel    |  |  Kuyruğu  |  |
|   |   Bakış)     |  |   ve Bırak)  |  |   Detay)      |  |  (Review) |  |
|   +--------------+  +--------------+  +---------------+  +-----------+  |
+------------------------------+------------------------------------------+
                               | HTTPS / REST API (JSON)
+------------------------------v------------------------------------------+
|                         BACKEND (FastAPI)                                |
|                                                                         |
|  +------------------+   +------------------+   +---------------------+ |
|  |   API Layer      |   |  Service Layer   |   |    PDF Engine       | |
|  |  (routes/)       +-->+  (services/)     +-->+  (pdf_engine/)      | |
|  |  Sadece HTTP     |   |  İş mantığı      |   |  Parser + Validator | |
|  +------------------+   +-------+----------+   +---------------------+ |
|                                 |                         |             |
|  +------------------+           |             +-----------v-----------+ |
|  |  Schemas Layer   |<----------+             |   Task Queue          | |
|  |  (Pydantic)      |           |             |   (Celery + Redis)    | |
|  +------------------+   +-------v----------+  +-----------------------+ |
|                          |  Repository      |                           |
|                          |  Layer           |                           |
|                          +-------+----------+                           |
+----------------------------------+--------------------------------------+
                                   | SQLAlchemy (async)
+----------------------------------v--------------------------------------+
|                        PostgreSQL Veritabanı                             |
|                                                                         |
|  institutions | students | exams | results | raw_files | review_queue   |
+-------------------------------------------------------------------------+
                                   |
                   +---------------+---------------+
                   |        Dosya Deposu           |
                   |  (Yerel FS veya S3-compat.)   |
                   |  /uploads/raw/<UUID>/file.pdf  |
                   +-------------------------------+
```

---

## 4. PDF Engine — Plugin Mimarisi

Bu kısım sistemin kalbidir. Tüm format karmaşıklığı burada yönetilir.

### 4.1 İşlem Akışı

```
                          PDF Yüklendi
                               |
                     +---------v----------+
                     |   Format Detector  |  <- "Bu hangi yayınevi?"
                     |   (detector.py)    |     Anahtar kelime + yapısal analiz
                     +---------+----------+
                               |
               +---------------+---------------+
               |               |               |
      +--------v------+ +------v-------+ +----v--------------+
      |  Parser: A    | |  Parser: B   | |  Parser: ???      |
      |  (Yayınevi A) | |  (Yayınevi B)| |  (Taninamadi)     |
      +--------+------+ +------+-------+ +----+---------------+
               |               |               |
               +-------+-------+               v
                       |           +------------------------+
                       v           |  FORMAT TANINAMADI     |
           +-----------+---------+ |  -> review_queue'ya    |
           |  Normalizer         | |     "UNKNOWN_FORMAT"   |
           |  (normalizer.py)    | |     ile düşer          |
           |  Ortak JSON'a çev.  | +------------------------+
           +-----------+---------+
                       |
           +-----------v---------+
           |  Validator          |  <- D + Y + B = Toplam Soru?
           |  (validator.py)     |     Öğrenci kodu eşleşiyor mu?
           +-----------+---------+     Tarih mantıklı mı?
                       |
          +------------+------------+
          v                         v
  +--------------+        +---------------------+
  |  GECERLI     |        |  SÜPHELI            |
  |  -> Database |        |  -> review_queue    |
  |    'e kayıt  |        |    (insan onayı)    |
  +--------------+        +---------------------+
```

### 4.2 Base Parser Sözleşmesi

Her parser `BasePDFParser` sınıfını implement etmek zorundadır:

```python
# pdf_engine/parsers/base_parser.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RawExtractionResult:
    """Her parser'ın döndüreceği standart ham veri yapısı."""
    parser_name: str
    raw_data: dict          # Format-spesifik ham çıktı
    confidence: float       # 0.0 - 1.0 arası güven skoru
    warnings: list[str]     # Şüpheli ama engelleyici olmayan durumlar
    errors: list[str]       # Engelleyici hatalar

@dataclass
class NormalizedExamData:
    """Tüm parser'ların üretmesi gereken standart çıktı."""
    exam_date: str          # ISO 8601 (YYYY-MM-DD)
    institution_name: str
    student_results: list[dict]   # Her öğrenci için standart yapı
    source_format: str      # "YAYINEVI_A_V1" gibi tanımlayıcı

class BasePDFParser(ABC):

    @abstractmethod
    def can_handle(self, pdf_path: str) -> bool:
        """Bu PDF bu parser'ın formatında mı? True/False döner."""
        pass

    @abstractmethod
    def extract(self, pdf_path: str) -> RawExtractionResult:
        """Ham veriyi PDF'ten çeker. Normalleştirme yapmaz."""
        pass

    @abstractmethod
    def normalize(self, raw: RawExtractionResult) -> NormalizedExamData:
        """Ham veriyi standart formata çevirir."""
        pass
```

### 4.3 PDF Engine Klasör Yapısı

```
pdf_engine/
├── __init__.py
├── detector.py              # Yüklenen PDF'in formatını tanır
├── engine.py                # Tüm süreci orkestre eden ana sınıf
├── normalizer.py            # Ortak normalizasyon yardımcıları
├── validator.py             # Tutarlılık kontrolü (D+Y+B, tarih, öğrenci kodu)
├── ocr_fallback.py          # Metin çıkmayan PDF'ler için pytesseract
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py       # Soyut temel sınıf (sözleşme)
│   ├── parser_yayinevi_a.py # İlk format implementasyonu
│   └── ...                  # Yeni format = yeni dosya, eski kodlara dokunulmaz
└── tests/
    ├── fixtures/            # Test için örnek PDF'ler
    ├── test_detector.py
    ├── test_validator.py
    └── test_parsers/
        └── test_yayinevi_a.py
```

**Kural:** Yeni bir yayınevi formatı geldiğinde tek yapılacak iş `parsers/` klasörüne yeni bir dosya eklemektir. Mevcut parser'lara **dokunulmaz**.

---

## 5. Veri Akışı

### 5.1 PDF Yükleme → Veritabanı

```
[1] PDF Yüklendi
     |  -> raw_files tablosuna kaydedilir (status: "PENDING")
     |  -> Fiziksel dosya /uploads/raw/<UUID>/ altına kopyalanır
     v
[2] Celery Task Tetiklendi (asenkron)
     |  -> PDF Engine devreye girer
     |  -> detector.py formatı belirler
     v
[3] Parser çalışır
     |  -> raw_extractions tablosuna kaydedilir (ham JSON)
     |  -> raw_files.status = "EXTRACTED"
     v
[4] Normalizer çalışır
     |  -> RawExtractionResult -> NormalizedExamData
     v
[5] Validator çalışır
     |
     +-- GECERLI  -> [6a] Normalize veriler DB'ye yazılır
     |                    (students, results tabloları)
     |                    raw_files.status = "PROCESSED"
     |
     +-- SÜPHELI  -> [6b] review_queue'ya eklenir
                          raw_files.status = "NEEDS_REVIEW"
                          Kullanıcıya bildirim
```

### 5.2 İnsan Onayı Akışı

```
review_queue (status: PENDING)
     |
     v  Rehber öğretmen inceleme ekranında
     |
     +-- ONAYLA -> Normalize veri DB'ye yazılır
     |              review_queue.status = "APPROVED"
     |
     +-- REDDET -> raw_files.status = "REJECTED"
                    review_queue.status = "REJECTED"
                    Neden? -> notes alanına kaydedilir
```

---

## 6. Veritabanı Şeması

### 6.1 Tablo Tanımları

```sql
-- Kurumlar
institutions
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  name            VARCHAR(255) NOT NULL
  slug            VARCHAR(100) UNIQUE NOT NULL  -- URL dostu tanımlayıcı
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

-- Sınıflar
classes
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  institution_id  UUID REFERENCES institutions(id) NOT NULL
  name            VARCHAR(50) NOT NULL  -- "7-A", "LGS-2025" gibi
  academic_year   VARCHAR(9) NOT NULL   -- "2024-2025"
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
  UNIQUE(institution_id, name, academic_year)

-- Öğrenciler
students
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  class_id        UUID REFERENCES classes(id) NOT NULL
  full_name       VARCHAR(255) NOT NULL
  student_code    VARCHAR(50)           -- Sınav kodunda kullanılan ID
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
  UNIQUE(class_id, student_code)

-- Ham Dosyalar (hiçbir zaman silinmez)
raw_files
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  institution_id  UUID REFERENCES institutions(id) NOT NULL
  file_path       TEXT NOT NULL UNIQUE  -- /uploads/raw/<UUID>/filename.pdf
  original_name   VARCHAR(255) NOT NULL
  file_hash       VARCHAR(64) NOT NULL  -- SHA-256, duplicate tespiti için
  status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                  -- PENDING | EXTRACTED | PROCESSED | NEEDS_REVIEW | REJECTED
  uploaded_by     UUID REFERENCES users(id) NOT NULL
  uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()

-- Ham Çıkarımlar (parser çıktısı, normalleştirilmemiş)
raw_extractions
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  raw_file_id     UUID REFERENCES raw_files(id) NOT NULL
  parser_used     VARCHAR(100) NOT NULL   -- "YAYINEVI_A_V1"
  detected_format VARCHAR(100)
  raw_json        JSONB NOT NULL          -- Parser'ın ham çıktısı
  confidence      NUMERIC(3,2)            -- 0.00 - 1.00
  warnings        TEXT[]                  -- Engelleyici olmayan uyarılar
  extracted_at    TIMESTAMPTZ NOT NULL DEFAULT now()

-- Sınavlar
exams
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  institution_id  UUID REFERENCES institutions(id) NOT NULL
  raw_file_id     UUID REFERENCES raw_files(id)
  name            VARCHAR(255) NOT NULL   -- "TYT Deneme 3"
  exam_date       DATE NOT NULL
  source_format   VARCHAR(100)            -- "YAYINEVI_A_V1"
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

-- Dersler
subjects
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  name            VARCHAR(100) NOT NULL UNIQUE  -- "Matematik", "Türkçe"
  short_code      VARCHAR(10) NOT NULL UNIQUE   -- "MAT", "TRK"

-- Konular
topics
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  subject_id      UUID REFERENCES subjects(id) NOT NULL
  name            VARCHAR(255) NOT NULL
  UNIQUE(subject_id, name)

-- Kazanımlar
learning_outcomes
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  topic_id        UUID REFERENCES topics(id) NOT NULL
  code            VARCHAR(50)                   -- Resmi müfredat kodu
  description     TEXT NOT NULL

-- Sonuçlar (Ana Veri Tablosu)
results
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  student_id      UUID REFERENCES students(id) NOT NULL
  exam_id         UUID REFERENCES exams(id) NOT NULL
  learning_outcome_id UUID REFERENCES learning_outcomes(id) NOT NULL
  correct         SMALLINT NOT NULL DEFAULT 0
  wrong           SMALLINT NOT NULL DEFAULT 0
  blank           SMALLINT NOT NULL DEFAULT 0
  total_questions SMALLINT NOT NULL
  measured        BOOLEAN NOT NULL DEFAULT true  -- FALSE = "ölçülmedi", soru yoktu
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
  UNIQUE(student_id, exam_id, learning_outcome_id)
  CONSTRAINT valid_counts CHECK (correct + wrong + blank = total_questions OR NOT measured)

-- İnsan Onay Kuyruğu
review_queue
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  raw_extraction_id UUID REFERENCES raw_extractions(id) NOT NULL
  reason          VARCHAR(100) NOT NULL  -- "VALIDATION_FAILED", "UNKNOWN_FORMAT", ...
  reason_detail   TEXT
  status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                  -- PENDING | APPROVED | REJECTED
  resolved_by     UUID REFERENCES users(id)
  resolved_at     TIMESTAMPTZ
  notes           TEXT                  -- Reddedilme sebebi veya onay notu
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

-- Kullanıcılar
users
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  institution_id  UUID REFERENCES institutions(id)
  email           VARCHAR(255) NOT NULL UNIQUE
  hashed_password TEXT NOT NULL
  role            VARCHAR(20) NOT NULL DEFAULT 'counselor'
                  -- admin | counselor | viewer
  is_active       BOOLEAN NOT NULL DEFAULT true
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

### 6.2 Kritik Tasarım Kararları

| Karar | Gerekçe |
|---|---|
| `measured BOOLEAN` alanı | "%0 aldı" ile "sınavda yoktu/ölçülmedi" farkını garanti altına alır |
| `raw_files` hiç silinmez | Parser hatalarında orijinal veriden geri dönüş imkânı |
| `raw_extractions.raw_json JSONB` | Format değişse bile ham veri okunabilir kalır |
| `file_hash (SHA-256)` | Aynı PDF'in iki kez yüklenmesini önler |
| Tüm ID'ler UUID | Tahmin edilemez, birden fazla kurumda ID çakışması olmaz |
| `UNIQUE(student, exam, learning_outcome)` | Aynı öğrenciye aynı kazanım için çift kayıt olamaz |

---

## 7. Backend Katman Ayrımı

### 7.1 Katman Sorumlulukları

```
+----------------------------------------------------------+
|  API Layer (api/)                                        |
|  * HTTP isteklerini karşılar                             |
|  * Request body'yi schema'ya çevirir                     |
|  * Response döner                                        |
|  * İş mantığı YOKTUR burada                             |
|  * Direkt DB sorgusu YASAKTIR                           |
+-------------------------+--------------------------------+
                          | çağırır
+-------------------------v--------------------------------+
|  Service Layer (services/)                              |
|  * Gerçek iş mantığı burada yaşar                       |
|  * Birden fazla repository'yi koordine eder             |
|  * Validasyon ve iş kuralları burada zorlanır           |
|  * Direkt DB sorgusu YASAKTIR                           |
+-------------------------+--------------------------------+
                          | çağırır
+-------------------------v--------------------------------+
|  Repository Layer (repositories/)                       |
|  * Sadece DB CRUD operasyonları                         |
|  * SQLAlchemy sorguları burada                          |
|  * İş mantığı YOKTUR burada                            |
+-------------------------+--------------------------------+
                          | kullanır
+-------------------------v--------------------------------+
|  Model Layer (models/)                                  |
|  * SQLAlchemy ORM modelleri                             |
|  * Tablo tanımları                                      |
+----------------------------------------------------------+
```

---

## 8. Frontend Yapısı

### 8.1 Sayfa ve Bileşen Hiyerarşisi

```
Frontend Sayfaları
|
+-- /dashboard           -> Genel bakış, son sınavlar, uyarılar
+-- /upload              -> PDF yükleme (drag & drop, durum takibi)
+-- /students            -> Öğrenci listesi + filtreleme
+-- /students/:id        -> Bireysel öğrenci analizi (zaman içi grafik)
+-- /exams               -> Sınav listesi
+-- /exams/:id           -> Sınav sonuçları (kurum geneli, konu kırılımı)
+-- /review              -> İnsan onay kuyruğu (rehber öğretmen)
+-- /settings            -> Kurum, sınıf, öğrenci yönetimi
```

### 8.2 Veri Akışı (Frontend)

```
Backend API
    |
    v
api/ (axios instance)       -> Tüm HTTP çağrıları tek yerden
    |
    v
hooks/ (React Query)        -> Cache + loading/error state otomatik
    |
    v
Zustand Store               -> Global state (auth, filters)
    |
    v
Components                  -> Sadece render, iş mantığı YOKTUR
```

---

## 9. Tam Klasör Ağacı

```
dershane-project/
|
+-- backend/
|   +-- app/
|   |   +-- __init__.py
|   |   +-- main.py                     # FastAPI app, middleware, router
|   |   |
|   |   +-- api/                        # HTTP katmanı
|   |   |   +-- __init__.py
|   |   |   +-- deps.py                 # Dependency injection (DB session, current user)
|   |   |   +-- v1/
|   |   |       +-- __init__.py
|   |   |       +-- auth.py
|   |   |       +-- students.py
|   |   |       +-- exams.py
|   |   |       +-- upload.py
|   |   |       +-- analytics.py
|   |   |       +-- review.py
|   |   |
|   |   +-- services/                   # İş mantığı katmanı
|   |   |   +-- __init__.py
|   |   |   +-- auth_service.py
|   |   |   +-- student_service.py
|   |   |   +-- exam_service.py
|   |   |   +-- upload_service.py       # PDF işleme orkestrasyonu
|   |   |   +-- analytics_service.py   # Analiz hesaplamaları
|   |   |   +-- review_service.py      # Onay kuyruğu yönetimi
|   |   |
|   |   +-- repositories/               # DB erişim katmanı
|   |   |   +-- __init__.py
|   |   |   +-- base_repository.py     # Ortak CRUD operasyonları
|   |   |   +-- student_repository.py
|   |   |   +-- exam_repository.py
|   |   |   +-- result_repository.py
|   |   |   +-- review_repository.py
|   |   |
|   |   +-- models/                     # SQLAlchemy ORM modelleri
|   |   |   +-- __init__.py
|   |   |   +-- base.py
|   |   |   +-- institution.py
|   |   |   +-- student.py
|   |   |   +-- exam.py
|   |   |   +-- result.py
|   |   |   +-- raw_file.py
|   |   |   +-- user.py
|   |   |
|   |   +-- schemas/                    # Pydantic v2 şemaları
|   |   |   +-- __init__.py
|   |   |   +-- student.py
|   |   |   +-- exam.py
|   |   |   +-- result.py
|   |   |   +-- upload.py
|   |   |   +-- analytics.py
|   |   |
|   |   +-- pdf_engine/                 # PDF işleme motoru
|   |   |   +-- __init__.py
|   |   |   +-- engine.py               # Ana orkestratör
|   |   |   +-- detector.py             # Format tanımlayıcı
|   |   |   +-- normalizer.py           # Ortak formata çevirici
|   |   |   +-- validator.py            # Tutarlılık kontrolü
|   |   |   +-- ocr_fallback.py         # OCR yedek
|   |   |   +-- parsers/
|   |   |       +-- __init__.py
|   |   |       +-- base_parser.py      # Soyut temel sınıf
|   |   |       +-- parser_yayinevi_a.py
|   |   |
|   |   +-- tasks/                      # Celery async görevler
|   |   |   +-- __init__.py
|   |   |   +-- pdf_tasks.py
|   |   |
|   |   +-- core/                       # Ortak altyapı
|   |       +-- __init__.py
|   |       +-- config.py               # Pydantic Settings (env'den okur)
|   |       +-- database.py             # DB bağlantısı, session factory
|   |       +-- security.py             # JWT, bcrypt
|   |       +-- exceptions.py           # Özel exception sınıfları
|   |
|   +-- migrations/                     # Alembic migration dosyaları
|   |   +-- env.py
|   |   +-- versions/
|   |
|   +-- tests/
|   |   +-- conftest.py
|   |   +-- test_api/
|   |   +-- test_services/
|   |   +-- test_repositories/
|   |   +-- test_pdf_engine/
|   |       +-- fixtures/               # Örnek PDF'ler
|   |       +-- test_detector.py
|   |       +-- test_validator.py
|   |       +-- test_parsers/
|   |
|   +-- .env.example
|   +-- requirements.txt
|   +-- requirements-dev.txt
|   +-- Dockerfile
|   +-- pyproject.toml
|
+-- frontend/
|   +-- src/
|   |   +-- main.jsx
|   |   +-- App.jsx
|   |   |
|   |   +-- pages/
|   |   |   +-- Dashboard.jsx
|   |   |   +-- UploadPage.jsx
|   |   |   +-- StudentsPage.jsx
|   |   |   +-- StudentDetailPage.jsx
|   |   |   +-- ExamsPage.jsx
|   |   |   +-- ExamDetailPage.jsx
|   |   |   +-- ReviewQueuePage.jsx
|   |   |   +-- SettingsPage.jsx
|   |   |
|   |   +-- components/
|   |   |   +-- layout/
|   |   |   |   +-- Sidebar.jsx
|   |   |   |   +-- Header.jsx
|   |   |   |   +-- PageWrapper.jsx
|   |   |   +-- charts/
|   |   |   |   +-- PerformanceLineChart.jsx
|   |   |   |   +-- SubjectRadarChart.jsx
|   |   |   |   +-- TopicBreakdownBar.jsx
|   |   |   +-- ui/                     # shadcn bileşenleri
|   |   |
|   |   +-- api/
|   |   |   +-- client.js               # Axios instance + interceptors
|   |   |   +-- students.js
|   |   |   +-- exams.js
|   |   |   +-- upload.js
|   |   |   +-- analytics.js
|   |   |
|   |   +-- hooks/
|   |   |   +-- useStudents.js
|   |   |   +-- useExamResults.js
|   |   |   +-- useAnalytics.js
|   |   |
|   |   +-- store/
|   |       +-- authStore.js
|   |       +-- filterStore.js
|   |
|   +-- public/
|   +-- index.html
|   +-- vite.config.js
|   +-- package.json
|   +-- Dockerfile
|
+-- docker-compose.yml
+-- docker-compose.dev.yml
+-- mimari-sablon.md         <- Bu dosya
```

---

## 10. Güvenlik Katmanı

| Katman | Mekanizma | Notlar |
|---|---|---|
| Frontend | JWT token (httpOnly cookie) | Token localStorage'a kaydedilmez |
| Backend (Auth) | JWT doğrulama middleware | Her protected endpoint'te çalışır |
| Backend (Authz) | Rol tabanlı erişim kontrolü (RBAC) — FastAPI Depends() | admin / counselor / viewer |
| Dosya Erişimi | UUID'li rastgele path, dosya adı sanitize | /uploads/raw/UUID/filename |
| Veritabanı | Parameterized queries (ORM) | SQL injection riski sıfır |
| Loglama | Öğrenci adı/kodu loglara düşmez | PII loglanmaz |
| Environment | .env dosyası Git'e push edilmez | .env.example template tutulur |

---

## 11. Test Stratejisi

### 11.1 Test Piramidi

```
           +-----------+
           |  E2E Tests |  <- Az, kritik akışlar (upload -> result)
          -+------------+-
        +------------------+
        |  Integration Tests|  <- API endpoint testleri
       -+------------------+-
     +------------------------+
     |      Unit Tests         |  <- Parser, validator, service testleri
     +------------------------+
```

### 11.2 Test Öncelik Sırası

1. **`validator.py`** — En kritik: veri doğruluğunu garantiler
2. **`parsers/`** — Her parser, örnek fixture PDF ile test edilir
3. **`services/`** — İş mantığı testleri
4. **`api/`** — Endpoint response testleri
5. **`repositories/`** — DB sorgu testleri (test DB ile)

### 11.3 Kurallar

- Her yeni parser eklendiğinde, o format için en az 1 fixture PDF ve test yazılır.
- `validator.py`'daki her kural için hem geçerli hem başarısız test case'i bulunur.
- Testler CI/CD pipeline'ında otomatik çalışır.

---

## 12. Genişleme Noktaları

| Genişleme İhtiyacı | Nasıl Karşılanıyor | Dokunulacak Kod |
|---|---|---|
| Yeni yayınevi / format | `parsers/` klasörüne yeni dosya eklenir | Sadece yeni dosya |
| Yeni kurum | `institutions` tablosuna satır eklenir | Sıfır kod değişikliği |
| Yeni ders / konu / kazanım | İlgili tablolara veri eklenir | Sıfır kod değişikliği |
| AI / ML entegrasyonu | `analytics_service.py`'a yeni metod | Mevcut metodlar bozulmaz |
| Yeni rapor türü | `services/`'e yeni servis, yeni route | Mevcut servisler etkilenmez |
| Farklı frontend (mobil vb.) | API aynı kalır, sadece yeni istemci | Backend değişmez |
| Büyük ölçek (1000+ öğrenci) | Celery task'lar async, DB index'leri hazır | Mimari aynı kalır |
| Multi-tenant (birden fazla kurum) | `institution_id` her tabloda mevcut | Sıfır şema değişikliği |

---

## 13. Geliştirme Fazları

### Faz 1 — Temel Altyapı

- [ ] PostgreSQL şema kurulumu (Alembic migration'larla)
- [ ] `core/config.py`, `core/database.py` kurulumu
- [ ] `models/` katmanı (tüm tablolar)
- [ ] `base_parser.py` arayüzü + `parser_yayinevi_a.py` (ilk format)
- [ ] `validator.py` + birim testleri
- [ ] Docker Compose (postgres + redis + backend)

### Faz 2 — Backend API

- [ ] Auth endpoints (register, login, token refresh)
- [ ] Upload endpoint + Celery task entegrasyonu
- [ ] Students CRUD endpoint'leri
- [ ] Exams endpoint'leri
- [ ] Review queue endpoint'leri

### Faz 3 — Temel Frontend

- [ ] Vite + React kurulumu
- [ ] Auth (login sayfası, token yönetimi)
- [ ] PDF upload ekranı (drag & drop, durum göstergesi)
- [ ] Öğrenci listesi

### Faz 4 — Analitik ve Dashboard

- [ ] `analytics_service.py` (ders bazlı performans, konu kırılımı)
- [ ] Dashboard sayfası (grafikler, özet kartlar)
- [ ] Bireysel öğrenci detay sayfası (zaman içi trend grafikleri)
- [ ] Sınav detay sayfası

### Faz 5 — Onay Kuyruğu ve İnsan Onayı

- [ ] `review_queue` ekranı (rehber öğretmen için)
- [ ] Onaylama / reddetme akışı
- [ ] Bildirim sistemi (e-posta veya uygulama içi)

### Faz 6 — İkinci Format + Deployment

- [ ] `parser_yayinevi_b.py` (ikinci yayınevi formatı)
- [ ] Dockerfile'lar tamamlandı, Nginx konfigürasyonu
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Production ortamı kurulumu

---

## 14. Karar Kayıtları (ADR)

> **ADR (Architecture Decision Record):** Önemli mimari kararlar burada tarihiyle birlikte kaydedilir. "Neden bu kararı aldık?" sorusu her zaman yanıtlanabilir olmalıdır.

---

### ADR-001: Tüm ID'ler UUID

**Tarih:** Proje başlangıcı
**Karar:** Auto-increment integer yerine UUID kullanılır.
**Gerekçe:** Multi-tenant yapıda ID çakışması riski sıfıra iner. Dışa açık API'lerde sıralı ID'ler güvenlik riski oluşturabilir.

---

### ADR-002: Celery ile Asenkron PDF İşleme

**Tarih:** Proje başlangıcı
**Karar:** PDF işleme HTTP request/response döngüsü dışında, Celery task olarak çalışır.
**Gerekçe:** PDF işleme 10-30 saniye sürebilir. Kullanıcı bu süre boyunca tarayıcıyı kapatabilir. Async kuyruğa alınırsa işlem güvenle tamamlanır.

---

### ADR-003: Ham Verinin Hiçbir Zaman Silinmemesi

**Tarih:** Proje başlangıcı
**Karar:** `raw_files` ve `raw_extractions` tabloları hiçbir zaman fiziksel olarak temizlenmez.
**Gerekçe:** Parser güncellenmesi durumunda eski veriler yeniden işlenebilir. Veri kaybı yaşanmadan hatadan geri dönüş mümkün olur.

---

### ADR-004: `measured` Alanının Zorunluluğu

**Tarih:** Proje başlangıcı
**Karar:** `results` tablosunda `measured BOOLEAN` alanı zorunludur.
**Gerekçe:** Bir öğrencinin bir kazanımda 0 doğru yapması ile o kazanımın sınavda ölçülmemesi (soru bulunmaması) arasındaki fark veri bütünlüğü açısından kritiktir. Bu farkı NULL ile değil, semantik `measured=false` ile ifade etmek gerekir.

---

*Bu belge projenin yaşayan anayasasıdır. Her büyük mimari karar buraya eklenir ve güncellenir.*
