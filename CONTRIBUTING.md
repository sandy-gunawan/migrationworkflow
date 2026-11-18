# Memelihara dokumentasi dan menyiapkan publikasi

[Beranda repository](README.md) | [Indeks dokumentasi](docs/README.md)

## Letakkan materi di tempat yang sesuai

| Materi | Tempat |
|---|---|
| Ringkasan dan pintu masuk | [README utama](README.md) |
| Daftar bacaan | [Indeks docs](docs/README.md) |
| Konsep terapan dan langkah mencoba | [how-to](docs/how-to/README.md) |
| Peta file serta cara membaca hasil | [reference](docs/reference) |
| Urutan belajar | [training](docs/training/README.md) |
| Rencana yang belum dikerjakan | [roadmap](docs/roadmap/README.md) |
| Nilai lingkungan, hasil historis, dan bukti mentah | Salinan operator; tidak masuk dokumentasi publik. |

Pertahankan nama file panduan yang sudah digunakan. Jika harus memindahkan file,
perbarui seluruh tautan relatif, generator, rute aset, dan tests pemakainya.
Jangan memindahkan HTML/screenshot hanya untuk membuat folder terlihat rapi.

## Gaya penulisan

- Gunakan bahasa Indonesia sehari-hari, kalimat pendek, dan istilah teknis yang
  memang diperlukan.
- Mulai dari tujuan, komponen, dan input/output sebelum potongan kode.
- Pisahkan persiapan, startup, request runtime, dan shutdown.
- Sebutkan tempat menjalankan perintah, hasil yang diharapkan, dan cara memeriksa.
- Gunakan tautan relatif agar navigasi bekerja di GitHub maupun salinan lokal.
- Pakai satu contoh sintetis yang konsisten, seperti `TRK001` dan `WO001`.
- Untuk diagram publik, utamakan Mermaid di Markdown; jangan memakai renderer
  pihak ketiga untuk mengirim kode atau data privat.
- Bedakan ilustrasi, expected result, bukti historis, hasil baru, dan usulan.
- Jangan menaruh token, secret, credential, atau signed URL di dokumen.

Hindari menyalin daftar yang sudah mempunyai sumber utama. Contohnya,
[corpus golden](tests/golden/cases.json) tetap menjadi sumber lengkap prompt;
[katalog publik](docs/how-to/test-prompts.md) cukup memilih contoh dan menjelaskan
cara menilainya.

## Pemeriksaan perubahan

Untuk perubahan Markdown:

1. Buka semua tautan baru/yang berubah dari posisi file tersebut.
2. Pastikan targetnya ikut daftar file Git, bukan hanya ada di komputer operator.
3. Periksa anchor judul, urutan bacaan, serta konsistensi contoh.
4. Pastikan snippet sesuai kode dan tidak mengklaim hasil tes yang belum dijalankan.

Untuk perubahan HTML lokal, gunakan source generator yang sesuai, jalankan
tests dokumentasi terkait, lalu periksa browser desktop dan layar kecil.
Jangan mengedit hasil generate saja jika perubahan akan tertimpa saat regenerate.
Materi HTML lokal tidak otomatis menjadi bagian publikasi.

## Sebelum masuk GitHub publik

- [ ] Tinjau daftar file yang akan masuk, bukan hanya README.
- [ ] Pastikan tidak ada konfigurasi operator, bukti mentah, parameter lingkungan,
  catatan `.local.md`, workshop/capture lama, build output, atau credential.
- [ ] Tinjau kode, export agent, source/target, dan resource runtime secara terpisah.
  Aturan ignore dokumentasi tidak menjamin isi area tersebut siap dipublikasikan.
- [ ] Periksa screenshot, metadata gambar, URL bertanda tangan, identitas pribadi,
  dan hak penggunaan materi sebelum menyertakan aset baru.
- [ ] Pilih lisensi sesuai hak serta kebijakan pemilik repository. Perapian ini
  tidak memilih atau memberikan lisensi secara otomatis.
- [ ] Periksa apakah nilai sensitif pernah masuk commit sebelumnya. Menambah
  `.gitignore` tidak menghapus riwayat Git atau mencabut credential.
- [ ] Jangan mengklaim tes live, deployment, atau pemeriksaan seluruh repository
  selesai jika yang diperiksa baru dokumentasi.

Nama resource, endpoint, tenant/subscription ID, dan hash snapshot bukan
credential. Nilai non-secret tersebut boleh tetap ada pada source demo.
File env aktual tetap tidak boleh ikut, termasuk yang bernama `.env.example`.
Contoh profil publik hanya berisi placeholder; jangan menggantinya dengan
konfigurasi operator.

### Pemeriksaan otomatis sebelum staging dan push

Pasang Gitleaks pada mesin pemeriksa jika belum ada; tool ini tidak diperlukan
untuk menjalankan aplikasi. Lalu:

```powershell
.\.venv\Scripts\python.exe .\tools\check_publication.py
```

Gate memindai kandidat publik **dan blob index**, menolak file env/ignored yang
dipaksa masuk staging, serta tidak mencetak nilai secret. Konfigurasi scanner
memakai rules bawaan, tanpa menonaktifkan temuan dengan komentar allowlist.
Snapshot pemeriksaan dibersihkan setelah selesai. Jalankan lagi setelah staging;
file working tree yang bersih tidak menjamin isi index juga bersih.

Ini pemindaian lokal, bukan jaminan semua format secret di masa depan terdeteksi.
Aktifkan secret scanning/push protection GitHub bila tersedia. Jangan memakai
`git push --mirror`, menyalin folder Git lama, atau menerbitkan refs checkpoint
agent: checkpoint dapat menyimpan file lokal yang memang tidak untuk publik.

### Materi belajar HTML publik

Edit [index.src.html](docs/index.src.html), lalu render dengan Visual Explainer
ke [index.html](docs/index.html). Simpan CSS dan JavaScript di file hasil render.
Hapus tautan Google Fonts yang ditambahkan renderer agar halaman memakai font
lokal dan tetap bisa dibuka offline. Cek diagram di desktop dan ponsel; file
`index.sheet*.png` adalah hasil pemeriksaan, bukan materi publik.

GitHub Pages menyajikan `main:/docs` sebagai situs statis; pertahankan
[.nojekyll](docs/.nojekyll). Materi ini tidak boleh memuat konfigurasi, capture,
atau bukti mentah dari workshop lokal.

Lihat daftar kandidat tanpa menambahkan file:

```powershell
git status --short
git ls-files --others --exclude-standard
```

Jika hasil review sudah sesuai, contoh staging **dokumentasi saja**:

```powershell
git add -- .gitignore README.md CONTRIBUTING.md docs `
  config\README.md config\environment.public.example.json
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
```

Perintah tersebut bukan instruksi untuk menambahkan seluruh kode aplikasi.
Pastikan semua file yang sudah lebih dulu berada di staging juga ditinjau.
Jangan memakai `git add -f` untuk melewati pemisahan file lokal.

Commit/push dilakukan setelah review dan persetujuan pemilik. Tidak ada
publikasi otomatis hanya karena dokumentasi atau aturan ignore diperbarui.
