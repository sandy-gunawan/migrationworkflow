# Perluasan multi-agent: contoh assessment 40 agent

[Indeks dokumentasi](../README.md) / [Roadmap](README.md)

Dokumen ini adalah rencana, **bukan klaim bahwa 40 agent telah dibaca atau
dimigrasikan**. Angka 40 dipakai sebagai contoh skala assessment berikutnya.
Demo memakai data mining sintetis. Jangan menjalankan discovery terhadap sistem
bisnis atau tenant Microsoft 365 tanpa izin dan batas akses yang jelas.

## Input yang perlu disediakan

Gunakan export yang disetujui dan sudah disanitasi, atau lingkungan sandbox baru.
Untuk setiap agent/workflow, catat:

| Area | Informasi wajib |
|---|---|
| Identitas | Nama, versi, project, pemilik, dan API family: named/versioned Prompt, Hosted, atau classic Thread/Run. |
| Orkestrasi | Kondisi beserta urutan/default, variabel, history percakapan, loop/parallel, timeout, approval, dan human handoff. |
| Agent | Prompt, model/deployment/version, output schema, parameter, dan perilaku error. |
| Tool | MCP/API/schema, filter tool, endpoint, grounding/citation format, dan bukti read-only. |
| Auth | MI project/runtime atau delegated user; audience, scope, role, caller boundary, dan lokasi secret jika memang diperlukan. |
| Data | Sandbox/content allowlist, klasifikasi, residency/cross-region, dan cara memverifikasi jawaban. |
| Operasi | Quota, preview/retirement, latency, biaya model/retrieval, retry dan audit. |

Jangan menyalin key/token atau konten bisnis ke export/dataset pengujian.

## Kelompok kompatibilitas

1. **Router dengan equality if/else dan satu specialist**: kandidat awal seperti
   demo ini. Compiler sekarang sengaja membatasi nama/resource/construct demo;
   bukan converter generik untuk seluruh estate.
2. **Variabel/history lebih kompleks**: perlu spec serta uji source-to-target
   tersendiri, bukan sekadar mengganti sintaks YAML.
3. **Parallel, loop, approval atau long-running**: belum didukung compiler demo.
   Definisikan semantik wait/cancel/retry sebelum memperluas implementasi.
4. **Classic API**: adapter/transformasi terpisah; jangan mencampur Thread/Run ID
   dengan Responses dan named/versioned agents.
5. **Delegated IQ/user context**: verifikasi pada sandbox terpisah. MI tidak
   otomatis menggantikan identitas pengguna atau izin Microsoft 365.

## Urutan batch yang disarankan

- Mulai satu router dan dua specialist yang paling sederhana.
- Bekukan export/hash, versi, data dummy, kontrak dan golden cases.
- Pindahkan **orkestrasi saja** ke MAF, lalu Logic Apps; specialist tetap Foundry.
- Bandingkan routing, fakta, sumber, korelasi dan error pada native run nyata.
- Perluas per kelompok kompatibilitas, bukan satu perubahan besar untuk 40 agent.
- Ekstraksi runtime specialist adalah pekerjaan opsional berikutnya, dengan
  persetujuan serta pengukuran biaya/latency baru.

Untuk setiap batch: unknown construct harus berhenti dengan diagnostic; jangan
silently drop node, mengarang citation, atau mengganti dependency gagal dengan
mock success. Simpan baseline agar presenter/operator bisa kembali ke source
tanpa menghapus atau menurunkan versi sistem klien.

Lihat [panduan migrasi](../how-to/foundry-yaml-to-maf-newbie.md),
[pengujian dan batas bukti](../how-to/migrate-test-and-cleanup.md), serta
[opsi ekstraksi specialist](specialist-extraction.md). Catatan scope, persetujuan,
dan hasil lingkungan tertentu disimpan terpisah dari dokumentasi publik.
