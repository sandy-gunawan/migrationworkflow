# Konfigurasi: contoh publik dan nilai lokal

[Persiapan demo](../docs/how-to/setup-and-source.md) |
[Panduan publikasi](../CONTRIBUTING.md)

[environment.public.example.json](environment.public.example.json) hanya
menunjukkan bentuk beberapa pengaturan dengan placeholder. File ini **tidak
dibaca otomatis oleh runtime** dan bukan template provisioning siap jalan.
Jangan menganggap menyalinnya sudah membuat agent, koneksi, role, atau resource.

Konfigurasi operator mencakup tenant/subscription, endpoint, resource, identity,
allowlist, workspace, dan versi yang benar-benar dipakai. Simpan serta bagikan
nilai tersebut hanya melalui jalur yang disetujui.

Pada snapshot operator, bahkan file bernama `environment.example.json`
memuat nilai lingkungan. Nama `example` saja bukan bukti bahwa file aman untuk
publik. Karena itu, versi publik hanya mengizinkan README ini dan dua contoh
placeholder; file konfigurasi lain tetap lokal.

## Profil runtime untuk lingkungan sendiri

[runtime.public.example.json](runtime.public.example.json) adalah template
konfigurasi yang benar-benar bisa dibaca runtime utama. Salin menjadi
`runtime.local.json`, isi **semua** field, lalu arahkan `DEMO_ENVIRONMENT_FILE`
ke file lokal tersebut. Tidak ada token, password, atau key dalam format ini.

Profil menentukan endpoint Foundry, backing/MAF, Search, subscription, scope
Fabric, serta normalizer Logic Apps yang dihasilkan compiler. Nama agent,
seed, index/knowledge base, versi, dan tag sintetis tetap mengikuti kontrak demo.
Lihat [langkah lengkap](../docs/how-to/run-in-your-environment.md).

Jangan mengubah konfigurasi operator untuk menyesuaikan contoh publik.
Pemakaian pada lingkungan baru memerlukan review guard, identity, resource scope,
source/baseline, dan pengujian tersendiri.
