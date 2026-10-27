# Öğrenme notları

Bu repoyu kurarken çalıştığım kavramlar, denediklerim ve mülakat için hazırladığım cümleler.

## 1. MQTT temelleri

- **Pub/sub:** Gönderen ve alıcı birbirini tanımaz, ikisi de sadece broker'ı tanır. Buluta yeni
  bir tüketici eklemek sahadaki cihazlara dokunmayı gerektirmez.
- **Topic:** `site/ludvika/station1/transformer3/temperature`. `+` tek seviyeyi, `#` altındaki her şeyi yakalar.
- **client_id benzersiz olmalı.** Aynı ID ile ikinci bir client bağlanırsa broker ilkini atar.
- **Payload'a MQTT karışmaz.** Zaman damgası cihazda basılır.

Deney: `demos/basic_publisher.py` + `demos/basic_subscriber.py`

## 2. Retained message: "son bilinen değer"

Broker her topic için **son** retained mesajı saklar ve yeni abone bağlanır bağlanmaz ona verir.
Durum bilgisi (online/offline, kademe, kesici durumu) için kullanılır; akış halindeki ölçümler için kullanılmaz.
Silmek için boş bir retained mesaj gönderilir: `mosquitto_pub -t <topic> -r -n`.

Broker retained mesajları RAM'de tutar. `persistence true` ise kapanışta ve `autosave_interval`
aralıklarıyla (varsayılan 30 dk) diske (`mosquitto.db`) yazar; ani çökmede son kayıttan sonrası kaybolabilir.

Deney: `demos/retained.py`

```powershell
docker exec mosquitto mosquitto_pub -t "test/kademe" -m "7" -r
docker exec -it mosquitto mosquitto_sub -t "test/#" -v
```

## 3. Last Will: "cihaz öldü" alarmı

Cihaz bağlanırken broker'a bir vasiyet bırakır. Beklenmedik bir kopuşta broker bu mesajı cihazın adına yayınlar.
- Düzgün `disconnect()` yapılırsa Will **tetiklenmez**.
- Elektrik kesintisinde TCP bağlantısı kapanmaz; broker kopuşu ancak **1,5 × keepalive** süre sessizlikten sonra anlar.
- Standart kalıp: bağlanınca `status=online` (retained), Will olarak `status=offline` (retained).

Broker logunda fark: `Received DISCONNECT` (düzgün kapanış) / `closed its connection` (ani kopuş, Will yayınlanır).

Deney: `demos/last_will.py`

```powershell
docker exec -it mosquitto mosquitto_sub -t "bos" -i cihaz1 -k 10 --will-topic "test/status" --will-payload "offline" --will-retain
docker exec mosquitto pkill -9 -f cihaz1
```

## 4. QoS ve kalıcı oturum

| QoS | Garanti | Kullanım |
|---|---|---|
| 0 | En fazla bir kez | Yüksek frekanslı telemetri |
| 1 | En az bir kez (tekrar gelebilir) | Alarm, olay. En yaygın seçim |
| 2 | Tam olarak bir kez (4 adımlı el sıkışma) | Komutlar |

- Gerçekleşen QoS = **min**(gönderenin QoS'u, abonenin QoS'u).
- Broker'ın çevrimdışı bir abone için mesaj biriktirmesi için üç şart gerekir: sabit `client_id`, `clean_session=False` ve QoS ≥ 1.
- QoS 1 tekrar üretebilir, bu yüzden tüketici **idempotent** olmalı.
- Kalıcı oturumların süresi varsayılan olarak hiç dolmaz; `persistent_client_expiration` ile sınırlanır.

Deney: `demos/persistent_session.py`

## 5. MQTT ve RabbitMQ

İkisi de broker'dır. MQTT kısıtlı cihazlar ve güvenilmez ağlar için tasarlanmış, yayın (fan-out) odaklıdır.
RabbitMQ (AMQP) ise exchange/queue yapısıyla sunucular arası iş dağıtımı için kullanılır.
Gerçek mimaride ikisi birlikte bulunur: sahadan buluta MQTT, bulutun içinde RabbitMQ veya Kafka.

## 6. OPC UA

- Cihaz **server**, gateway **client**'tır. Bağlantı broker'sız ve doğrudandır: `opc.tcp://host:4840`.
- **Address space:** cihaz kendini bir node ağacı olarak tarif eder. Her node'un bir NodeId'si vardır,
  örneğin `ns=2;s=Transformer3.Temperature`. Namespace 0 ve 1 standarda ayrılmıştır.
- Bir okuma 3 şey döndürür: **Value**, **SourceTimestamp** ve **StatusCode** (Good/Bad/Uncertain).
  Kaliteye bakmadan değere güvenilmez.
- Üç temel işlem: **Browse**, **Read** ve **Subscribe**. Subscribe, değişiklik olduğunda bildirim gönderir; polling'e göre çok daha verimlidir.
- Güvenlik sertifika tabanlıdır. Sahada en sık görülen sorun, sertifikanın "rejected" klasörüne düşmesidir.

### Alıştırma: kendi client'ını yaz (`client.py`)

`python plc_simulator/opcua_server.py` çalışırken:
1. `ns=2;s=Transformer3.Temperature` node'unu oku; değeri, zaman damgasını ve kaliteyi yazdır.
2. `ns=2;s=Transformer3` altındaki tüm değişkenleri `get_children()` ile listele.
3. `create_subscription(500, Handler())` + `subscribe_data_change(...)` ile değişiklikleri dinle.
   Ek soru: TapPosition'a abone olunca neden bildirim gelmiyor?

## 7. Gateway: store-and-forward

Veri yolu: OPC UA değişikliği → SQLite tamponu → MQTT (QoS 1). Bir satır, ancak broker PUBACK gönderdikten sonra silinir.
- Bağlantı kopunca veri diskte birikir; bağlantı gelince sırayla gönderilir.
- Disk dolarsa en eski veri atılır.
- `gateway/status` gateway'in ayakta olup olmadığını, `gateway/opcua` PLC'ye ulaşıp ulaşamadığını söyler.
  İkisi birlikte "sorun bizde mi, karşı tarafta mı?" sorusunu cevaplar.

## Mülakat cümleleri

> MQTT, publish/subscribe modeliyle göndericiyi ve alıcıyı birbirinden ayırır. Edge cihaz sadece broker'ı bilir,
> bu yüzden bulut tarafına yeni tüketiciler eklemek sahadaki konfigürasyona dokunmayı gerektirmez.

> Edge cihazlarda Last Will ile retained status birlikte kullanılır. Telemetri için QoS 0 yeterli olabilir,
> alarmlar için QoS 1 ve kalıcı oturum kullanılır. QoS 1 tekrar üretebileceği için tüketici idempotent olmalıdır.

> Broker'ın kuyruğu tüketici tarafındaki kesintiyi çözer. Edge ile broker arasındaki bağlantı koparsa
> veriyi edge'in kendisi diskte biriktirmelidir. Ben bunu SQLite tabanlı bir FIFO ile yaptım ve
> broker'ı durdurup tekrar başlatarak kayıp olmadığını doğruladım.

> OPC UA cihazla konuşmak için, MQTT veriyi taşımak için. Edge'de OPC UA subscription ile değişiklikler okunur,
> cihazın zaman damgası ve kalite bilgisiyle birlikte MQTT'ye köprülenir.
