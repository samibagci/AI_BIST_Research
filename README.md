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
