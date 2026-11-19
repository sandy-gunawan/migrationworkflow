# Dokumentasi demo

[Beranda repository](../README.md)

**[Mulai belajar dari HTML: tiga opsi migrasi Foundry](https://sandy-gunawan.github.io/migrationworkflow/).**
Bandingkan MAF mapping ke kode Python, MAF yang memuat workflow YAML, dan
Azure Logic Apps. Pakai indeks ini untuk mencari referensi teknisnya.

## 1. Pilih workshop HTML

| Materi | Yang akan dipahami |
|---|---|
| [Materi HTML](https://sandy-gunawan.github.io/migrationworkflow/) | Tiga jalur migrasi dan langkah interaktif dari pertanyaan sampai jawaban. |
| [Perbandingan dan setup bersama](https://sandy-gunawan.github.io/migrationworkflow/workshop/workflow-migration-overview.html) | Persiapan sandbox, perbedaan saat alur berubah, biaya, dan kriteria lulus. |
| [Logic Apps: setup dan alur](https://sandy-gunawan.github.io/migrationworkflow/workshop/logicapps-alur-request.html) | Dari izin dan WDL hingga POST OAuth dan Run history. Lanjut ke [node dan parameter](https://sandy-gunawan.github.io/migrationworkflow/workshop/logicapps-node-walkthrough.html) dan [UI](https://sandy-gunawan.github.io/migrationworkflow/workshop/logicapps-ui-walkthrough.html). |
| [MAF code-first](https://sandy-gunawan.github.io/migrationworkflow/workshop/maf-code-first-walkthrough.html) | Mapping JSON, graph Python, profil sandbox, dan cara memeriksa UI. |
| [MAF workflow YAML](https://sandy-gunawan.github.io/migrationworkflow/workshop/maf-declarative-walkthrough.html) | `WorkflowFactory`, environment terpisah, dan cara membaca snapshot. |
| [Video demo](videos/README.md) | Rekaman tiga UI serta [alur MCP di Designer](videos/README.md#4-logic-apps-designer-satu-jalur-mcp). |

## 2. Pahami cara kerjanya

| Materi | Yang akan dipahami |
|---|---|
| [Alur belajar](training/README.md) | Urutan bacaan dari memilih jalur sampai memeriksa hasil. |
| [YAML Foundry ke MAF](how-to/foundry-yaml-to-maf-newbie.md) | Bagian definisi yang bisa dipetakan dan batas compiler. |
| [Arsitektur dan satu alur request](how-to/maf-internals-newbie.md) | Browser, Python, Foundry, tools, dan perjalanan jawaban kembali. |
| [Peta repository](reference/repository-map.md) | Folder sumber, hasil konversi, runtime, eksperimen, dan dokumentasi. |
| [Cara membaca hasil pengujian](reference/validation.md) | Perbedaan expected result, tes lokal, bukti live, dan cakupan pengujian. |

## 3. Coba dan periksa

| Materi | Yang akan dilakukan |
|---|---|
| [Persiapan dan batas demo](how-to/setup-and-source.md) | Menyiapkan Python dan memeriksa prasyarat live. |
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
  index.html                Beranda workshop, bisa dibuka offline dari clone/ZIP
  workshop/                 Workshop HTML, gaya, interaksi, dan screenshot
  how-to/                   Rujukan teknis dan perintah terperinci
  reference/                Peta repository dan cara membaca bukti
  roadmap/                  Rencana, bukan fitur yang sudah selesai
  training/                 Urutan belajar dari nol
  videos/                   MP4, preview, subtitle, dan batas bukti rekaman
```

Workshop adalah jalur utama untuk belajar. Rujukan Markdown melengkapi langkah
yang butuh detail implementasi, batas sandbox, atau validasi.

## Publik dan lokal

Panduan publik memuat setup, nama field, kode, serta screenshot yang sudah
ditinjau. Nilai environment aktual, credential, dan bukti mentah yang mungkin
memuatnya tidak ikut. Generator dan hasil workshop lama yang membaca data
operator tetap lokal, terpisah dari [workshop publik](workshop).

Jangan menjadikan status atau biaya historis sebagai status cloud saat ini.
Aturan pemisahannya dijelaskan di
[panduan publikasi](../CONTRIBUTING.md#sebelum-masuk-github-publik).
