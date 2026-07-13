# RG_V3 Market Data Model

This document outlines the standard contracts and parameters governing advanced market data adapter classes in **Phase 24 Real Market Data Intelligence Adapter Layer**.

---

## 1. MT5 Market Ingestion Models

### MarketInstrument
Core trading instrument definitions:
*   `symbol`: `str` (e.g. `"EURUSD"`)
*   `asset_class`: `str` (e.g. `"FX"`, `"Crypto"`, `"Equities"`)
*   `digits`: `int` (default `5`)
*   `contract_size`: `float` (default `100000.0`)
*   `tick_size`: `float` (default `0.00001`)
*   `description`: `str`

### CandleRecord
Uniform historical or snapshot candle:
*   `timestamp`: `datetime`
*   `open`: `float`
*   `high`: `float`
*   `low`: `float`
*   `close`: `float`
*   `volume`: `float`

### MarketDataMetadata
Chronological and latency metadata:
*   `provider_id`: `str`
*   `retrieved_at`: `datetime`
*   `latency_ms`: `float`
*   `additional_properties`: `Dict[str, Any]`

---

## 2. Macroeconomic & News Feeds Models

### EconomicCalendarRecord
 Macroeconomic fact log:
*   `event_id`: `str`
*   `name`: `str`
*   `country`: `str`
*   `timestamp`: `datetime`
*   `impact`: `str` (Low, Medium, High)
*   `actual`: `float`
*   `previous`: `float`
*   `expected`: `float`

### NewsRecord
Passive text article:
*   `article_id`: `str`
*   `headline`: `str`
*   `timestamp`: `datetime`
*   `category`: `str`
*   `summary`: `str`
*   `meta`: `NewsMetadata`

---

## 3. Provider Health Score Formulation

Provider health is evaluated dynamically across chronological availability and response speed dimensions:

$$\text{Health Rating} = \text{Availability} \cdot \left(1.0 - \frac{\text{Ping}_{\text{ms}}}{500.0}\right) \cdot (1.0 - \text{Error Rate})$$

*   If `Availability` equals $0.0$, the provider is marked `UNHEALTHY`.
*   If `Ping` exceeds $100.0$ ms, the provider is marked `DEGRADED`.
*   Otherwise, the provider is `HEALTHY`.
