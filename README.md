# AI_BIST_Research

Borsa İstanbul hisselerini teknik analiz, temel analiz, haber ve KAP akışı, makroekonomi, sektör görünümü ve risk yönetimi açısından değerlendiren yapay zekâ destekli yatırım araştırma sistemi.

## Projenin amacı

Sistem aşağıdaki işlemleri gerçekleştirmeyi hedefler:

- BIST hisselerini analiz etmek
- Likiditesi düşük hisseleri elemek
- Son 30 günlük haber ve KAP akışını incelemek
- Teknik göstergeleri Python ile hesaplamak
- Temel ve makroekonomik analiz yapmak
- Hisseleri 100 puan üzerinden değerlendirmek
- En fazla 5 hisseyi sıralamak
- GÜÇLÜ AL, AL, TUT, SAT veya GÜÇLÜ SAT sonucu üretmek
- Riskleri, hedef senaryolarını ve stop seviyelerini açıklamak
- Günlük raporları ilerleyen sürümlerde e-posta ile göndermek

## Temel çalışma prensibi

Sayısal hesaplamalar Python tarafından yapılacaktır.

GPT aşağıdaki görevleri üstlenecektir:

- Haberleri yorumlamak
- KAP açıklamalarını değerlendirmek
- Teknik ve temel sinyalleri birleştirmek
- Çelişkileri açıklamak
- Olumlu ve olumsuz senaryolar oluşturmak
- Nihai araştırma raporunu hazırlamak

## Proje yapısı

```text
AI_BIST_Research/
├── config/
├── docs/
├── prompts/
├── reports/
├── src/
├── tests/
├── .gitignore
└── README.md

## Kullanım

### 1. Sanal ortamı etkinleştirme

PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2. Paketleri kurma

```powershell
python -m pip install -r requirements.txt
```

### 3. Tam analiz işlemini çalıştırma

`config/bist_watchlist.txt` dosyasındaki hisseleri analiz etmek için:

```powershell
python src/run_full_analysis.py --period 1y
```

Belirli hisseleri analiz etmek için:

```powershell
python src/run_full_analysis.py THYAO ASELS TUPRS --period 1y
```

### 4. İzleme listesi

Analiz edilecek hisseler şu dosyada tutulur:

```text
config/bist_watchlist.txt
```

Her satıra bir BIST hisse kodu yazılabilir:

```text
THYAO
ASELS
TUPRS
KCHOL
SISE
```

### 5. Çıktılar

Analiz sonucunda aşağıdaki dosyalar oluşturulur:

```text
reports/bist_batch_analysis.json
reports/bist_batch_analysis.md
reports/bist_candidates.json
reports/bist_candidates.md
```

İndirilen fiyat verileri şu klasörde saklanır:

```text
data/prices/
```

### 6. Testler

Tüm testleri çalıştırmak için:

```powershell
python -m pytest -q
```

> Sistem yalnızca araştırma ve teknik analiz amacıyla geliştirilmiştir. Üretilen sonuçlar yatırım tavsiyesi değildir.