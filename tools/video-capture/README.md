# Perekam dan editor video demo

[Video jadi](../../docs/videos/README.md) | [README proyek](../../README.md)

Tool ini terpisah dari Python environment demo. Perekaman memakai Playwright
dan browser Microsoft Edge yang sudah terpasang di Windows. Pengeditan memakai
FFmpeg; tidak memerlukan layanan narasi, akun editor video, atau Remotion.

## Render ulang dari aset yang disertakan

Dari PowerShell pada root repository, dengan Node.js/npm dan Microsoft Edge:

```powershell
Set-Location .\tools\video-capture
npm ci
npm run stills
npm run render
npm run verify
```

Perintah ini hanya membaca capture yang disertakan, membuat title card secara
lokal, dan meng-encode video. **Tidak memanggil Azure atau menjalankan agent.**
Periksa sampel scene di folder output sebelum meng-encode. MP4, preview PNG,
subtitle, dan laporan pemeriksaan ditulis ke [folder video](../../docs/videos).

Untuk satu video saja:

```powershell
npm run stills -- --kind=maf
npm run render -- --kind=maf
```

Pilihan lain adalah `logicapps` dan `declarative`. Render ulang membaca
[timeline.json](public/timeline.json) dan capture publik, bukan folder mentah.
Jika mengubah teks pada timeline, jaga maksimal dua baris dan 42 karakter
per baris, serta perbarui SRT yang bersesuaian.
[story.json](story.json) adalah template penjelasan untuk pembuatan timeline
baru dari capture mentah pada langkah berikutnya.

## Mengambil capture live baru

Ini **operasi terpisah dan berbayar**, bukan bagian render ulang. Siapkan
ketiga UI serta izin pada lingkungan demo sendiri terlebih dahulu:

- MAF awal: port 8765, environment Python utama.
- Logic Apps: port 8766, environment Python utama.
- Declarative: port 8767, environment Python eksperimen declarative.

Jalankan hanya setelah mendapat persetujuan request model/tool:

```powershell
npm run capture -- maf --allow-live
npm run capture -- logicapps --allow-live
npm run capture -- declarative --allow-live
npm run timeline
```

Setiap perintah capture mengirim tepat satu pertanyaan TRK001 melalui form UI.
Receipt mencegah pengulangan tanpa review; tidak ada auto-retry model ketika
hasil gagal. Jangan menghapus receipt untuk diam-diam mengulang request.

Video mentah dan receipt tetap lokal pada folder `raw`. `timeline` menerima
hanya receipt sukses, membuat salinan capture H.264 yang lebih kecil, dan
menulis timeline serta SRT baru. Periksa seluruh scene sebelum publikasi:
video biner tidak dapat dinyatakan bebas secret hanya dari pemindaian teks.

Perekam tidak mengambil seluruh desktop, menyimpan header Authorization,
merekam token browser, atau mengaktifkan Fabric. Script juga tidak memberikan
izin Azure atau membuat resource baru.
