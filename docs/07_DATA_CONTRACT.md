# 07 — Veri Sözleşmesi

## 1. Amaç

Bu belge, AI_BIST_Research sistemindeki modüllerin birbirleriyle hangi veri formatında iletişim kuracağını tanımlar.

Sistem içinde temel veri aktarım formatı JSON olacaktır.

## 2. Temel kurallar

- Her analiz çalışmasının benzersiz bir kimliği bulunmalıdır.
- Her veri için kaynak ve tarih bilgisi tutulmalıdır.
- Eksik veriler sıfır olarak değil, `null` olarak saklanmalıdır.
- Hisse kodları büyük harfle yazılmalıdır.
- Tarihler ISO 8601 formatında tutulmalıdır.
- Puanlar 0 ile 100 arasında olmalıdır.
- Para birimi açıkça belirtilmelidir.
- Eski veya güvenilirliği düşük veriler işaretlenmelidir.

## 3. Ana analiz yapısı

```json
{
  "run_id": "20260730-143000",
  "analysis_date": "2026-07-30T14:30:00+03:00",
  "market": "BIST",
  "market_regime": {},
  "stocks": [],
  "warnings": [],
  "errors": []
}
```
## 4. Piyasa rejimi yapısı

```json
{
  "regime": "BULL",
  "confidence_score": 78,
  "bist100_trend": "POSITIVE",
  "volatility_level": "MEDIUM",
  "market_breadth": "POSITIVE",
  "risk_appetite": "MEDIUM",
  "reasons": []
}
```

## 5. Hisse analiz yapısı

```json
{
  "symbol": "THYAO",
  "company_name": "Türk Hava Yolları",
  "sector": "Ulaştırma",
  "currency": "TRY",
  "last_price": null,
  "price_date": null,
  "data_quality": {},
  "technical": {},
  "fundamental": {},
  "news_and_kap": {},
  "macro": {},
  "sector_analysis": {},
  "institutional_flow": {},
  "risk": {},
  "score": {},
  "decision": {}
}
```

## 6. Veri kalitesi yapısı

```json
{
  "quality_score": 90,
  "price_data_available": true,
  "financial_data_available": true,
  "news_data_available": true,
  "kap_data_available": true,
  "is_data_current": true,
  "missing_fields": [],
  "warnings": []
}
```

## 7. Teknik analiz yapısı

```json
{
  "technical_score": 82,
  "trend_score": 85,
  "momentum_score": 78,
  "volume_score": 75,
  "volatility_score": 70,
  "rsi": null,
  "macd": null,
  "ema": {},
  "bollinger": {},
  "atr": null,
  "adx": null,
  "relative_volume": null,
  "support_levels": [],
  "resistance_levels": [],
  "signals": [],
  "warnings": []
}
```

## 8. Temel analiz yapısı

```json
{
  "fundamental_score": 76,
  "growth_score": null,
  "profitability_score": null,
  "debt_score": null,
  "cash_flow_score": null,
  "valuation_score": null,
  "dividend_score": null,
  "financial_period": null,
  "strengths": [],
  "weaknesses": [],
  "warnings": []
}
```

## 9. Haber ve KAP yapısı

```json
{
  "news_score": 80,
  "sentiment": "POSITIVE",
  "confidence_score": 85,
  "news_count": 0,
  "kap_count": 0,
  "important_events": [],
  "rumors": [],
  "duplicate_news_removed": 0,
  "sources": [],
  "warnings": []
}
```

## 10. Risk yapısı

```json
{
  "risk_level": "MEDIUM",
  "risk_score": 65,
  "risk_multiplier": 0.92,
  "liquidity_risk": "LOW",
  "volatility_risk": "MEDIUM",
  "news_risk": "LOW",
  "data_risk": "LOW",
  "hard_block": false,
  "block_reasons": [],
  "warnings": []
}
```

## 11. Puanlama yapısı

```json
{
  "technical": 0,
  "fundamental": 0,
  "news_and_kap": 0,
  "macroeconomic": 0,
  "sector": 0,
  "institutional_flow": 0,
  "ai_synthesis": 0,
  "risk": 0,
  "raw_score": 0,
  "final_score": 0
}
```

## 12. Karar yapısı

```json
{
  "rating": "HOLD",
  "confidence_score": 75,
  "investment_horizon": "1-3_MONTHS",
  "entry_zone": {},
  "target_scenarios": [],
  "stop_loss": {},
  "risk_reward_ratio": null,
  "bull_case": {},
  "base_case": {},
  "bear_case": {},
  "counter_thesis": [],
  "invalidating_conditions": []
}
```
Kullanılabilecek kararlar:

- `STRONG_BUY`
- `BUY`
- `HOLD`
- `SELL`
- `STRONG_SELL`
- `NO_ACTION`

## 13. Hata ve uyarılar

Sistem sessizce başarısız olmamalıdır.

Hatalar aşağıdaki yapıyla kaydedilmelidir:
```json
{
  "module": "technical_analysis",
  "symbol": "THYAO",
  "error_code": "MISSING_PRICE_DATA",
  "message": "Teknik analiz için yeterli fiyat verisi bulunamadı.",
  "timestamp": "2026-07-30T14:30:00+03:00"
}
```
