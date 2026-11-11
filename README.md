# Varşova ↔ İstanbul Bilet Takibi

Varşova ile İstanbul arasındaki THY, LOT ve Pegasus biletlerini her sabah kontrol eden küçük bir site.
En ucuz gidiş-dönüşü, fiyat geçmişini ve hangi günün daha ucuz olduğunu grafiklerle gösterir.

- Fiyatlar her sabah GitHub Actions ile Google Flights'tan otomatik çekilir ve `data/history.json` dosyasına eklenir.
- Site GitHub Pages üzerinden yayınlanır. Ücretsizdir, API anahtarı gerekmez.
- Fiyatlar tek kişi içindir ve bagaj içermeyebilir. Satın almadan önce sitedeki "Bak" düğmesiyle güncel fiyata bakın.

## Ayarlar (`config.json`)

| Alan | Ne işe yarar |
|---|---|
| `outbound_dates`, `return_dates` | Taranan gidiş ve dönüş tarih aralıkları |
| `origins`, `destinations` | Havalimanları (WAW; IST ve SAW) |
| `airlines` | Takip edilen havayolları |
| `min_stay_days`, `max_stay_days` | Gidiş-dönüş için en az ve en çok kalış günü |

## Kurulum

1. **Settings → Pages**: Source olarak *Deploy from a branch*, branch olarak `main` / `(root)` seçin.
2. **Actions → Günlük fiyat kontrolü → Run workflow** ile ilk fiyatları çekin.
   Bundan sonra her sabah kendiliğinden çalışır.

## Bilgisayarda çalıştırma

```bash
pip install -r requirements.txt
python scripts/fetch.py   # fiyatları çek
python serve.py           # http://localhost:8765
```
