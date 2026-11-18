# Migrasi, pengujian, dan retensi

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

Panduan ini membedakan pemeriksaan kode lokal, konversi workflow, tes live,
dan pengelolaan resource. Jalankan PowerShell dari root repository dan gunakan
environment yang sesuai. Tidak ada perintah di sini yang memberi persetujuan
untuk mengubah resource Azure.

## 1. Pilih pemeriksaan yang sesuai

### Salinan publik tanpa konfigurasi operator

Setelah [instalasi lokal](setup-and-source.md), jalankan unit/contract tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit tests\contract -q
.\.venv\Scripts\python.exe -m pip check
```

Fixture untuk graph dibuat dari data sintetis; suite ini tidak membaca bukti
Azure operator. Ini bukan tes live atau seluruh pengujian eksperimen.

### Salinan operator dengan baseline lengkap

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit tests\contract -q
.\.venv\Scripts\python.exe -m ruff check src tests tools
.\.venv\Scripts\python.exe -m pip check
```

Unit/contract tests memakai fixture yang jelas ditandai sebagai sintetis.
Baseline serta bukti native tetap dipakai terpisah untuk tes live dan comparator;
jangan menyebut keberhasilan fixture sebagai bukti retrieval Azure.

Perintah di atas tidak menjalankan direktori tes `live`. Hasilnya juga bukan
bukti browser atau retrieval Azure baru.

## 2. Konversi source pada lingkungan lengkap

Baca [pilihan migrasi](foundry-yaml-to-maf-newbie.md) sebelum menjalankan alat
berikut. Perintah ini menulis ulang artefak target/mapping lokal, bukan hanya
menampilkan preview.

```powershell
.\.venv\Scripts\python.exe -m tools.migrate_workflow --target maf
.\.venv\Scripts\python.exe -m tools.migrate_workflow --target logicapps
```

| Target | Yang perlu diperiksa |
|---|---|
| MAF | Mapping source, versi agent, urutan activity, kondisi/default, konteks, dan graph Python. |
| Logic Apps | Definisi native WDL, validasi input, Switch, panggilan MI, normalisasi, dan korelasi run. |

Compiler menolak construct yang tidak didukung. Jangan melewati guard, mengubah
hash baseline, atau mengganti source demi memaksa konversi berhasil.
Output konversi belum berarti layanan sudah dideploy.

<a id="5-ulangi-tes-hosted-dengan-helper-baru"></a>

## 3. Sebelum pengujian live

Operator perlu meninjau:

1. Resource yang dimiliki demo, identity, allowlist, serta data sintetis.
2. Persetujuan provisioning/update dan hasil validation/what-if bila ada perubahan.
3. Versi source, target, agent, normalizer, dan corpus yang dibandingkan.
4. Anggaran dan lifecycle kapasitas, termasuk cleanup jika terjadi error.
5. Tempat menyimpan bukti tanpa token, credential, atau signed URL.

[Tes live](../../tests/live) dan [alat helper Azure](../../tools/run_azure_job.py)
memiliki prasyarat serta guard tambahan. Jangan sekadar mengaktifkan flag live
atau memakai run ID lama. Gunakan prosedur lingkungan yang telah disetujui.

Tes Foundry source, hosted MAF, native Logic Apps, UI browser, dan eksperimen
declarative mempunyai cakupan berbeda. Keberhasilan satu jalur tidak otomatis
mengesahkan jalur lain.

## 4. Bandingkan fakta dan sumber

Mulai dengan [prompt MCP01](test-prompts.md), lalu perluas ke corpus yang
disepakati. Bandingkan route, status, fakta, sumber, versi, dan korelasi.
Jangan menuntut prosa identik atau membaca flag `PASS` tanpa memeriksa isi.

Untuk Logic Apps, [lihat video alur MCP di Designer](../videos/README.md#4-logic-apps-designer-satu-jalur-mcp).
Mulai dari posisi node, buka **Parameters** untuk melihat data yang diteruskan,
lalu cocokkan `WO001` dan sumbernya di **Run history**. Video memakai run yang
sudah diverifikasi; menontonnya tidak memicu run baru.

[Comparator](../../tools/compare_runs.py) memerlukan laporan dan bukti lokal
yang lengkap. Pada lingkungan tersebut, jalankan:

```powershell
.\.venv\Scripts\python.exe -m tools.compare_runs
```

Tanpa bukti lokal, perintah ini bukan pemeriksaan yang bisa direproduksi dari
salinan publik. Simpan error asli dan ulangi run dengan identitas baru setelah
akar masalah diperbaiki; jangan menyatukan partial success menjadi bukti penuh.

## 5. Setelah mencoba

- Tunggu run dan cleanup selesai sebelum [menghentikan UI](maf-ui.md#4-hentikan-dengan-aman).
- Verifikasi kapasitas yang memang boleh dipause sudah kembali ke status yang
  disepakati; jangan mengubah kapasitas lain.
- Verifikasi helper yang dibuat untuk run sudah berhenti.
- Jangan menghapus baseline, menurunkan versi layanan, atau menghapus resource
  hanya karena sesi demo selesai.
- Perubahan ukuran, penghentian layanan, atau deletion memerlukan permintaan
  dan persetujuan terpisah.

UI yang sudah berhenti tidak berarti semua biaya berhenti. App hosting, Search,
Fabric, model/retrieval, storage, dan network mempunyai meter masing-masing.
Gunakan pricing serta tagihan yang sesuai waktu/region; angka historis bukan
quotation produksi atau hard cap.

## 6. Laporkan dengan batas yang jelas

Catat waktu, versi, cakupan, jumlah kasus per status, hasil aktual, error,
dan pemeriksaan yang dilewati. Jangan menyalin output mentah ke dokumentasi
publik sebelum review.

Lihat [referensi validasi](../reference/validation.md) untuk bentuk ringkasan
dan [panduan publikasi](../../CONTRIBUTING.md) untuk pemisahan materi lokal.
