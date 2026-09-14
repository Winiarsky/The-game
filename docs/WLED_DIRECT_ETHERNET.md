# Bezpośrednie połączenie WLED z komputerem

Konfiguracja zastosowana 2026-09-11. Sterownik Gledopto Elite 4D-EXMU
GL-C-618WL, WLED 16.0.1, 620 LED. Ethernet type = 13, fabrycznie aktywny.

## Podłączenie i uruchomienie

- Kabel Ethernet bezpośrednio komputer → sterownik WLED.
- Dotychczasowy USB komputer → ESP skanujący przyciski.
- Dotychczasowe zasilanie sterownika i LED.
- Uruchomić aplikację. Po migracji trzeba ją ponownie uruchomić, ponieważ
  istniejące połączenie może nadal pamiętać poprzedni adres Wi-Fi.

Router i internet nie są potrzebne do komunikacji z planszą. Wi-Fi komputera
może służyć niezależnie do internetu.

## Zapisane ustawienia

| Urządzenie | Adres | Maska | Brama |
| --- | --- | --- | --- |
| Komputer, enp2s0 | 192.168.50.1 | 255.255.255.0 | brak |
| WLED | 192.168.50.2 | 255.255.255.0 | 192.168.50.1 |

Profil NetworkManager: `Plansza-WLED`, UUID
`eac55d2f-c66e-49f0-b1d7-1f377717b657`, IPv4 manual, never-default,
IPv6 disabled, autoconnect, autoconnect-priority 20. Profil jest przeznaczony
do kabla planszy; przy użyciu tego portu do zwykłej sieci wybrać poprzedni
profil `Wired connection 1`.

W `board/config.json` ustawiono `wled.base_url = http://192.168.50.2`.
Panel WLED: <http://192.168.50.2>.

Po późniejszych timeoutach wyłączono łączenie sterownika z domowym Wi-Fi:
wyczyszczono zapisane SSID przez formularz `/settings/wifi`. JSON API nie
nadaje się do tej operacji, ponieważ ignoruje puste SSID. Hasło, ustawienia
awaryjnego hotspotu, Ethernetu oraz konfiguracja LED zostały zachowane.
Po restarcie firmware 16.0.1 pokazuje domyślne `Your_Network` zamiast pustego
SSID; poprzednia nazwa sieci nie wraca, a BSSID pozostaje pusty (brak
połączenia Wi-Fi). Wi-Fi komputera nadal obsługuje internet.

WLED wymaga **niezerowej bramy** do zastosowania statycznego adresu Ethernet.
Przy `0.0.0.0` urządzenie w tej próbie używało DHCP mimo zapisanego stałego IP.
Po uzupełnieniu bramy i restarcie zgłosiło się pod stałym adresem.
Komputer nie musi udostępniać internetu: brama jest wymogiem konfiguracji
firmware'u, a ruch aplikacji pozostaje w lokalnej podsieci.

Podczas odzyskiwania dostępu chwilowo użyto profilu IPv4 shared; na końcu
przywrócono manual, wyłączając serwer DHCP/udostępnianie tego profilu.
Nie zmieniano firmware'u, ustawień LED ani skanera USB.

## Weryfikacja

- `ip route get 192.168.50.2`: enp2s0, źródło 192.168.50.1.
- Domyślna trasa internetu nadal przez Wi-Fi wlp3s0.
- WLED odpowiada po restarcie i po wyłączeniu tymczasowego DHCP.
- Klient `_WledClient` aplikacji: 10 GET `/json/info`, mediana 17,2 ms,
  maksimum 19,2 ms; 10 POST `/json/state` z tą samą jasnością,
  mediana 10,8 ms, maksimum 14,0 ms. Wszystkie żądania poprawne.
- Pomiar dotyczy odpowiedzi HTTP, nie czasu od naciśnięcia do fizycznego
  zapalenia LED. Pełna próba samouczka i zimnego startu pozostaje do wykonania.

### Ponowna weryfikacja po wyłączeniu klienta Wi-Fi, 2026-09-11

Przed zmianą ping po Ethernet wynosił około 1 ms bez utraty pakietów,
ale HTTP przekraczał limit 2 s; panel nie otwierał się lub pobierał częściowo.
Po usunięciu SSID wykonano 10 GET `/json/info` i 10 POST `/json/state`
z dotychczasową jasnością, a następnie powtórzono próbę po programowym restarcie.
Wszystkie 40 żądań zakończyło się poprawnie. Po restarcie: GET mediana
14,05 ms, maksimum 16,2 ms; POST mediana 10,15 ms, maksimum 11,2 ms.
Cały panel HTTP 200 pobrał się w 37,5 ms. Porównanie konfiguracji potwierdziło
zachowanie ustawień LED, hotspotu, adresu i bramy Ethernetu oraz typu 13.
Tymczasowy dodatkowy adres Wi-Fi komputera użyty do odzyskania dostępu został
usunięty, profil `Plansza-WLED` przywrócony. Test odłączenia zasilania i pełnej
gry pozostaje osobną próbą sprzętową.

## Powrót do poprzedniego połączenia

Poprzednio WLED pobierał adres z DHCP przez Wi-Fi (ostatnio 192.168.0.165).
SSID usunięto podczas diagnozowania timeoutów; hasło zachowano. Aby przywrócić
Wi-Fi, wpisać nazwę domowej sieci. Dla DHCP w panelu WLED ustawić
Static IP = 0.0.0.0, gateway = 0.0.0.0, subnet = 255.255.255.0 i zapisać.
Po ponownym połączeniu sprawdzić przydzielony adres i wpisać go w konfiguracji
aplikacji. Ustawienie adresu WLED jest wspólne dla Wi-Fi i Ethernetu.

Źródła: [GL-C-618WL](https://gledopto.com/h-pd-64.html),
[ustawienia WLED](https://kno.wled.ge/features/settings/),
[warunek inicjalizacji Ethernetu](https://github.com/wled/WLED/blob/main/wled00/network.cpp).
