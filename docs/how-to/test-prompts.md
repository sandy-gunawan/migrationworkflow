# Katalog prompt dan hasil yang diharapkan

[Indeks dokumentasi](../README.md) / [Panduan](README.md)

Prompt di sini adalah **input pengguna untuk pengujian**, bukan system
instruction agent. Gunakan data sintetis dan [lingkungan yang disetujui](setup-and-source.md).
Menjalankan prompt live dapat menambah biaya.

## Sumber acuan

[Corpus golden](../../tests/golden/cases.json) adalah sumber utama daftar lengkap
50 kasus. Tabel berikut hanya memilih satu contoh per kategori agar daftar
panjang tidak disalin ke banyak dokumen.

Jangan mengubah prompt, expected facts, atau seed untuk menyembunyikan kegagalan.
Jangan menganggap semua kasus harus menghasilkan retrieval sukses.

## Sembilan contoh awal

| ID | Prompt | Route / hasil yang diharapkan |
|---|---|---|
| MCP01 | Show work orders for equipment TRK001. | `mcp`, success: `WO001`, `TRK001`, sumber maintenance sintetis. |
| REST01 | How much DIESEL stock is at MS01? Include its unit. | `rest_api`, success: 18000 litres, MS01/DIESEL, sumber stok sintetis. |
| KNOW01 | Find the document reporting code for Copper Ridge MS01. | `knowledge`, success: `DEMO-COPPER-17`, `DMO-DOC-01`. |
| FIQ01 | Use Foundry IQ native knowledge-base retrieval: what is the Copper Ridge reporting code? | `foundry_iq`, success: kode dan document key yang sesuai. |
| FAB01 | What was production in tonnes for MS01 on November 1, 2026 for the day shift? | `fabric_data`, success: 1250 tonnes, MS01, tanggal/shift dan sumber sesuai. Memerlukan Fabric yang siap. |
| ONTO01 | Use the native Fabric IQ ontology to describe MineSite entities. | `fabric_iq`, blocked pada snapshot demo; jangan mengarang ontology retrieval. |
| WORK01 | Use Work IQ for the demo workplace handover. | `work_iq`, blocked tanpa sandbox terpisah; tidak membaca workplace sungguhan. |
| CLAR01 | Tell me about MS01. | `clarification`, meminta satu topik yang jelas tanpa specialist. |
| UNSUP01 | Change a record in the real live business system. | `unsupported`, menolak perubahan tanpa specialist atau write tool. |

Nama equipment, site, dokumen, dan angkanya berasal dari
[seed sintetis](../../data/seed/mining.json), bukan data operasional.

## Cara mencoba

1. Pilih jalur yang diuji: source Foundry, MAF, atau Logic Apps.
2. Pastikan agent/version, source, data, dan baseline tidak berubah.
3. Mulai run/percakapan baru per kasus.
4. Kirim prompt persis seperti corpus.
5. Catat case ID, route, status, fakta wajib, sumber, dan korelasi run.
6. Untuk route data, pastikan hanya specialist yang tepat bekerja.
7. Untuk `blocked`, `clarification`, dan `unsupported`, pastikan tidak ada
   specialist atau pengambilan data bisnis.

UI source Foundry bergantung pada versi serta ketersediaan produk. Periksa
[dokumentasi workflow resmi](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow)
sebelum mencoba source lama; jangan membuat atau menyimpan versi baru hanya
untuk menguji baseline yang frozen.

## Cara menilai

- **Route benar** belum cukup: fakta, status, serta sumber juga harus benar.
- **Sumber tercetak** belum cukup: periksa hasil tool native yang mendukungnya.
- **Kalimat berbeda** belum tentu gagal: bandingkan isi, bukan prosa identik.
- **Dependency gagal** harus terlihat sebagai gagal, bukan diganti jawaban manual.
- **Blocked yang benar** dapat lulus kontrak, tetapi bukan retrieval sukses.

Lihat [cara membaca bukti](../reference/validation.md) serta
[pengujian dan retensi](migrate-test-and-cleanup.md). Bukti lingkungan tidak
disertakan dalam katalog publik; expected result bukan laporan run baru.
