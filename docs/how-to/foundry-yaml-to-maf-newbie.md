# Dari YAML Foundry ke MAF

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

Untuk melihat ketiga opsi dulu, buka
[pelajaran HTML: migrasi workflow Foundry](https://sandy-gunawan.github.io/migrationworkflow/).
Halaman ini melengkapi pelajaran itu dengan detail teknis dua jalur MAF.

Migrasi di demo ini memindahkan **aturan alur kerja**, bukan mengunggah YAML ke
portal MAF. Microsoft Agent Framework (MAF) adalah library yang dipakai aplikasi
untuk menjalankan agent dan workflow.

Contohnya tetap sama: pertanyaan tentang `TRK001` memilih jalur maintenance,
membaca `WO001`, lalu mengembalikan jawaban dengan sumber sintetis yang sesuai.

## Apa yang pindah, apa yang tetap?

| Bagian | Yang terjadi |
|---|---|
| Kondisi dan urutan langkah | Diterapkan pada runtime tujuan. |
| Pertanyaan dan konteks percakapan | Harus diteruskan dengan perilaku yang setara. |
| Router dan specialist | Pada demo ini tetap agent bernama/berversi di Foundry. |
| Model, tools, API, Search, dan Fabric | Tidak otomatis dibuat atau dipindahkan. |
| Identity, izin, dan koneksi | Harus disiapkan serta diuji terpisah. |
| Bukti hasil | Harus dibandingkan ulang; kode yang bisa dijalankan belum tentu setara. |

Analogi sederhananya: YAML adalah lembar prosedur. Mengganti pos yang menjalankan
prosedur tidak otomatis memindahkan petugas, peralatan, dan catatan sumbernya.

## Pilih jalur dengan sadar

| Jalur | Cara menulis alur | Yang menjalankannya | Batas di repository |
|---|---|---|---|
| Declarative / Cara 1 | YAML yang cocok dengan loader | Runtime declarative resmi | Eksperimen terpisah, bukan baseline hosted MAF. |
| Code-first | Kode Python yang membangun graph | MAF `WorkflowBuilder` | Baseline memakai compiler terbatas dan mapping turunan source. |
| Bantuan code generation | Copilot/tooling membantu menulis kode | Runtime hasil implementasi | Bukan runtime tambahan dan bukan jaminan parity. |
| Logic Apps | Definisi workflow native JSON/WDL | Azure Logic Apps | Target alternatif; bukan tahap sesudah MAF. |

**YAML konfigurasi target tidak selalu berarti official YAML loader.** Pada
baseline demo, compiler membaca source, memvalidasi subset yang didukung, lalu
MAF membangun graph Python. Jangan menyebut compiler internal sebagai converter
generik Microsoft.

Versi baseline mengikuti [manifest dependency](../../pyproject.toml).
Eksperimen declarative memakai environment sendiri; jangan memasang dependency
eksperimen ke environment baseline hanya agar import berhasil.

## Urutan migrasi

### 1. Bekukan sumber

Ambil export workflow dan versi agent yang disepakati. Simpan hash, daftar
dependensi, kontrak output, serta contoh input/output.

Input langkah ini adalah versi sumber yang jelas. Output-nya menjadi acuan
compiler dan pengujian berikutnya. Jangan menimpa source frozen untuk
menghilangkan kegagalan tes.

### 2. Periksa kompatibilitas

Catat kondisi, default branch, urutan activity, conversation, error, timeout,
dan fitur seperti loop atau approval. Compiler demo hanya mendukung subset
yang memang diimplementasikan.

Construct yang tidak dikenal harus menghasilkan diagnostic. Mengabaikan node
secara diam-diam membuat hasil migrasi terlihat berhasil padahal perilakunya
berubah.

### 3. Bangun target

Lihat [compiler dan mapping](../../src/demo_common/migration.py),
[runtime MAF](../../src/maf_service/workflow.py), dan
[alat konversi](../../tools/migrate_workflow.py).

Pada lingkungan operator yang lengkap, alat konversi membaca source frozen dan
menghasilkan target beserta mapping. Ini pekerjaan lokal; hasilnya belum berarti
target sudah dideploy atau diberi izin. Review perubahan hasil generate sebelum
dipakai.

### 4. Sambungkan layanan

Siapkan agent/version, identity, audience, tool connections, serta sumber data
dummy. Untuk mode hosted, Managed Identity (MI) adalah identitas aplikasi Azure;
untuk UI lokal, kode memakai identity Azure CLI operator.

App Service dan Foundry Hosted Agent adalah pilihan hosting yang berbeda.
Implementasi demo tidak membuktikan bahwa semua pilihan hosting resmi sudah
dijalankan.

### 5. Bandingkan perilaku

Gunakan [corpus prompt](test-prompts.md) yang sama. Periksa:

- route dan hanya specialist yang semestinya dipanggil;
- pertanyaan asli serta konteks percakapan;
- status, fakta wajib, sumber, dan bentuk hasil;
- error, route yang tidak didukung, serta capability yang `blocked`.

Prosa jawaban boleh berbeda. Fakta dan sumber tidak boleh dibuat-buat demi
mendapat hasil tes hijau. Baca [batas bukti](../reference/validation.md).

### 6. Alihkan pemanggil setelah lulus

Baru arahkan aplikasi pemanggil ke runtime tujuan setelah validasi, persetujuan,
dan rencana rollback tersedia. Jangan menghapus baseline atau mengubah sistem
bisnis sebagai bagian dari membaca panduan ini.

## Kalau ada perubahan

| Yang diubah | Tindak lanjut |
|---|---|
| YAML declarative | Muat ulang/restart runtime sesuai mekanisme loader, lalu uji ulang. Pada UI demo, file dibaca saat startup. |
| Graph Python baseline | Perbarui kode dan tes; restart proses lokal atau deploy versi aplikasi baru. |
| Definisi Logic Apps | Review lalu deploy/publish workflow native dan uji run baru. |
| Agent, tool, atau izin | Verifikasi versi/koneksi/akses; perubahan file workflow saja tidak memberikannya. |

## Referensi resmi

Panduan ini menjelaskan implementasi repository, bukan salinan jaminan dukungan
produk saat ini. Periksa kembali status preview, versi, dan retirement sebelum
memakai source workflow pada lingkungan baru:

- [Foundry workflows dan migration guide](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow#migration-guide).
- [Workflow di Foundry Toolkit](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/vs-code-agents-workflow-low-code).
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/).

**Berikutnya:** [ikuti satu request sampai kembali ke UI](maf-internals-newbie.md).
