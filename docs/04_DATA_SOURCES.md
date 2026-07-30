# 04 — Veri Kaynakları

## 1. Amaç

Bu belge, AI_BIST_Research sisteminde kullanılacak veri türlerini ve kaynak seçim kurallarını tanımlar.

## 2. Kaynak önceliği

Veri kaynakları aşağıdaki güven sırasına göre değerlendirilir:

1. KAP ve diğer resmî kurum açıklamaları
2. Şirketlerin yatırımcı ilişkileri sayfaları
3. Borsa ve yetkili finansal veri sağlayıcıları
4. Güvenilir ulusal ve uluslararası haber ajansları
5. Güvenilir ekonomi ve finans basını
6. İkincil veri platformları
7. Sosyal medya ve yatırım forumları

Sosyal medya ve forum bilgileri doğrulanmış haber olarak kullanılmaz.

## 3. Kullanılacak veri türleri

- Hisse fiyatları
- İşlem hacmi
- BIST 100 ve sektör endeksleri
- Şirket finansal tabloları
- KAP açıklamaları
- Son 30 günlük şirket haberleri
- Faiz ve enflasyon verileri
- Döviz kurları
- CDS ve tahvil faizleri
- Petrol, altın ve sektöre bağlı emtialar
- Temettü ve sermaye artırımı bilgileri
- Uygun olduğunda yabancı yatırımcı ve fon hareketleri

## 4. Veri kalitesi kuralları

Her veri için mümkün olduğunda şunlar bulunmalıdır:

- Kaynak
- Yayın tarihi
- Veri tarihi
- Güncellenme zamanı
- Para birimi
- Dönem bilgisi

Eksik veri sıfır olarak kabul edilmez. Eksik alanlar açıkça belirtilir.

## 5. Haber doğrulama

- Aynı haberin farklı sitelerdeki kopyaları tek olay olarak değerlendirilir.
- Birincil kaynak varsa öncelikle o kullanılır.
- Söylentiler ayrı olarak işaretlenir.
- Çelişkili haberler kullanıcıya bildirilir.
- Haber başlığı tek başına karar vermek için yeterli değildir.
- Son üç gündeki haberler daha yüksek zaman ağırlığı alabilir.

## 6. Veri güncelliği

- Fiyat verisi: Son işlem günü
- Teknik analiz verisi: Son işlem günü veya kullanılan zaman dilimi
- Haberler: Son 30 gün
- Finansal tablolar: Son açıklanan dönem
- Makroekonomik veriler: Son yayımlanan değer
- Sektör verileri: Günlük, haftalık ve aylık

## 7. Lisans ve kullanım koşulları

Bir veri kaynağı sisteme eklenmeden önce aşağıdakiler kontrol edilmelidir:

- Ücretsiz veya ücretli olması
- API erişiminin bulunması
- Kullanım limiti
- Ticari kullanım şartları
- Verinin saklanmasına izin verilip verilmediği
- Kaynak gösterme zorunluluğu

Üretim aşamasında kullanım şartları doğrulanmamış kaynaklar kullanılmamalıdır.
