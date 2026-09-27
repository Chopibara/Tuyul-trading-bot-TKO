# Tuyul Trading Bot TKO V5.3.40

Bot trading crypto otomatis yang belajar dari data market Tokocrypto.

### Gimana cara kerja AI nya?
1. **Ambil Data:** Dari API publik Tokocrypto (PEPE, DOGE, SHIB, dll) real-time
2. **Bersihin Data:** Skip data kosong/error, buang harga 0/negatif, pakai try-except biar gak crash, cek minimal 12 data baru latih
3. **Latih AI:** Pakai 50-200 data terakhir, kasih label naik/turun (target 0.15%)
4. **Cek Akurasi:** Kalo akurasi di bawah 45% -> skip, gak beli

### Tech Stack
- Python
- scikit-learn
- Groq API

### Data Cleaning
- `if price is None or price <= 0: continue`
- Validasi jumlah data & handle error API

### Hasil
Akurasi rata-rata 45-65%, pernah tembus 80%+ pas market sideways stabil.
Jika akurasi <45% -> sistem otomatis skip untuk hindari false signal.
Pernah evaluasi 4x SL saat market crash, jadi ada pembelajaran risk management.
