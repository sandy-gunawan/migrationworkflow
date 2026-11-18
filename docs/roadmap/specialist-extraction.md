# Opsi berikutnya: ekstraksi specialist

[Indeks dokumentasi](../README.md) / [Roadmap](README.md)

**Belum diimplementasikan.** Saat ini yang dimigrasikan adalah orkestrasi:
router/specialist tetap named/versioned Foundry agents, termasuk model dan tool
yang mereka panggil. Hosting MAF atau memakai Logic Apps tidak menghilangkan
biaya model, Fabric, Search atau knowledge retrieval.

## Pilot yang paling sederhana

Gunakan maintenance MCP pada data dummy TRK001/WO001 sebagai kandidat pertama.
Layanan MCP/API yang sudah baru dan terlindungi MI tetap menjadi sumber data.

1. Bekukan prompt, tool schema, versi, konteks dan keluaran specialist sumber.
2. Implementasikan specialist Python dengan provider/SDK yang sudah benar-benar
   diuji pada versi tersebut. Jangan menganggap contoh SDK versi lain kompatibel.
3. Batasi tool ke operasi read-only dan resource/content allowlist demo.
4. Pertahankan MI dan audience yang benar. Jangan menghidupkan local keys yang
   dinonaktifkan kebijakan.
5. Pertahankan parser evidence serta citation: teks model tanpa tool/result nyata
   bukan sukses.
6. Jalankan golden cases dan auth/error negatives terhadap kedua runtime.
7. Ukur token, latency, CPU/memory, cold start dan biaya aktual sebelum mengklaim
   penghematan atau memperluas batch.

Lanjutkan REST/Search setelah pilot lulus. Native Fabric DataAgent/Foundry IQ
tetap punya kontrak dan lifecycle service sendiri; memindahkan pemanggilnya
bukan berarti menulis ulang service tersebut.

## Work IQ dan Fabric IQ

- Native ontology masih `FeatureNotAvailable`; jangan menggantinya dengan mock
  lalu menyebut migrasi native sudah selesai.
- Work IQ hanya boleh memakai sandbox Microsoft 365 terpisah dengan data dummy
  dan izin yang disetujui. Tidak ada akses ke mail, Teams atau SharePoint live.
- Delegated-user context harus dipertahankan bila memang diwajibkan produk;
  lakukan desain consent/billing dan pengujian terpisah.

Ekstraksi banyak agent memerlukan assessment pada
[rencana estate](forty-agent-assessment.md), bukan perubahan otomatis pada
resource yang sudah ada.
