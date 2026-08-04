"""
Manuel test scripti — TYT/LGS format parser'larını doğrular.

Kullanım:
    python test_parser_manual.py [pdf_yolu]

Varsayılan PDF yolu: sample_pdfs/tyt_örnek.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Proje kök dizinini Python path'e ekle ─────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.resolve()
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


def main() -> None:
    pdf_path_str = sys.argv[1] if len(sys.argv) > 1 else "sample_pdfs/tyt_örnek.pdf"
    pdf_path = Path(pdf_path_str)

    from app.pdf_engine.factory import ParserFactory

    print(f"Test ediliyor: {pdf_path}")

    try:
        parser = ParserFactory.create_parser(pdf_path)
        print(f"Kullanılan Parser: {parser.__class__.__name__}")

        parser.parse()
        students = parser.extract_student_info()
        topics = parser.extract_topics()
        results = parser.extract_results()

        print(f"Çıkarılan öğrenci sayısı: {len(students)}")
        print(f"Çıkarılan konu/kazanım sayısı: {len(topics)}")
        print(f"Çıkarılan sonuç nesnesi sayısı: {len(results)}")

        output_path = Path("output_sample.json")
        output_data = {"students": students, "topics": topics, "results": results}
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"JSON Çıktısı kaydedildi: {output_path.resolve()}")
    except Exception as e:
        print(f"Hata oluştu: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
