# Persiapan dan batas demo

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

Ada dua kegiatan yang berbeda: **membaca dan memeriksa kode secara lokal**, atau
**menjalankan pertanyaan ke layanan Azure**. Menyiapkan Python tidak membuat
resource cloud, memberi izin, atau mengaktifkan koneksi agent.

## 1. Yang tersedia di salinan publik

- [Data mining sintetis](../../data/seed/mining.json).
- [Kontrak request dan hasil](../../contracts/demo.schema.json).
- [Implementasi layanan](../../src), [alat bantu](../../tools), dan [tests](../../tests).
- Definisi workflow sumber, mapping, serta target demo. Baca
  [peta repository](../reference/repository-map.md) sebelum mengubahnya.
- [Contoh konfigurasi publik](../../config/environment.public.example.json).
  Isinya placeholder, bukan akses ke lingkungan operator.
- [Profil runtime publik](../../config/runtime.public.example.json) untuk
  menyiapkan runtime utama pada sandbox sendiri.

Konfigurasi Azure aktual, bukti mentah, dan catatan operator tidak disertakan.
[Workshop publik](https://sandy-gunawan.github.io/migrationworkflow/) memuat
langkah setup dan screenshot yang sudah ditinjau. Tes live dan generator workshop
lama tetap memerlukan prasyarat lingkungan sendiri.

## 2. Siapkan Python lokal

**Kebutuhan:** Git dan Python 3.13, sesuai [pyproject.toml](../../pyproject.toml).
Jalankan PowerShell dari folder root repository yang sudah kamu salin.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Perintah ini membuat environment Python terpisah dan memasang proyek beserta
alat development. Instalasi membutuhkan koneksi ke package registry, tetapi
tidak melakukan provisioning Azure.

Verifikasi dependency:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Untuk tes unit/contract yang tidak memerlukan bukti live atau manifest operator:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit tests\contract -q
```

Hasil yang diharapkan: dependency konsisten dan tes selesai tanpa kegagalan.
Tes graph memakai respons sintetis, bukan replay bukti Azure milik operator.
Tes tersebut memeriksa perilaku lokal; **tidak membuktikan akses atau retrieval
Azure berhasil**. Daftar pemeriksaan yang lebih luas ada pada
[panduan pengujian](migrate-test-and-cleanup.md).

## 3. Sebelum mencoba UI live

Operator perlu menyiapkan dan memverifikasi:

| Bagian | Yang harus tersedia |
|---|---|
| Identitas lokal | Azure CLI pada tenant/subscription sandbox yang diizinkan. UI lokal memakai identitas operator, bukan Managed Identity laptop. |
| Foundry | Project, model deployment, router, specialist, versi, dan koneksi tool yang sesuai. |
| Backing API/MCP | Endpoint demo yang benar, seed sintetis, audience, dan izin pemanggil. |
| Search / native knowledge retrieval | Index, konten dummy, serta koneksi yang memang sudah diuji. |
| Fabric | Workspace, lakehouse, DataAgent, dan kapasitas demo jika route Fabric akan dipakai. |
| Baseline lokal | Manifest, mapping, export, serta bukti yang diwajibkan runtime atau pengujian tertentu. |
| Pengendalian biaya | Persetujuan run, batas resource, serta prosedur resume/pause dan penghentian helper. |

[Konfigurasi publik](../../config/README.md) menjelaskan bentuk placeholder dan
alasan konfigurasi operator tidak dipublikasikan.

**Jangan sekadar mengganti semua nama resource lalu menjalankan script setup.**
Kode dan compiler demo mempunyai guard serta allowlist khusus data/agent demo.
Gunakan [profil runtime](run-in-your-environment.md) untuk sandbox sendiri.
Script deployment historis dan hasil export tetap perlu review serta baseline
baru; profil runtime bukan pengganti receipt atau persetujuan provisioning.

## 4. Source dan batas perilaku

Workflow sumber adalah acuan migrasi, bukan file yang boleh diganti tanpa
memperbarui mapping, hash, serta baseline. Sebelum migrasi:

1. Ambil export dari versi yang disepakati.
2. Catat agent/version, kondisi, urutan activity, konteks percakapan, dan hasil
   terminal.
3. Bekukan data sintetis dan corpus pengujian.
4. Bandingkan perilaku target, bukan hanya kemiripan sintaks.

Tidak ada akses ke data bisnis, mail, Teams, atau SharePoint sungguhan yang
diperlukan untuk memahami contoh ini. Capability yang belum tersedia harus
tetap `blocked`, bukan diganti hasil sukses buatan.

**Berikutnya:** [pilih jalur migrasi](foundry-yaml-to-maf-newbie.md), lalu ikuti
[arsitektur dan satu request](maf-internals-newbie.md).
