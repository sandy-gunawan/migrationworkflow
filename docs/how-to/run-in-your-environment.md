# Menjalankan di environment sendiri

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

Source aplikasi boleh dibagikan tanpa membawa file env, key, atau credential
operator. Ada dua cara mencoba: tes offline untuk kode/kontrak, atau UI live
yang memakai layanan Azure pada sandbox milikmu.

## 1. Jalankan tes tanpa Azure

Dari PowerShell pada root repository, gunakan Python 3.13:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests\unit tests\contract -q
.\.venv\Scripts\python.exe -m pip check
```

Suite ini memakai fixture sintetis, tidak membutuhkan file env/config operator,
dan tidak memanggil Azure. Lima puluh prompt memeriksa graph serta hasil yang
diharapkan; itu bukan bukti 50 retrieval live.

Tes integrasi scanner dapat dilewati jika Gitleaks tidak terpasang. Untuk
publikasi, [gate secret](../../tools/check_publication.py) tetap mewajibkan
Gitleaks dan akan gagal jika tool tidak tersedia.

## 2. Buat profil runtime milikmu

Jangan mengubah source frozen, hash, atau konstanta runtime untuk mengganti
endpoint. Salin template:

```powershell
Copy-Item .\config\runtime.public.example.json .\config\runtime.local.json
```

Isi seluruh field pada salinan lokal:

| Kelompok | Yang diisi |
|---|---|
| Subscription/tenant | Identifier sandbox milikmu. |
| Foundry | Resource group, account, dan project berisi agent demo yang telah disiapkan. |
| Backing/MAF/Search | Nama resource milikmu, bukan URL bebas. Runtime membentuk endpoint Azure dan tetap memeriksa batas host. |
| API audience/caller | Application ID API dan caller verifikasi yang diizinkan. Ini identifier, bukan client secret. |
| Fabric | Workspace, lakehouse, serta kapasitas demo. Workspace retained dan native harus berbeda. |
| Logic Apps | Nama workflow milikmu. |

File profil **tidak menerima password, token, key, atau field credential**.
Semua field harus ada agar konfigurasi yang belum lengkap tidak diam-diam
memakai resource snapshot lama. Simpan file lokal tersebut di luar Git.

Aktifkan untuk proses yang akan dijalankan:

```powershell
$env:DEMO_ENVIRONMENT_FILE = (Resolve-Path .\config\runtime.local.json).Path
```

Profil dibaca saat proses Python mulai; restart proses setelah mengubahnya.
Tanpa variabel ini, perilaku snapshot lama tetap dipertahankan untuk operator
yang sudah mempunyai setup lokal. Default lama **bukan** akses bersama atau
persetujuan memakai subscription tersebut.

## 3. Siapkan layanan sandbox sebelum UI live

Profil hanya memilih tujuan, tidak memprovision atau memberi izin.
Siapkan [prasyarat Azure](setup-and-source.md#3-sebelum-mencoba-ui-live):

- Agent dengan nama/versi yang sesuai [workflow sumber](../../source/foundry/workflow.yaml).
- Backing API/MCP, Search index, native knowledge retrieval, dan seed sintetis.
- Model deployment serta koneksi tool yang benar pada project milikmu.
- Entra identity/RBAC dan caller policy yang disetujui.
- Workspace dan kapasitas F2 bertag demo bila route Fabric dipakai.

Kontrak demo tetap memakai nama agent/index/knowledge base, tag `48254cc6`,
namespace `urn:kppdemo:`, dan data sintetis yang sama. Mengganti project atau
subscription tidak otomatis mengganti kontrak tersebut. Jangan melemahkan
allowlist, pemeriksaan evidence, atau guard hash.

Login menggunakan Azure CLI pada tenant/subscription sendiri, lalu
[nyalakan UI MAF](maf-ui.md#1-nyalakan-server). Jangan menyalin token ke source.
Health HTTP hanya membuktikan startup; retrieval baru teruji setelah satu
prompt benar-benar mengembalikan fakta dan sumber yang sesuai.

## 4. API hosted dan target Logic Apps

Gunakan profil yang sama pada proses backing/MAF. Untuk host Azure, sediakan
file profil melalui jalur deployment non-publik dan set `DEMO_ENVIRONMENT_FILE`
ke path yang tersedia **di host**, bukan path laptop.

Konfigurasi authentication API tetap memakai pengaturan yang sudah didukung:
`DEMO_TENANT_ID`, `DEMO_API_AUDIENCE`, `DEMO_ALLOWED_CALLER_IDS`, serta
`DEMO_API_RESOURCE`. MAF juga memerlukan `DEMO_BACKING_URL` dan
`DEMO_FOUNDRY_ENDPOINT`; nilainya harus cocok dengan profil. Caller khusus
normalizer tetap dibatasi melalui `DEMO_NORMALIZER_CALLER_ID`.

Gunakan pengaturan aplikasi Azure untuk nilai lokal tersebut, bukan commit
file env. Jalur hosted menggunakan Managed Identity; UI lokal memakai Azure CLI.

Compiler Logic Apps memakai endpoint Foundry dan normalizer dari profil ketika
membuat target baru. [Perintah migrasi](migrate-test-and-cleanup.md#2-konversi-source-pada-lingkungan-lengkap)
menulis artefak lokal dan tetap membutuhkan source/baseline yang cocok.
Review output sebelum deployment; generated workflow lama tidak otomatis
berubah hanya karena file profil diedit.

## 5. Batas portabilitas yang perlu diketahui

- Template, script provisioning/helper, receipt, dan export historis masih
  mencatat resource serta identity snapshot asal. Itu bukan secret, tetapi
  **bukan installer generik sekali jalan** untuk sandbox baru.
- Profil mengatur runtime utama, Fabric scope, dan generator WDL; tidak
  menulis ulang template infrastruktur, raw export, receipt, atau persetujuan.
  Review parameter dan batas resource sebelum memakai alat administrasi.
- Tes live, comparator, UI Logic Apps tambahan, serta generator workshop
  memerlukan manifest/baseline lingkungan yang kamu buat dan verifikasi sendiri.
- Eksperimen declarative/code-first memakai dependency terpisah dari baseline.
  File env operator tidak disertakan dan tidak wajib ada untuk loader;
  konfigurasi endpoint dapat memakai profil runtime.
- Versi SDK, ketersediaan layanan, quota, serta status preview/retirement perlu
  diperiksa kembali. Keberhasilan offline bukan jaminan entitlement cloud.

Tidak ada resource baru yang dibuat hanya dengan membaca halaman ini atau
menjalankan unit tests. Request live, provisioning, dan perubahan kapasitas
memerlukan persetujuan serta pengendalian biaya sendiri.

## 6. Kembali ke setup operator yang lama

Di terminal yang tadi mengaktifkan profil baru:

```powershell
Remove-Item Env:\DEMO_ENVIRONMENT_FILE
```

Restart proses Python yang akan memakai setup lama. Perintah ini hanya melepas
variabel pada terminal tersebut; tidak menghapus profil, file env, manifest,
credential Azure CLI, atau resource cloud.
