# Belajar demo dari nol

[Indeks dokumentasi](../README.md)

Cerita yang dipakai sepanjang materi: operator menanyakan work order untuk
`TRK001`; alur memilih specialist maintenance; specialist membaca data sintetis;
aplikasi memeriksa `WO001` dan sumbernya sebelum menampilkan jawaban.

## Urutan belajar

| Tahap | Baca | Setelah itu kamu bisa menjelaskan |
|---|---|---|
| 1. Tujuan | [Beranda demo](../../README.md) | Apa yang dipindahkan dan apa yang tetap berjalan di Foundry. |
| 2. Persiapan | [Setup dan batas](../how-to/setup-and-source.md) | Perbedaan membaca repository, menyiapkan Python, dan mengakses Azure. |
| 3. Pilihan | [YAML ke MAF](../how-to/foundry-yaml-to-maf-newbie.md) | Bedanya declarative YAML, code-first, dan Logic Apps. |
| 4. Perjalanan data | [Satu request sampai pulang](../how-to/maf-internals-newbie.md) | Siapa memanggil siapa, input/output-nya, dan siapa memakai hasilnya. |
| 5. Praktik | [UI lokal](../how-to/maf-ui.md) dan [prompt](../how-to/test-prompts.md) | Cara mencoba satu pertanyaan jika lingkungan live sudah tersedia. |
| 6. Bukti | [Cara membaca pengujian](../reference/validation.md) | Kenapa health, unit test, dan retrieval live adalah bukti yang berbeda. |

## Tiga hal yang harus dibedakan

- **Definisi:** YAML/JSON menyimpan aturan, tetapi tidak berjalan sendiri.
- **Runtime:** Python MAF atau Logic Apps menjalankan aturan itu.
- **Layanan dan data:** agent/model, API, MCP, Search, dan Fabric memiliki koneksi,
  izin, dan lifecycle sendiri.

Browser mengirim request ke server yang sudah hidup. Browser tidak menjalankan
file Python secara langsung.

## Tentang materi workshop lama

Salinan operator juga mempunyai pelajaran HTML interaktif, diagram editable,
dan capture portal. Paket tersebut memakai detail lingkungan serta bukti
historis, sehingga tidak ikut versi publik ini. Materinya tetap disimpan lokal;
Markdown di atas menjadi jalur belajar publik yang tidak memerlukan paket itu.
