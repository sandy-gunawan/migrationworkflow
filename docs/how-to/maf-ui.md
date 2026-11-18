# UI MAF lokal: mulai, coba, dan berhenti

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

UI ini menjalankan graph MAF, bukan memutar ulang jawaban tersimpan. Browser
berbicara dengan server lokal; server memanggil agent Foundry dan tools demo.
Setiap klik Run dapat menambah biaya cloud.

## Sebelum mulai

- Selesaikan [persiapan](setup-and-source.md), termasuk konfigurasi operator,
  akses Azure CLI, agent/version, dan sumber data sintetis.
- Gunakan environment baseline dari [pyproject.toml](../../pyproject.toml).
  Eksperimen declarative mempunyai environment terpisah.
- Pastikan port `8765` tidak sedang dipakai proses lain.
- Jangan memakai resource atau data bisnis sungguhan untuk mencoba panduan ini.

Menyalakan UI tidak melakukan provisioning, tidak memberi izin tambahan, dan
tidak otomatis membuat lingkungan baru cocok dengan guard demo.

## 1. Nyalakan server

Dari PowerShell pada root repository:

```powershell
.\.venv\Scripts\python.exe .\tools\run_maf_ui.py --port 8765
```

Biarkan terminal terbuka, lalu buka **http://127.0.0.1:8765/**.
Server hanya mendengarkan pada loopback komputer ini. Jangan mengubahnya menjadi
endpoint publik atau menambahkan reverse proxy sebagai jalan pintas.

## 2. Periksa kesiapan HTTP

Di terminal PowerShell kedua:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8765/health'
```

Hasil yang diharapkan memuat `status: ready` dan `service: local-maf-ui`.
Ini hanya membuktikan server melayani HTTP. Retrieval Azure belum diuji.

Jika startup gagal karena konfigurasi atau akses belum lengkap, perbaiki
prasyaratnya. Jangan menutupi error dengan manifest fiktif atau mematikan guard.

## 3. Coba satu pertanyaan

Masukkan:

```text
Show work orders for equipment TRK001.
```

Lalu jalankan satu kali dan amati:

1. **Pertanyaan:** input asli tidak berubah.
2. **Jalur eksekusi:** router memilih `mcp`, lalu satu specialist maintenance.
3. **Kode dan trace:** agent/version serta langkah berasal dari run aktual.
4. **Jawaban dan sumber:** terdapat `WO001`, `TRK001`, dan sumber maintenance
   sintetis yang sesuai.

Ini hasil yang diharapkan, bukan janji setiap request pasti sukses. Error,
dependency yang tidak tersedia, atau evidence yang tidak valid harus terlihat.
Progress tidak mengungkap pikiran internal model.

Lihat [katalog prompt](test-prompts.md) untuk route lain. Route Fabric memerlukan
kapasitas dan prosedur lifecycle yang sudah disetujui; jangan mengaktifkan
kapasitas lain hanya agar contoh berhasil.

## 4. Hentikan dengan aman

Tunggu run dan cleanup selesai. Di terminal kedua:

```powershell
.\.venv\Scripts\python.exe .\tools\run_maf_ui.py --port 8765 --stop
```

Launcher memeriksa identitas layanan pada port itu dan meminta shutdown.
Jika ada run aktif, permintaan dapat ditolak dengan HTTP 409; tunggu lalu ulangi.
Jangan mematikan semua proses Python berdasarkan nama.

Pastikan terminal server menulis `Application shutdown complete` dan kembali
ke prompt. Kamu juga bisa memeriksa listener:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
```

Tidak ada output berarti tidak ada listener pada port tersebut. Menutup tab
browser saja tidak menghentikan server. Shutdown UI juga **tidak** menghentikan
semua resource atau biaya Azure.

## Masalah umum

| Gejala | Yang perlu diperiksa |
|---|---|
| Port sudah dipakai | Buka server demo yang sudah berjalan atau pilih port lain. Jangan hentikan proses yang tidak kamu miliki. |
| Health tidak merespons | Terminal server, port, dependency, dan konfigurasi startup. |
| HTTP 409 saat stop | Run/cleanup masih aktif; tunggu selesai. |
| Azure menolak akses | Identity, tenant, audience, caller policy, dan izin runtime yang disetujui. Jangan mengganti dengan token di source. |
| Data tidak terverifikasi | Periksa error dan sumber aktual; teks agent saja bukan bukti retrieval. |
| Perubahan kode belum terlihat | Selesaikan run, restart server bila perlu, lalu reload halaman. |

**Berikutnya:** [bandingkan hasil](migrate-test-and-cleanup.md) dan
[pahami batas pengujian](../reference/validation.md).
