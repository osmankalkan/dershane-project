# Bilinen Eksikler ve Sonraki Adımlar

## Hiç başlanmamış, gerçek eksikler
- **İkinci parser (çoklu format desteği)** — sistem şu an sadece TYT formatını destekliyor, gerçek kullanılacak format (ortaokul/LGS) henüz test edilmedi.
- **Otomatik test yazımı** — `test_pdf_parser`, `test_student_matching`, `test_duplicate_exam`, `test_missing_topic`, `test_ocr_fallback` gibi testler hiç yazılmadı, şu ana kadar sadece manuel test script'i (`test_parser_manual.py`) kullanıldı.
- **Yedekleme (backup) stratejisi** — PostgreSQL için otomatik yedekleme scripti hiç kurulmadı.
- **Row-Level Security (RLS)** — `institution_id` filtrelemesi şu an sadece kod seviyesinde yapılıyor, veritabanı seviyesinde garanti altına alınmamış. Tek kurum olduğu sürece risk değil, çoklu kuruma geçişte önce ele alınmalı.
- **Hassas veri loglama kontrolü** — backend logları öğrenci isimleri ve sonuçlarını açıkça terminale yazıyor, production'a geçmeden önce gözden geçirilmeli.

## Planlanmış, geliştirme aşamasında
- PDF karne çıktısı
- Ayarlar sayfası (manuel veri girişi/düzenleme)
- Kural tabanlı yorumlama sistemi

## Bilinçli olarak ertelenen (şu an gerekmiyor, ileride internete açılırken veya çoklu kullanıcıya geçilirken ele alınacak)
- Auth / JWT / roller
- WhatsApp/SMS entegrasyonu
- AI/ML tabanlı tahminleme
- Hosting/domain (internet erişimi)

> **Not**: Bu bölüm, ileride "hangi eksikler bilinçli, hangileri unutulmuş" sorusuna hızlı cevap verebilmek için eklenmiştir.
