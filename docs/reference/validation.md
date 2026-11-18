# Cara membaca hasil pengujian

[Indeks dokumentasi](../README.md)

Expected result, tes lokal, dan retrieval live adalah tiga hal yang berbeda.
Dokumentasi publik menjelaskan kontrak serta cara memeriksa hasil; bukti mentah
lingkungan disimpan lokal.

## Apa yang dibuktikan?

| Pemeriksaan | Membuktikan | Tidak membuktikan |
|---|---|---|
| Dependency check / lint | Dependency konsisten dan kode memenuhi pemeriksaan yang dijalankan. | Azure dapat diakses atau jawaban grounded. |
| Unit / contract test | Perilaku kode untuk input/fixture yang diuji. | Request baru benar-benar sampai ke provider live. |
| Health HTTP | Server menjawab endpoint health. | Agent atau tool sudah mengambil data. |
| Replay baseline | Parser/normalizer bekerja pada bukti yang disimpan. | Kondisi layanan saat ini sama dengan saat bukti diambil. |
| Run live | Eksekusi aktual pada jalur, versi, dan waktu itu. | Jalur lain atau semua kasus otomatis lulus. |
| Browser test | Alur UI yang benar-benar dicoba. | Seluruh corpus dijalankan melalui browser. |

## Status hasil

| Status | Arti | Yang perlu diperiksa |
|---|---|---|
| `success` | Retrieval lolos pemeriksaan. | Fakta wajib, sumber, versi agent, dan evidence tool aktual. |
| `blocked` | Capability yang dibutuhkan belum tersedia. | Alasan eksplisit, tanpa specialist atau citation buatan. |
| `clarification` | Input belum cukup spesifik. | Meminta klarifikasi, tanpa mengambil banyak sumber sekaligus. |
| `unsupported` | Permintaan di luar cakupan. | Penolakan yang sesuai, tanpa write tool atau akses bisnis. |
| `failed` | Eksekusi atau dependency gagal. | Error terlihat, tidak diubah menjadi jawaban sukses. |

Kasus `blocked` yang sesuai expected result dapat lulus kontrak, tetapi tetap
bukan retrieval sukses. "Semua kasus cocok" tidak sama dengan "semua kasus
mengambil data".

## Corpus dan cakupan

[Corpus golden](../../tests/golden/cases.json) memuat 50 pertanyaan asli.
[Katalog ringkas](../how-to/test-prompts.md) memilih sembilan contoh.
Jangan menyamakan sembilan smoke cases dengan seluruh 50 kasus.

Baseline MAF, eksperimen declarative, prototype code-first, Logic Apps, dan
browser masing-masing mempunyai scope sendiri. Tidak ada klaim hasil live baru
yang bisa ditarik hanya dengan membaca halaman ini atau menjalankan tes awal.

## Isi ringkasan yang berguna

Saat membuat laporan untuk dibagikan, tulis:

1. Tanggal dan waktu pengujian.
2. Jalur yang diuji serta versi source, target, agent, dan dependency.
3. Case ID dan jumlah kasus per status.
4. Route, fakta wajib, sumber, serta hasil aktual.
5. Bentuk bukti: unit, replay, HTTP, browser, atau live provider.
6. Pemeriksaan yang gagal, dilewati, dan batas lingkungan.

Jangan memasukkan token, key, credential, signed URL, identitas pribadi, atau
konten bisnis ke laporan publik. ID korelasi dan screenshot juga perlu ditinjau
sesuai kebutuhan serta izin berbagi.

**Lanjutkan:** [perintah pengujian](../how-to/migrate-test-and-cleanup.md) atau
[checklist publikasi](../../CONTRIBUTING.md#sebelum-masuk-github-publik).
