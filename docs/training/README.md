# Belajar demo dari nol

[Indeks dokumentasi](../README.md)

**[Buka materi belajar HTML di browser](https://sandy-gunawan.github.io/migrationworkflow/).**
Mulai dari perbandingan MAF mapping ke kode Python, MAF pakai workflow YAML,
dan Azure Logic Apps. Untuk offline, clone atau unduh ZIP repository, ekstrak,
dan buka [index.html](../index.html) di browser bersama asetnya.

Cerita yang dipakai sepanjang materi: operator menanyakan work order untuk
`TRK001`; alur memilih specialist maintenance; specialist membaca data sintetis;
aplikasi memeriksa `WO001` dan sumbernya sebelum menampilkan jawaban.

## Urutan belajar

| Tahap | Baca | Setelah itu kamu bisa menjelaskan |
|---|---|---|
| 1. Tujuan | [Beranda demo](../../README.md) | Apa yang dipindahkan dan apa yang tetap berjalan di Foundry. |
| 2. Pilihan dan persiapan | [Perbandingan, setup, dan biaya](https://sandy-gunawan.github.io/migrationworkflow/workshop/workflow-migration-overview.html) | Siapa yang menjalankan alur, apa yang disiapkan terpisah, dan apa yang bisa menimbulkan biaya. |
| 3. Perjalanan data | [Satu request sampai pulang](https://sandy-gunawan.github.io/migrationworkflow/#alur) | Siapa memanggil siapa, input/output-nya, dan siapa memakai hasilnya. |
| 4. Praktik | [Logic Apps](https://sandy-gunawan.github.io/migrationworkflow/workshop/logicapps-alur-request.html) · [MAF code-first](https://sandy-gunawan.github.io/migrationworkflow/workshop/maf-code-first-walkthrough.html) · [MAF YAML](https://sandy-gunawan.github.io/migrationworkflow/workshop/maf-declarative-walkthrough.html) | Cara menyiapkan dan mencoba jalur yang dipilih, sesuai akses sandbox. |
| 5. Perluas contoh | [Katalog prompt](../how-to/test-prompts.md) | Memilih route lain dan membedakan hasil yang sukses atau memang diblokir. |
| 6. Bukti | [Cara membaca pengujian](../reference/validation.md) | Kenapa health, unit test, dan retrieval live adalah bukti yang berbeda. |

## Tiga hal yang harus dibedakan

- **Definisi:** YAML/JSON menyimpan aturan, tetapi tidak berjalan sendiri.
- **Runtime:** Python MAF atau Logic Apps menjalankan aturan itu.
- **Layanan dan data:** agent/model, API, MCP, Search, dan Fabric memiliki koneksi,
  izin, dan lifecycle sendiri.

Browser mengirim request ke server yang sudah hidup. Browser tidak menjalankan
file Python secara langsung.

## Versi workshop publik

Workshop publik memuat langkah setup dan screenshot yang sudah ditinjau. Salinan
operator yang membutuhkan nilai environment, manifest, atau bukti mentah tetap
lokal, dan tidak dibutuhkan untuk membuka workshop.
