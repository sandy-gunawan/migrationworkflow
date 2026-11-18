# Dokumentasi demo

[Beranda repository](../README.md)

**[Mulai belajar dari HTML: tiga opsi migrasi Foundry](https://sandy-gunawan.github.io/migrationworkflow/).**
Bandingkan MAF mapping ke kode Python, MAF yang memuat workflow YAML, dan
Azure Logic Apps. Pakai indeks ini untuk mencari referensi teknisnya.

## 1. Kenali demo

| Materi | Yang akan dipahami |
|---|---|
| [Materi HTML](https://sandy-gunawan.github.io/migrationworkflow/) | Tiga jalur migrasi dan langkah interaktif dari pertanyaan sampai jawaban. |
| [Alur belajar](training/README.md) | Urutan bacaan pendamping dari konsep sampai pengujian. |
| [Persiapan dan batas demo](how-to/setup-and-source.md) | Isi salinan publik, kebutuhan Python, dan prasyarat lingkungan live. |
| [YAML Foundry ke MAF](how-to/foundry-yaml-to-maf-newbie.md) | Pilihan migrasi dan bagian yang tidak otomatis ikut pindah. |
| [Video demo](videos/README.md) | Tiga UI dan [alur MCP di Logic Apps Designer](videos/README.md#4-logic-apps-designer-satu-jalur-mcp), dari posisi node sampai hasil di Run history. |

## 2. Pahami cara kerjanya

| Materi | Yang akan dipahami |
|---|---|
| [Arsitektur dan satu alur request](how-to/maf-internals-newbie.md) | Browser, Python, Foundry, tools, dan perjalanan jawaban kembali. |
| [Peta repository](reference/repository-map.md) | Folder sumber, hasil konversi, runtime, eksperimen, dan dokumentasi. |
| [Cara membaca hasil pengujian](reference/validation.md) | Perbedaan expected result, tes lokal, bukti live, dan cakupan pengujian. |

## 3. Coba dan periksa

| Materi | Yang akan dilakukan |
|---|---|
| [Panduan UI lokal](how-to/maf-ui.md) | Menyalakan, memeriksa health, mencoba satu prompt, dan menghentikan UI. |
| [Environment sendiri](how-to/run-in-your-environment.md) | Menjalankan tes bersih dan mengarahkan runtime ke sandbox sendiri tanpa mengganti source. |
| [Katalog prompt](how-to/test-prompts.md) | Memilih contoh input dan memeriksa route, fakta, status, serta sumber. |
| [Migrasi, pengujian, dan retensi](how-to/migrate-test-and-cleanup.md) | Memisahkan pemeriksaan lokal, tes live, dan pengelolaan resource. |

UI live hanya boleh dicoba pada lingkungan yang sudah disiapkan dan disetujui.
Membuka dokumentasi atau melihat health belum membuktikan retrieval data.

## 4. Pelihara dan kembangkan

- [Panduan kontribusi dan publikasi](../CONTRIBUTING.md): cara memperbarui materi,
  menjaga tautan, dan menyiapkan daftar file sebelum diunggah.
- [Roadmap](roadmap/README.md): perluasan multi-agent dan opsi ekstraksi specialist.

## Susunan dokumentasi

```text
docs/
  README.md                 Indeks utama
  index.html                Materi belajar visual, juga bisa dibuka offline
  how-to/                   Panduan konsep terapan dan langkah praktik
  reference/                Peta repository dan cara membaca bukti
  roadmap/                  Rencana, bukan fitur yang sudah selesai
  training/                 Urutan belajar dari nol
  videos/                   MP4, preview, subtitle, dan batas bukti rekaman
```

Nama file panduan lama dipertahankan agar tautan yang sudah dipakai tidak perlu
berubah. Setiap topik mempunyai satu halaman rujukan; README cukup mengarahkan
pembaca, bukan mengulang semua langkah teknis.

## Publik dan lokal

Panduan publik memakai contoh sintetis dan tidak bergantung pada tautan bukti
lingkungan. Versi panjang yang memuat nilai resource serta hasil historis
disimpan sebagai catatan `.local.md`. Workshop HTML lama, screenshot, dan
generator-nya juga tetap berada di salinan operator, tetapi tidak ikut Git.

Jangan menjadikan status atau biaya historis sebagai status cloud saat ini.
Aturan pemisahannya dijelaskan di
[panduan publikasi](../CONTRIBUTING.md#sebelum-masuk-github-publik).
