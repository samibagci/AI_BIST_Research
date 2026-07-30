# 01 — Proje Kapsamı

## 1. Projenin amacı

AI_BIST_Research, Borsa İstanbul hisselerini farklı veri türleriyle analiz eden bir yatırım araştırma ve karar destek sistemi geliştirmeyi amaçlar.

Sistem aşağıdaki verileri birlikte değerlendirecektir:

- Fiyat ve işlem hacmi verileri
- Teknik göstergeler
- Şirket finansal tabloları
- KAP açıklamaları
- Son 30 günlük haber akışı
- Makroekonomik göstergeler
- Sektör ve endeks görünümü
- Likidite ve volatilite riskleri

## 2. Hedef kullanıcı

İlk sürüm aşağıdaki kullanıcı profiline göre tasarlanacaktır:

- BIST hisselerine yatırım yapan bireysel yatırımcı
- Düşük risk profili
- 1–3 aylık yatırım vadesi
- Günlük en fazla 5 hisse önerisi isteyen kullanıcı

## 3. Sistemin temel görevleri

Sistem:

1. BIST hisselerini analiz eder.
2. Likiditesi düşük hisseleri eler.
3. Son 30 günlük haberleri değerlendirir.
4. KAP açıklamalarını inceler.
5. Teknik analiz sonuçlarını değerlendirir.
6. Temel analiz yapar.
7. Makroekonomik ve sektörel etkileri inceler.
8. Her hisseye 100 üzerinden puan verir.
9. En fazla 5 hisseyi sıralar.
10. GÜÇLÜ AL, AL, TUT, SAT veya GÜÇLÜ SAT sonucu üretir.
11. Her kararın gerekçesini ve risklerini açıklar.
12. İlerleyen sürümlerde günlük raporu e-posta ile gönderir.

## 4. İlk sürümde yapılmayacaklar

İlk sürümde sistem:

- Otomatik alım veya satım emri göndermez.
- Aracı kurum hesabına bağlanmaz.
- Kullanıcı onayı olmadan portföy değiştirmez.
- Kesin getiri veya garanti kazanç vaat etmez.
- Kaynaksız fiyat ve finansal veri üretmez.
- Sosyal medya söylentilerini doğrulanmış haber gibi kullanmaz.

## 5. Temel çalışma prensipleri

- Teknik göstergeler Python tarafından hesaplanacaktır.
- GPT teknik göstergeleri hesaplamak yerine yorumlayacaktır.
- Güncel bilgiler kaynaklandırılacaktır.
- Eksik veriler açıkça belirtilecektir.
- Kritik veri eksikse hisse önerilmeyecektir.
- Yüksek puan, kritik riski geçersiz kılmayacaktır.
- Nakit veya işlem yapmama kararı geçerli bir sonuç olacaktır.
- Her olumlu görüşün karşı tezi de yazılacaktır.

## 6. İlk sürümün başarı kriterleri

İlk çalışan sürüm:

- Aynı veriyle aynı teknik sonuçları üretmelidir.
- Eksik veriyi açıkça göstermelidir.
- En fazla 5 hisse önermelidir.
- Her öneriye risk seviyesi eklemelidir.
- Her hisse için olumlu ve olumsuz senaryo sunmalıdır.
- Güncel iddiaları kaynaklarla desteklemelidir.
- Standart bir rapor formatı kullanmalıdır.
- Hataları kaydetmeli ve sessizce başarısız olmamalıdır.

## 7. Donanım ve teknik sınırlar

- Sistem düşük donanımlı bir Windows bilgisayarda çalışabilmelidir.
- Güçlü bir ekran kartına ihtiyaç duymamalıdır.
- Yapay zekâ işlemleri gerektiğinde bulut API üzerinden yapılabilir.
- Teknik hesaplamalar yerel bilgisayarda Python ile yapılacaktır.
- İlk aşamada ücretsiz veya düşük maliyetli veri kaynakları tercih edilecektir.

## 8. Sorumluluk sınırı

Bu proje bir yatırım araştırma ve karar destek sistemidir.

Üretilen çıktılar kesin getiri garantisi veya kişiye özel lisanslı yatırım danışmanlığı olarak değerlendirilmemelidir. Nihai yatırım kararı kullanıcıya aittir.
