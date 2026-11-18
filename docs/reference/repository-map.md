# Peta repository

[Indeks dokumentasi](../README.md)

Bedakan **sumber**, **hasil konversi**, **runtime**, **alat bantu**, dan
**bukti lingkungan**. Berada di repository yang sama tidak berarti semuanya
berjalan bersamaan.

## Kode dan definisi

| Lokasi | Peran | Sebelum mengubah |
|---|---|---|
| [src](../../src) | Layanan dan kode bersama. | Periksa pemanggil, kontrak, dan tests terkait. |
| [source](../../source) | Definisi sumber serta snapshot demo. | Jangan menimpa baseline frozen tanpa proses re-baseline. Export lingkungan perlu review terpisah sebelum publikasi. |
| [migration](../../migration) | Mapping source ke target. | Jaga keterlacakan action, kondisi, dan versi. |
| [targets](../../targets) | Definisi target hasil konversi. | Periksa sumber generate; jangan menganggap ini resource yang otomatis sudah aktif. |
| [contracts](../../contracts) | Schema API dan keluaran. | Jaga konsistensi producer, consumer, serta contract tests. |
| [data/seed](../../data/seed) | Data pertambangan sintetis. | Perubahan fakta dapat memengaruhi golden cases dan validasi evidence. |
| [tests](../../tests) | Unit/contract dengan fixture sintetis, live, dan corpus golden. | Tes live memerlukan konfigurasi serta baseline operator; suite unit/contract tidak. |

## Operasi dan eksperimen

| Lokasi | Peran | Batas |
|---|---|---|
| [infra](../../infra) | Template infrastruktur. | Membaca template tidak memprovision resource. Parameter lingkungan tidak dipublikasikan. |
| [tools](../../tools) | Setup, konversi, packaging, validasi, dan launcher. | Tidak semuanya read-only; baca scope sebelum menjalankan. |
| [spikes](../../spikes) | Eksperimen dan UI tambahan. | Bukan otomatis baseline; dependency serta bukti pengujiannya dapat berbeda. |
| [config](../../config/README.md) | Penjelasan, contoh publik, dan template profil runtime. | Nilai operator tetap lokal. Profil harus diisi lengkap sebelum dipakai live. |

## Dokumentasi

| Lokasi | Isi |
|---|---|
| [README utama](../../README.md) | Ringkasan dan pintu masuk. |
| [Indeks docs](../README.md) | Seluruh jalur baca publik. |
| [how-to](../how-to/README.md) | Panduan konsep terapan dan langkah praktik. |
| [training](../training/README.md) | Urutan belajar dari nol. |
| [roadmap](../roadmap/README.md) | Opsi lanjutan yang belum menjadi implementasi. |
| [Panduan kontribusi](../../CONTRIBUTING.md) | Aturan pemeliharaan dan pemeriksaan sebelum publikasi. |

## Yang hanya ada di salinan operator

- File `.local.md`: penjelasan panjang, detail resource, dan catatan historis.
- Konfigurasi aktual dan parameter deployment.
- Evidence mentah, snapshot run, hasil biaya, serta catatan persetujuan.
- Workshop HTML lama, screenshot portal, diagram, dan generator yang terkait
  lingkungan tersebut.
- Virtual environment, cache, ZIP, dan build output.

File-file itu tetap ada di komputer operator, tetapi dipisahkan oleh
[.gitignore](../../.gitignore). Mengabaikan file tidak menghapusnya dari riwayat
Git jika sebelumnya pernah di-commit.
