"""
LGS (Liselere Geçiş Sistemi) / Ortaokul formatı PDF parser'ı.

Desteklenen format özellikleri:
  - Tek PDF'te art arda birden fazla öğrenci sayfası
  - Her sayfa bir öğrenci bloğu; 'SINAV SONUÇ BELGESİ' başlığıyla başlar
  - LGS branşları (Türkçe, İnkılap Tarihi, Din Kültürü, Yabancı Dil, Matematik, Fen)
  - Toplam 90 soru
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from app.pdf_engine.parsers.base_parser import BasePDFParser
from app.pdf_engine.parsers.parser_tyt_format import (
    _RIGHT_COLUMN_X_THRESHOLD,
    _SINAV_BELGESI_MARKER,
    _group_words_into_rows,
    _row_to_text,
    _safe_float,
    _safe_int,
    _should_skip_line,
)

# ── Sabitler ──────────────────────────────────────────────────────────────────

PARSER_NAME = "LGS_FORMAT_V1"

# Özet tablodaki ders satırlarını tanımak için LGS subject prefix'leri
_SUBJECT_PREFIXES = (
    "Türkçe.08",
    "Türkçe",
    "Matematik.08",
    "Matematik",
    "Fen Bilgisi.08",
    "Fen Bilimleri",
    "Fen Bilgisi",
    "İnkılap Tarihi.08",
    "T.C. İnkılap Tarihi ve Atatürkçülük",
    "T.C. İnkılap Tarihi",
    "İnkılap Tarihi",
    "Sosyal Bilgiler.05",
    "Sosyal Bilgiler.06",
    "Sosyal Bilgiler.07",
    "Sosyal Bilgiler",
    "İngilizce.08",
    "Yabancı Dil",
    "İngilizce",
    "Din Kültürü.08",
    "Din Kültürü ve Ahlak Bilgisi",
    "Din Kültürü",
    "LGS Toplam",
    "Toplam:",
)


class ParserLGSFormat(BasePDFParser):
    parser_name: str = PARSER_NAME

    def can_handle(self, pdf_path: Path) -> bool:
        """LGS denemesi mi?"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return False
                first_page_text = pdf.pages[0].extract_text() or ""
                return _SINAV_BELGESI_MARKER in first_page_text and any(k in first_page_text for k in ["LGS", "8.SINIF", "MADALYON"])
        except Exception:
            return False

    def extract(self, pdf_path: Path) -> dict[str, Any]:
        warnings: list[str] = []
        errors: list[str] = []
        raw_students: list[dict[str, Any]] = []
        raw_exam_info: dict[str, Any] = {}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    try:
                        student_raw, exam_info, page_warnings = self._extract_student_page(page, page_num)
                        warnings.extend(page_warnings)
                        if student_raw:
                            raw_students.append(student_raw)
                        if not raw_exam_info and exam_info:
                            raw_exam_info = exam_info
                    except Exception as exc:
                        msg = f"Sayfa {page_num}/{total_pages} işlenirken hata: {exc}"
                        errors.append(msg)
                        warnings.append(msg)
        except Exception as exc:
            raise RuntimeError(f"PDF dosyası açılamadı: {pdf_path} — {exc}") from exc

        return {
            "raw_students": raw_students,
            "raw_exam_info": raw_exam_info,
            "warnings": warnings,
            "errors": errors,
        }

    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        warnings: list[str] = list(raw_data.get("warnings", []))
        raw_students: list[dict[str, Any]] = raw_data.get("raw_students", [])
        raw_exam: dict[str, Any] = raw_data.get("raw_exam_info", {})

        if not raw_students:
            raise ValueError("Normalleştirme başarısız: raw_students listesi boş.")

        normalized_students: list[dict[str, Any]] = []

        for raw_s in raw_students:
            try:
                normalized_s = self._normalize_student(raw_s)
                normalized_students.append(normalized_s)
            except Exception as exc:
                name = raw_s.get("full_name", "?")
                warnings.append(f"Öğrenci '{name}' normalleştirilemedi: {exc}")

        return {
            "exam_date": raw_exam.get("exam_date", ""),
            "institution_name": raw_exam.get("institution_name", ""),
            "source_format": PARSER_NAME,
            "student_results": normalized_students,
            "warnings": warnings,
        }

    def _extract_student_page(self, page: Any, page_num: int) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        warnings: list[str] = []
        words = page.extract_words(use_text_flow=False)
        if not words:
            warnings.append(f"Sayfa {page_num}: kelime bulunamadı, atlandı.")
            return {}, {}, warnings

        left_words = [w for w in words if w["x0"] < _RIGHT_COLUMN_X_THRESHOLD]
        right_words = [w for w in words if w["x0"] >= _RIGHT_COLUMN_X_THRESHOLD]

        left_rows = _group_words_into_rows(left_words)
        right_rows = _group_words_into_rows(right_words)

        exam_info = self._parse_exam_info(left_rows)
        student_meta = self._parse_student_meta(left_rows)
        summary_subjects = self._parse_summary_table(left_rows, warnings)
        analysis_subjects = self._parse_analysis_section(right_rows, warnings)

        student_raw: dict[str, Any] = {
            **student_meta,
            "summary_subjects": summary_subjects,
            "analysis_subjects": analysis_subjects,
            "page_num": page_num,
        }

        return student_raw, exam_info, warnings

    def _parse_exam_info(self, rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
        exam_name = ""
        institution_name = ""
        for row in rows[:8]:
            text = _row_to_text(row)
            # Find exact Exam Name like "8.SINIF 17.DENEME (PALME SİLVER 6)"
            # Usually after Sınav Adı
            if "Sınav Adı" in text:
                match = re.search(r"Sınav Adı\s+(.*?)\s+(Alan|Numara|Şube)", text)
                if match:
                    exam_name = match.group(1).strip()
            elif "KURUMSAL DENEME" in text:
                match = re.search(r"(KURUMSAL DENEME.*?)\s+(Alan|Numara)", text)
                if match:
                    exam_name = match.group(1).strip()

            if "Geldiği Okul" in text or "Okul" in text:
                if "/" in text and "SINAV" in text.upper():
                    institution_name = text.strip()
                else:
                    match = re.search(r"Okul\s+(.*?)(?:Geldiği Okul|$)", text)
                    if match:
                        institution_name = match.group(1).strip()

        return {
            "exam_name": exam_name,
            "institution_name": institution_name,
            "exam_date": "",
        }

    def _parse_student_meta(self, rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
        full_name = ""
        student_code = ""
        student_class = ""
        score = None

        for row in rows[:20]:
            text = _row_to_text(row)

            # Öğrenci Adı ve Numara tespiti
            if "Öğrenci" in text and not full_name:
                match = re.search(r"Öğrenci\s+(?:Adı|Ad)?\s*:?\s*(.*?)\s+(?:Numara|No)\s*:?\s*(\d+)", text, re.IGNORECASE)
                if match:
                    full_name = match.group(1).strip()
                    student_code = match.group(2).strip()
                else:
                    match_name = re.search(r"Öğrenci\s+(?:Adı|Ad)?\s*:?\s*([^0-9]+)", text, re.IGNORECASE)
                    if match_name:
                        name_candidate = match_name.group(1).split("Numara")[0].split("Sınıf")[0].split("Şube")[0].strip()
                        if len(name_candidate) > 2:
                            full_name = name_candidate

            # Sınıf / Şube tespiti (örn: 8/A, 8/EG3, 8-A, 8A, Sınıfı 8/A)
            if not student_class:
                class_match = re.search(r"(?:Şube|Sınıf|Sınıfı)\s*:?\s*([A-Za-z0-9\/\.\-]+)", text, re.IGNORECASE)
                if class_match:
                    cand = class_match.group(1).strip().upper()
                    if not any(kw in cand for kw in ["DENEME", "SINIF", "KURUM", "SINAV"]):
                        student_class = class_match.group(1).strip()

            # LGS Puanı tespiti
            if text.startswith("LGS") or "LGS" in text:
                try:
                    curr_idx = rows.index(row)
                    for row_below in rows[curr_idx : curr_idx + 5]:
                        b_text = _row_to_text(row_below)
                        m_score = re.search(r"\b(\d{3}[,\.]\d{2,3})\b", b_text)
                        if m_score:
                            score = m_score.group(1).replace(",", ".")
                            break
                except Exception:
                    pass

        return {
            "full_name": full_name,
            "student_code": student_code,
            "student_class": student_class,
            "tyt_score": score,
            "tyt_avg": score,
        }

    def _parse_summary_table(self, rows: list[list[dict[str, Any]]], warnings: list[str]) -> list[dict[str, Any]]:
        subjects: list[dict[str, Any]] = []
        in_table = False
        for row in rows:
            text = _row_to_text(row)
            if _should_skip_line(text):
                continue
            if "DERSLER" in text and "Soru Sayısı" in text:
                in_table = True
                continue
            if not in_table:
                continue
            if text.startswith("Toplam"):
                parts = text.split()
                if len(parts) >= 5:
                    try:
                        total_q = _safe_int(parts[1])
                        correct = _safe_int(parts[2])
                        wrong = _safe_int(parts[3])
                        subjects.append(
                            {
                                "subject_name": "Toplam",
                                "total_questions": total_q,
                                "correct": correct,
                                "wrong": wrong,
                                "blank": total_q - correct - wrong,
                                "net": _safe_float(parts[4]) if len(parts) > 4 else 0.0,
                                "success_pct": _safe_float(parts[5]) if len(parts) > 5 else 0.0,
                                "is_total_row": True,
                            }
                        )
                    except Exception:
                        pass
                in_table = False
                continue

            tokens = text.split()
            if len(tokens) < 4:
                continue
            subject_name = self._detect_subject_name(text)
            if not subject_name:
                continue
            rest = text[len(subject_name) :].split()
            if len(rest) < 3:
                continue
            try:
                total_q = _safe_int(rest[0])
                correct = _safe_int(rest[1])
                wrong = _safe_int(rest[2])
                blank = total_q - correct - wrong
                subjects.append(
                    {
                        "subject_name": subject_name.strip(),
                        "total_questions": total_q,
                        "correct": correct,
                        "wrong": wrong,
                        "blank": blank,
                        "net": _safe_float(rest[3]) if len(rest) > 3 else 0.0,
                        "success_pct": _safe_float(rest[4]) if len(rest) > 4 else 0.0,
                        "is_total_row": False,
                    }
                )
            except Exception as exc:
                warnings.append(f"Özet tablo satırı parse edilemedi: '{text[:60]}' — {exc}")
        return subjects

    def _clean_subject_name(self, raw_name: str) -> str:
        name = raw_name.strip()
        # Türkçe karakterleri harita ile normalize et
        clean_upper = (
            name.upper().replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
        )

        if "TURKCE" in clean_upper:
            return "Türkçe"
        if "MATEMATIK" in clean_upper:
            return "Matematik"
        if "FEN" in clean_upper:
            return "Fen Bilimleri"
        if "INKILAP" in clean_upper or "TC" in clean_upper or "ATATURK" in clean_upper:
            return "T.C. İnkılap Tarihi ve Atatürkçülük"
        if "INGILIZCE" in clean_upper or "YABANCI" in clean_upper or "ENGLISH" in clean_upper:
            return "Yabancı Dil"
        if "DIN" in clean_upper or "DKAB" in clean_upper or "AHLAK" in clean_upper:
            return "Din Kültürü ve Ahlak Bilgisi"
        if "SOSYAL" in clean_upper:
            return "Sosyal Bilgiler"
        return name

    def _detect_subject_name(self, text: str) -> str:
        for prefix in sorted(_SUBJECT_PREFIXES, key=len, reverse=True):
            if text.startswith(prefix):
                return prefix
        return self._detect_analysis_subject_header(text)

    def _parse_analysis_section(self, rows: list[list[dict[str, Any]]], warnings: list[str]) -> list[dict[str, Any]]:
        outcomes: list[dict[str, Any]] = []
        current_subject = ""
        for row in rows:
            text = _row_to_text(row)
            stripped = text.strip()
            if not stripped or "Konu Adı" in stripped or re.match(r"^Sayı\s+Doğ\s+Yan\s+%$", stripped):
                continue
            if _should_skip_line(stripped):
                continue

            subject_match = self._detect_analysis_subject_header(stripped)
            if subject_match:
                current_subject = self._clean_subject_name(subject_match)
                continue

            outcome = self._parse_outcome_row(stripped, current_subject, warnings)
            if outcome:
                outcomes.append(outcome)

        return outcomes

    def _detect_analysis_subject_header(self, text: str) -> str:
        stripped = text.strip()
        cleaned_upper = (
            stripped.upper().replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
        )

        if "TOPLAM" in cleaned_upper or "DENEME" in cleaned_upper or "GENEL" in cleaned_upper:
            return ""

        known_keywords = ["TURKCE", "MATEMATIK", "FEN", "INKILAP", "INGILIZCE", "YABANCI", "DIN", "SOSYAL"]
        for kw in known_keywords:
            if kw in cleaned_upper:
                # Kazanım satırı ile ders başlığı ayrımı:
                # Kazanım satırları son 4 token sayı olan satırlardır (örn: S D Y B%)
                tokens = stripped.split()
                if len(tokens) >= 5:
                    try:
                        int(tokens[-2])
                        int(tokens[-3])
                        int(tokens[-4])
                        # Eğer bu bir kazanım satırı ise başlık değil, geç
                        # Ancak satır başında sadece ders adı kalıyorsa ders başlığıdır
                        if not any(stripped.startswith(p) for p in _SUBJECT_PREFIXES):
                            continue
                    except ValueError:
                        pass
                return stripped
        return ""

    def _parse_outcome_row(self, text: str, current_subject: str, warnings: list[str]) -> dict[str, Any] | None:
        if text.startswith("- "):
            text = text[2:].strip()

        tokens = text.split()
        if len(tokens) < 5:
            return None

        try:
            b_pct = float(tokens[-1])
            wrong = int(tokens[-2])
            correct = int(tokens[-3])
            total_q = int(tokens[-4])
        except ValueError:
            return None

        if total_q < 0 or correct < 0 or wrong < 0:
            return None

        description = " ".join(tokens[:-4]).strip()
        if not description:
            return None

        blank = total_q - correct - wrong
        if blank < 0:
            blank = 0

        return {
            "subject_name": current_subject,
            "outcome_description": description,
            "total_questions": total_q,
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "success_pct": b_pct,
            "measured": total_q > 0,
        }

    def _normalize_student(self, raw_s: dict[str, Any]) -> dict[str, Any]:
        full_name = raw_s.get("full_name", "")
        student_code = raw_s.get("student_code", "")
        analysis: list[dict[str, Any]] = raw_s.get("analysis_subjects", [])
        summary: list[dict[str, Any]] = raw_s.get("summary_subjects", [])
        subject_results: list[dict[str, Any]] = []

        if analysis:
            aggregated_analysis = {}
            for item in analysis:
                subj = item.get("subject_name", "")
                desc = item.get("outcome_description", "")
                key = (subj, desc)

                if key not in aggregated_analysis:
                    aggregated_analysis[key] = {
                        "subject_name": subj,
                        "topic_name": desc,
                        "outcome_code": None,
                        "outcome_description": desc,
                        "correct": 0,
                        "wrong": 0,
                        "blank": 0,
                        "total_questions": 0,
                        "success_pct": 0.0,
                        "measured": item.get("measured", True),
                    }

                agg = aggregated_analysis[key]
                agg["correct"] += item.get("correct", 0)
                agg["wrong"] += item.get("wrong", 0)
                agg["blank"] += item.get("blank", 0)
                agg["total_questions"] += item.get("total_questions", 0)

                if agg["total_questions"] > 0:
                    agg["success_pct"] = (agg["correct"] / agg["total_questions"]) * 100.0

            subject_results = list(aggregated_analysis.values())
        else:
            for item in summary:
                if item.get("is_total_row"):
                    continue
                total_q = item.get("total_questions", 0)
                subject_results.append(
                    {
                        "subject_name": item.get("subject_name", ""),
                        "topic_name": "",
                        "outcome_code": None,
                        "outcome_description": "",
                        "correct": item.get("correct", 0),
                        "wrong": item.get("wrong", 0),
                        "blank": item.get("blank", 0),
                        "total_questions": total_q,
                        "success_pct": item.get("success_pct", 0.0),
                        "measured": total_q > 0,
                    }
                )

        return {
            "student_code": student_code,
            "full_name": full_name,
            "student_class": raw_s.get("student_class", ""),
            "tyt_score": raw_s.get("tyt_score"),
            "subject_results": subject_results,
        }
