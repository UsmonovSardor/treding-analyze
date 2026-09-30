# MT5 Trade Journal 📊

MetaTrader 5 da qilingan **har bir savdoni** — aniq **sana/vaqt**, kirish/chiqish narxi,
**SL/TP**, **net P/L**, **pips** va **R-multiple** bilan — avtomatik ravishda
**Google Sheets** va **Excel** ga yozib boradigan senior darajadagi jurnal.

- ✅ Yopilgan savdolar → `Trades` varaq (sana/vaqt + to'liq natija)
- ✅ Ochiq pozitsiyalar → `Open_Positions` varaq (jonli, floating P/L)
- ✅ **Dublikatsiz** (bir savdo — bir marta) va **internet uzilsa yo'qolmaydi** (offline navbat)
- ✅ Bir nechta odam ishlata oladi (tarqoq model, har kim o'z config'i bilan)
- ✅ Kompyuter yonganda avto-ishga tushadi (Windows Task Scheduler)

> To'liq arxitektura va reja: [REJA.md](REJA.md)

---

## 1. O'rnatish

```powershell
# 1) Loyihani oling
git clone https://github.com/UsmonovSardor/treding-analyze.git
cd treding-analyze

# 2) Virtual muhit
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Kutubxonalar
pip install -r requirements.txt
```

> **Talab:** Windows + o'rnatilgan **MetaTrader 5** terminali + Python 3.11+.

---

## 2. Sozlash

```powershell
copy .env.example .env
```

`.env` faylni oching va to'ldiring:

- **MT5:** MT5 terminalingiz **ochiq** bo'lsa, `MT5_LOGIN/PASSWORD/SERVER` ni bo'sh
  qoldiring — tizim ochiq sessiyaga ulanadi (eng oddiy). Yoki login/parol/serverni yozing.
- **Excel:** `ENABLE_EXCEL=true`, `EXCEL_PATH=data/trades.xlsx` (tayyor).
- **Google Sheets:** quyidagi 3-bo'limga qarang.

---

## 3. Google Sheets ulash (bir martalik)

1. https://console.cloud.google.com → yangi loyiha yarating.
2. **Google Sheets API** ni yoqing (Enable).
3. **Service Account** yarating → JSON kalit yuklab oling.
4. JSON faylni `config/credentials/service_account.json` ga qo'ying.
5. Google Sheets'da yangi jadval oching. JSON ichidagi `client_email` manziliga
   (masalan `...@...iam.gserviceaccount.com`) jadvalni **Editor** sifatida **Share** qiling.
6. Jadval URL'idagi ID ni oling (`/d/`**`BU_QISM`**`/edit`) → `.env` dagi `GOOGLE_SHEET_ID` ga yozing.

Varaqlar (`Trades`, `Open_Positions`) va sarlavhalar **avtomatik** yaratiladi.

---

## 4. Ishga tushirish

```powershell
# Doimiy kuzatuv (daemon) — savdo yopilishi bilan jadvalga tushadi
python -m src.main

# Yoki bir marta tekshirib chiqish (sinov uchun)
python -m src.main --once
```

O'tmishdagi savdolarni bir marta import qilish:

```powershell
python -m scripts.backfill --days 365
```

---

## 5. Avto-ishga tushirish (kompyuter yonganda)

```powershell
# PowerShell'ni Administrator sifatida oching
.\scripts\install_service.ps1
```

Bu `MT5TradeJournal` nomli Windows vazifasini yaratadi — login bo'lganda xizmat o'zi
ishga tushadi va uzilib qolsa qayta ko'tariladi.

---

## 6. Ko'p foydalanuvchi (tarqoq model)

Har trader o'z kompyuterida shu loyihani klon qiladi, o'zining `.env` faylini to'ldiradi
(o'z MT5 hisobi + o'z Google Sheet ID'si) va `python -m src.main` ni ishlatadi.
Barchasi mustaqil ishlaydi. Namuna: [config/users.example.yaml](config/users.example.yaml).

---

## 7. Testlar

```powershell
pip install pytest
pytest -q
```

---

## 8. Xavfsizlik

- `.env`, `config/credentials/*.json`, `config/users.yaml` — **git'ga tushmaydi** (`.gitignore`).
- Service account faqat siz ulashgan jadvalga kira oladi.
- Tizim **savdo qilmaydi** — faqat o'qiydi va yozadi (read-only, xavfsiz).

---

## Papka tuzilmasi

```
src/            asosiy kod (mt5_client, trade_engine, formatters, state, sinks/)
scripts/        backfill.py, install_service.ps1
tests/          unit testlar
config/         credentials/ (JSON), users.example.yaml
data/           trades.xlsx, journal.db (git'da yo'q)
logs/           kunlik loglar
REJA.md         to'liq senior reja va roadmap
```
