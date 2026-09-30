# MT5 Savdo Jurnali (Trade Journal) — Senior Reja

> **Maqsad:** MetaTrader 5 da qilingan har bir savdoni (kirish, TP, SL, chiqish, natija) —
> aniq **sana/vaqt** va **to'liq natijalari** bilan — avtomatik ravishda **Google Sheets** yoki
> **Excel** ga yozib boradigan, senior darajadagi, tez va ishonchli tizim.
> **Ko'p foydalanuvchi** ishlata oladigan qilib qurilади. Keyinchalik **optimallashtirish/analitika**
> xususiyatlari qo'shiladi.

Muallif uchun eslatma: bu reja — bitta katta boshqaruv hujjati. Kod bosqichma-bosqich shu reja
asosida yoziladi. Har bir bosqich oxirida "Bajarildi" belgisi qo'yiladi.

---

## 0. Qisqacha xulosa (TL;DR)

- **Yadro texnologiya:** Python + rasmiy `MetaTrader5` kutubxonasi (Windows).
- **Yozish manzili:** Google Sheets (asosiy, bulutda, real-time) **va/yoki** Excel `.xlsx` (lokal zaxira).
- **Ishlash rejimi:** doimiy ishlaydigan **fon xizmati (daemon)** — MT5 tarixi va ochiq
  pozitsiyalarni kuzatib turadi, yangi/yopilgan savdolarni aniqlab, jadvalga qator qo'shadi.
- **Ikki xil hodisa manbai:**
  1. **Polling (so'rov)** — Pythondan `history_deals_get` / `positions_get` ni interval bilan tekshirish (ishonchli, oddiy).
  2. **Event-driven (hodisaviy)** — MT5 dagi MQL5 Expert Advisor (EA) `OnTradeTransaction` da darhol lokal HTTP endpointga xabar yuboradi (bir zumda yozish). *Ixtiyoriy, 2-fazada.*
- **Ko'p foydalanuvchi:** har foydalanuvchi/hisob uchun alohida config + alohida sheet/varaq;
  bitta markaziy xizmat bir nechta MT5 hisobini boshqara oladi.
- **Optimallashtirish (keyin):** analitika (winrate, PF, expectancy, R-multiple, drawdown),
  strategiya bo'yicha guruhlash, dashboard, xatolik-signallari.

---

## 1. Talablar (Requirements)

### 1.1 Funksional talablar
- [ ] Har bir **yopilgan savdo** (deal/position) jadvalga yoziladi.
- [ ] Har bir **ochilgan pozitsiya** ham (ixtiyoriy) real-time yoziladi/yangilanadi.
- [ ] Yoziladigan maydonlar (minimal senior to'plam):
  - Ticket (position ID), Order ID, Deal ID
  - Symbol (masalan XAUUSD, EURUSD)
  - Yo'nalish: BUY / SELL
  - Hajm (lot / volume)
  - **Kirish narxi**, **Kirish vaqti** (sana + vaqt, timezone bilan)
  - **Chiqish narxi**, **Chiqish vaqti**
  - **Stop Loss (SL)** narxi, **Take Profit (TP)** narxi
  - Yopilish sababi: TP / SL / Manual / Stop Out (deal reason)
  - **Profit** (valyutada), **Commission**, **Swap**, **Net P/L**
  - **Pips / points**, **R-multiple** (risk-ga nisbatan natija)
  - Davomiylik (holding time), Magic number, Comment
  - Balans (savdodan keyingi), Hisob raqami, Broker
- [ ] Sana/vaqt **aniq va bir xil formatda** (ISO 8601 + timezone).
- [ ] Har bir savdo **faqat bir marta** yoziladi (dublikat yo'q — idempotentlik).
- [ ] Manual (qo'lda) savdo, EA/robot savdosi — barchasi qamrab olinadi.

### 1.2 Nofunksional talablar
- [ ] **Tez:** yangi savdo yopilgach bir necha soniyada jadvalga tushadi.
- [ ] **Aniq/ishonchli:** yozuv yo'qolmaydi, dublikat bo'lmaydi, internet uzilsa navbatga olinadi.
- [ ] **Barqaror:** xizmat kompyuter yonganda avto-ishga tushadi (Windows Service / Task Scheduler).
- [ ] **Xavfsiz:** hisob paroli, API kalitlari kodda emas — `.env` / config faylda, git'ga tushmaydi.
- [ ] **Kengaytiriladigan:** yangi maydon/analitika qo'shish oson (modulli arxitektura).
- [ ] **Kuzatiladigan (observability):** log fayllar, xatolik bildirishnomalari (Telegram, ixtiyoriy).

---

## 2. Arxitektura

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MT5 Terminal (Windows)                         │
│   - Savdolar (manual + EA)                                             │
│   - [Ixtiyoriy] Journal EA: OnTradeTransaction → lokal HTTP push       │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │ MetaTrader5 Python API         │ WebRequest (event push, 2-faza)
                ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Python Journal Service (daemon)                     │
│                                                                        │
│  ┌────────────┐   ┌───────────────┐   ┌──────────────┐   ┌─────────┐  │
│  │ mt5_client │──▶│  trade_engine  │──▶│  formatters  │──▶│  sinks  │  │
│  │ (ulanish,  │   │ (yangi savdoni │   │ (maydonlar,  │   │ Sheets/ │  │
│  │  poll)     │   │  aniqlash,     │   │  R-multiple, │   │ Excel/  │  │
│  │            │   │  dedup, state) │   │  pips, vaqt) │   │ CSV)    │  │
│  └────────────┘   └───────┬────────┘   └──────────────┘   └────┬────┘  │
│                           │                                    │       │
│                    ┌──────▼──────┐                    ┌────────▼─────┐ │
│                    │ state store │                    │ retry queue  │ │
│                    │ (SQLite:    │                    │ (offline →   │ │
│                    │  seen deals)│                    │  keyin push) │ │
│                    └─────────────┘                    └──────────────┘ │
│                                                                        │
│  config/  (har foydalanuvchi/hisob uchun profil)                       │
│  logs/    (kunlik log fayllar)                                         │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │                                 │
                ▼                                 ▼
        ┌───────────────┐               ┌─────────────────┐
        │ Google Sheets │               │  Excel (.xlsx)  │
        │ (service acc) │               │  lokal zaxira   │
        └───────────────┘               └─────────────────┘
                ▲
                │ (keyin: analitika/dashboard shu Sheets ustida)
        ┌───────┴────────┐
        │ Analytics/BI    │  ← optimallashtirish fazasi
        └────────────────┘
```

**Nega Python + polling asosiy?**
- Rasmiy `MetaTrader5` kutubxonasi tarix va pozitsiyalarga to'liq kirish beradi — SL/TP,
  commission, swap, deal reason hammasi bor.
- Polling — eng ishonchli: terminal restart bo'lsa ham, o'tkazib yuborilgan savdolarni
  keyingi so'rovda ushlaydi (EA push'da esa terminal o'chsa hodisa yo'qoladi).
- EA push — 2-fazada "bir zumda" yozish uchun qo'shimcha (past latency), lekin polling
  har doim "safety net" bo'lib qoladi.

---

## 3. Texnologiya to'plami (Tech Stack)

| Qatlam | Tanlov | Sabab |
|---|---|---|
| Til | Python 3.11+ | MT5 API, boy ekotizim |
| MT5 ulanish | `MetaTrader5` (pip) | Rasmiy, Windows |
| Google Sheets | `gspread` + `google-auth` (service account) | Server-to-server, OAuth siz |
| Excel | `openpyxl` | Formatlash, formulalar |
| State/dedup | `sqlite3` (standart kutubxona) | Bir marta yozish kafolati |
| Config | `pydantic` + `.env` / `YAML` | Validatsiya, ko'p profil |
| Log | `logging` + `RotatingFileHandler` | Kunlik audit |
| Retry/offline | lokal navbat (SQLite jadvali) | Internet uzilsa yo'qolmaslik |
| Bildirishnoma (ixt.) | Telegram bot | Xatolik/kunlik hisobot |
| Servis (ixt.) | `pywin32` Windows Service / Task Scheduler | Avto-ishga tushish |
| EA (2-faza) | MQL5 `OnTradeTransaction` + `WebRequest` | Event push |

---

## 4. Ma'lumot modeli (Google Sheets / Excel jadval ustunlari)

**`Trades` varaqi (asosiy jurnal):**

| # | Ustun | Namuna | Izoh |
|---|---|---|---|
| 1 | `logged_at` | 2026-09-30T14:05:12+05:00 | Yozilgan vaqt |
| 2 | `account` | 5012345 | MT5 login |
| 3 | `broker` | RoboForex | Server nomi |
| 4 | `position_id` | 987654321 | Unikal (dedup kaliti) |
| 5 | `symbol` | XAUUSD | Instrument |
| 6 | `direction` | BUY | BUY/SELL |
| 7 | `volume` | 0.10 | Lot |
| 8 | `entry_time` | 2026-09-30T12:00:03+05:00 | Kirish vaqti |
| 9 | `entry_price` | 2645.30 | Kirish narxi |
| 10 | `sl` | 2640.00 | Stop Loss |
| 11 | `tp` | 2655.00 | Take Profit |
| 12 | `exit_time` | 2026-09-30T13:10:44+05:00 | Chiqish vaqti |
| 13 | `exit_price` | 2655.00 | Chiqish narxi |
| 14 | `close_reason` | TP | TP/SL/MANUAL/SO |
| 15 | `pips` | +170 | Points/pips |
| 16 | `gross_profit` | 17.00 | Valyutada |
| 17 | `commission` | -0.70 | |
| 18 | `swap` | 0.00 | |
| 19 | `net_pl` | 16.30 | Sof natija |
| 20 | `risk_amount` | 5.30 | SL bo'yicha risk ($) |
| 21 | `r_multiple` | +3.08R | Natija / risk |
| 22 | `duration` | 01:10:41 | Ushlab turish |
| 23 | `balance_after` | 1016.30 | Savdodan keyin |
| 24 | `magic` | 0 | EA magic (0=manual) |
| 25 | `comment` | — | Savdo izohi |
| 26 | `strategy` | Breakout_v5 | Magic/comment'dan aniqlangan |

Qo'shimcha varaqlar: `Open_Positions` (jonli ochiq), `Daily_Summary` (kunlik jamlanma),
`Errors` (xatolik logi), `Config` (o'qish uchun).

---

## 5. Papka tuzilmasi (Project layout)

```
mt5-trade-journal/
├── REJA.md                     # ← shu fayl
├── README.md                   # ishga tushirish yo'riqnomasi
├── requirements.txt
├── .env.example                # namunaviy config (parolsiz)
├── config/
│   ├── users.yaml              # ko'p foydalanuvchi profillari
│   └── credentials/            # google service-account json (git-ignore)
├── src/
│   ├── main.py                 # kirish nuqtasi, scheduler
│   ├── config.py               # pydantic settings, profil yuklash
│   ├── mt5_client.py           # MT5 ulanish, poll, tarix o'qish
│   ├── trade_engine.py         # yangi savdoni aniqlash, dedup, model qurish
│   ├── models.py               # Trade dataclass/pydantic
│   ├── formatters.py           # R-multiple, pips, vaqt, timezone
│   ├── state.py                # SQLite: seen deals, retry queue
│   ├── sinks/
│   │   ├── base.py             # Sink interfeysi
│   │   ├── google_sheets.py    # gspread sink
│   │   ├── excel.py            # openpyxl sink
│   │   └── csv_sink.py         # oddiy CSV fallback
│   ├── analytics.py            # (2-faza) winrate, PF, expectancy...
│   └── notifier.py             # (ixt.) Telegram
├── ea/                         # (2-faza) MQL5 Expert Advisor
│   └── TradeJournalPush.mq5
├── scripts/
│   ├── install_service.ps1     # Windows service/Task Scheduler
│   └── backfill.py             # eski savdolarni bir marta import qilish
├── tests/
│   ├── test_formatters.py
│   ├── test_dedup.py
│   └── test_sinks.py
└── logs/
```

---

## 6. Asosiy logika (senior darajada)

### 6.1 Savdoni aniqlash oqimi (dedup + idempotentlik)
1. Har `POLL_INTERVAL` (masalan 5 s) da:
   - `mt5.history_deals_get(from, to)` — oxirgi N kun / oxirgi belgilangan vaqtdan.
   - `mt5.positions_get()` — hozir ochiq pozitsiyalar.
2. Deal'larni **position_id** bo'yicha guruhlash → bitta savdo (entry deal + exit deal) qurish.
3. Har position_id ni **SQLite `seen`** jadvalidan tekshirish:
   - Agar yopilgan va hali yozilmagan bo'lsa → **Trade** modeli quriladi.
   - `seen` ga yoziladi (dedup — internet qaytsa ham qayta yozilmaydi).
4. Model → formatters (R, pips, duration) → sink(lar)ga uzatiladi.
5. Sink muvaffaqiyatli bo'lsa `seen.written=1`; muvaffaqiyatsiz bo'lsa **retry queue**ga.

> Muhim: dedup kaliti = **position_id** (deal_id emas). Bir pozitsiya ko'p deal'dan iborat
> bo'lishi mumkin (qisman yopish). Qisman yopishlarni to'g'ri jamlaymiz.

### 6.2 R-multiple hisoblash (senior metrika)
- `risk_per_unit = |entry_price - sl|`
- `risk_amount = risk_per_unit * contract_size * volume` (symbol tick value orqali aniq)
- `r_multiple = net_pl / risk_amount` (agar SL bo'lmasa → bo'sh)
- Bu — strategiya sifatini o'lchashning eng muhim metrikasi (pul emas, R'da o'ylash).

### 6.3 Vaqt/timezone
- MT5 vaqti — broker serveri vaqti (odatda UTC+2/+3). Uni **UTC**ga, keyin foydalanuvchi
  timezone'siga (`Asia/Tashkent`, +05:00) o'giramiz. Jadvalda ISO 8601 + offset saqlanadi.

### 6.4 Offline / xatolikka chidamlilik
- Google Sheets API xato bersa (internet, quota) → yozuv retry queue'ga (SQLite).
- Har poll'da queue avval bo'shatiladi (FIFO), keyin yangi savdolar.
- Exponential backoff + jitter. Excel/CSV sink — har doim lokal, internetsiz ham ishlaydi.

### 6.5 Ko'p foydalanuvchi (multi-user)
- `config/users.yaml` da har foydalanuvchi: MT5 login/parol/server, maqsad Sheet ID/varaq,
  timezone, sink turlari.
- Xizmat har profil uchun alohida `mt5_client` sessiyasi ochadi (yoki navbat bilan ulanadi —
  MT5 API bir vaqtda bitta terminal; shuning uchun **profil = alohida MT5 terminal instansiyasi**
  yoki navbatli ulanish). Bir necha odam turli kompyuterda ishlatsa — har kim o'z nusxasini
  o'z config bilan yuritadi (eng oddiy va ishonchli model).
- Ikki model:
  - **A) Tarqoq (tavsiya, MVP):** har trader o'z Windows'ida xizmatni ishlatadi, umumiy
    Google Sheets'ga (yoki har kim o'ziga) yozadi. Oddiy, mustaqil.
  - **B) Markaziy:** bitta server bir nechta hisobni boshqaradi (VPS + har hisob uchun MT5
    terminal). Kuchli, lekin murakkabroq — 3-fazada.

---

## 7. Bosqichlar (Roadmap) — bajarish tartibi

### FAZA 0 — Poydevor (1-kun)
- [ ] `requirements.txt`, `.env.example`, papka skeleti.
- [ ] `mt5_client.py`: MT5 ga ulanish, `terminal_info`, `account_info` sinovi.
- [ ] `state.py`: SQLite sxema (`seen`, `retry_queue`).
- **Natija:** MT5 ga ulanib, hisob ma'lumotini terminalga chiqarish.

### FAZA 1 — MVP: savdo → CSV/Excel (2-kun)
- [ ] `models.py`, `formatters.py` (R, pips, duration, timezone) + testlar.
- [ ] `trade_engine.py`: yopilgan savdolarni aniqlash + dedup.
- [ ] `sinks/csv_sink.py`, `sinks/excel.py`.
- [ ] `main.py`: poll loop.
- **Natija:** manual savdo yopilsa — bir necha soniyada Excel/CSV ga to'g'ri qator tushadi.

### FAZA 2 — Google Sheets + ishonchlilik (2-kun)
- [ ] Service account setup, `sinks/google_sheets.py`.
- [ ] Retry queue + offline chidamlilik.
- [ ] `Open_Positions` jonli varaq.
- [ ] `scripts/backfill.py` — o'tmishdagi savdolarni bir marta import.
- **Natija:** savdolar real-time Google Sheets'da, internet uzilsa ham yo'qolmaydi.

### FAZA 3 — Avtomatik ishga tushish + ko'p foydalanuvchi (1-kun)
- [ ] `config/users.yaml` ko'p profil.
- [ ] `scripts/install_service.ps1` (Task Scheduler/Windows Service).
- [ ] `notifier.py` Telegram (ixtiyoriy).
- **Natija:** kompyuter yonsa xizmat o'zi ishga tushadi; bir nechta odam ishlata oladi.

### FAZA 4 — Optimallashtirish / Analitika (keyinchalik)
- [ ] `analytics.py`: winrate, profit factor, expectancy, avg R, max drawdown,
      strategiya/sessiya/symbol bo'yicha kesim.
- [ ] `Daily_Summary` avto-jamlanma varaq (Sheets formulalari yoki Python).
- [ ] Dashboard (Google Sheets chart yoki alohida web-panel).
- [ ] EA push (`ea/TradeJournalPush.mq5`) — past-latency event yozish.
- [ ] Anomaliya signallari: masalan risksiz (SL yo'q) savdo, katta drawdown ogohlantirishi.

---

## 8. Xavfsizlik va maxfiylik
- MT5 parol, Google credentials — **hech qachon** kodda emas; `.env` + `config/credentials/`
  `.gitignore`'da. Git repo yaratilsa — bular commit qilinmaydi.
- Google: **service account** (foydalanuvchi OAuth emas), faqat kerakli Sheet'ga ulashiladi.
- Loglarda parol/token chop etilmaydi.
- Ko'p foydalanuvchida har kim faqat o'z Sheet'iga yozadi (kirish nazorati Sheets ulashuvida).

## 9. Testlash
- Unit: formatters (R-multiple, pips, timezone), dedup mantiqi, sink yozuvi (mock).
- Integratsiya: MT5 **demo hisob**da real savdo ochib/yopib, jadvalga to'g'ri tushishini tekshirish.
- Chek-ro'yxat: TP bilan yopilish, SL bilan yopilish, manual yopilish, qisman yopilish,
  bir vaqtda 2 pozitsiya, internet uzilishi, terminal restart.

## 10. Ochiq savollar (foydalanuvchidan aniqlash kerak)
1. **Asosiy manzil:** Google Sheets, Excel, yoki ikkalasi? (Tavsiya: ikkalasi — Sheets asosiy, Excel zaxira.)
2. **Broker/server nomi** va MT5 versiyasi? Demo hisob bormi (sinov uchun)?
3. **Timezone** jadvalda qaysi bo'lsin? (Tavsiya: Asia/Tashkent, +05:00.)
4. **Ko'p foydalanuvchi modeli:** tarqoq (A, har kim o'z kompida) yoki markaziy (B, VPS)?
5. **Faqat yopilgan savdolar** yozilsinmi yoki **ochiqlari ham** real-time?
6. **Telegram** bildirishnoma kerakmi (savdo yopildi / xatolik / kunlik hisobot)?
7. O'tmishdagi savdolarni ham import qilaymizmi (backfill)?

---

## 11. Keyingi qadam
Yuqoridagi 10-bo'limdagi savollarga javob berilgach, **FAZA 0 + FAZA 1** ni darhol yozib,
demo hisobda real savdo bilan sinab ko'ramiz — ya'ni bir necha soatda ishlaydigan MVP.

<!-- HOLAT JURNALI (har faza oxirida yangilanadi):
FAZA 0: [ ]  FAZA 1: [ ]  FAZA 2: [ ]  FAZA 3: [ ]  FAZA 4: [ ]
-->
