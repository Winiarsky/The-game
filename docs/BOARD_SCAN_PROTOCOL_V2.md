# Protokół skanera planszy v2

Data: 2026-09-10. Kontrakt wdrożony w firmware `board_scan_protocol_v2_2`
i aplikacji (`board/serial_v2.py`, adapter gry i panel przeglądarki).
Obsługujemy wyłącznie v2; usunięto zgodność ze starym protokołem.
Testy fizycznych naciśnięć w scenariuszu i arenie pozostają do wykonania.
[Raport wdrożenia](BOARD_FIRMWARE_DEPLOYMENT.md),
[README skanera](../future/board_20x30_usb_wled_test/README.md).
Zastępuje propozycję skanowania tła z [audytu](BOARD_SCAN_PROTOCOL_REVIEW.md).

## Decyzje

- ESP skanuje wyłącznie aktywne pola. Nie skanuje tła i nie wysyła
  `rejected_press`. W odczytanym banku ignoruje bity spoza maski.
- Aplikacja określa maskę, znaczenie pól i legalność działania. ESP obsługuje
  wyłącznie wejście: filtrowanie styków, kontekst, zdarzenia i zakończenie.
- Jeden kontekst może obsłużyć jeden wybór albo wiele naciśnięć. Zmiana
  wyniku tej samej kości nie powoduje kolejnej komendy uzbrojenia.
- Osobna maska pól kończących pozwala zatrzymać wejście natychmiast na ESP,
  np. po ✓, bez czekania na przeglądarkę.
- Brak aktywności gracza nie jest awarią. Łączność ma własny mechanizm kontroli.
- WLED pozostaje osobnym transportem. Reguły D&D nie trafiają do firmware.

## Transport i ramki

USB serial, 115200 baud, 8N1 jak w obecnym szkicu. Jedna wiadomość JSON na
linię zakończoną LF; dopuszczalne CRLF. Limit 2048 bajtów bez zakończenia
linii w obu kierunkach, stałe bufory i ograniczona głębokość parsera.
Nie dodajemy własnego protokołu binarnego ani automatycznego zwiększania baud.

Wyjątek to dokładne `PING\n` do bezpiecznego wykrycia wersji. ESP v2 zwraca
`info` z `protocol: "board_scan_usb_v2"`, `v: 2`, wersją firmware, `boot`,
wymiarami, `mapping_id`, stanem czujników i limitami. To polecenie nie zmienia
sesji ani wejścia. Host akceptuje tylko info v2. Stare firmware powoduje
czytelny błąd wymaganej aktualizacji, bez przejścia na inny protokół.
Tekstowe SCAN, SCAN_ONCE, ARM, STOP, CANCEL, STATUS i INFO są odrzucane.
Pozostawiony tekstowy PING służy wyłącznie wykrywaniu urządzenia v2.

Wszystkie wiadomości JSON mają `v: 2` oraz `type`. Po HELLO obie strony
przesyłają także `boot` i `session`; komunikaty kontekstu mają `context`.
`boot` jest nowym 16-znakowym identyfikatorem hex przy każdym restarcie ESP,
`session` takim samym identyfikatorem losowanym przez host przy połączeniu.
Służą korelacji wiadomości, nie uwierzytelnianiu.

Współrzędne są zawsze zerowane: `col` 0–19, `row` 0–29. Pola liczbowe
wymagają liczb całkowitych, bez bool, ułamków i konwersji tekstu. Nieznane
komendy, zduplikowane klucze i nadmiarowe pola komend są błędem. Host może
ignorować dodatkowe pola diagnostyczne odpowiedzi po sprawdzeniu schematu.
Przepełnioną linię odrzucamy w całości aż do LF. Urwany fragment odrzucamy
po 1 s bez kolejnego bajtu; jego późniejszą końcówkę ignorujemy aż do LF.
Nie wykonujemy końcówek wiadomości ani dopasowań fragmentów nazw komend.

Parser firmware przyjmuje ścisły podzbiór JSON używany w komendach: obiekty,
tablice, liczby uint32 i zwykłe ciągi ASCII bez sekwencji escape. Nie wymaga
dodatkowej biblioteki. Limit to 192 tokeny i trzy poziomy zagnieżdżenia pod
korzeniem; pełne maski mask/finish mieszczą się w tych limitach. Retransmisja
komendy zachowuje identyczne bajty, łącznie z kolejnością kluczy i odstępami.

## Komendy i odpowiedzi

| Host → ESP | ESP → host | Znaczenie |
|---|---|---|
| `HELLO` | `hello` | Otwarcie sesji dla rozpoznanego boot, sprawdzenie wersji, mapowania, gotowości i limitów |
| `SET_INPUT` | `input_set` | Atomowe zastąpienie kontekstu, maski, trybu i pól kończących |
| — | `input_ready` | Aktywne styki zostały zwolnione; skaner może przyjąć świeże naciśnięcie |
| — | `press` | Jedno odfiltrowane naciśnięcie z numerem zdarzenia |
| `ACK` | — | Potwierdzenie odebrania kolejnych zdarzeń konkretnego kontekstu |
| `STOP` | `stopped` | Zatrzymanie wskazanego kontekstu, bez naruszania nowszego |
| `PING` (JSON) | `status` | Kontrola łączności i bieżący stan; nie przerywa skanowania |
| — | `error` / `fault` | Błąd komendy / awaria wejścia wymagająca zatrzymania |

HELLO, SET_INPUT, STOP i JSON PING mają `id`: rosnącą liczbę całkowitą
1…2³²−1 w obrębie sesji. Odpowiedź powtarza `id`. Host utrzymuje najwyżej
jedną oczekującą komendę; ACK nie zajmuje tego miejsca i nie ma `id`.
Ponowienie ostatniej komendy z tym samym ID i identyczną treścią zwraca
zapamiętaną odpowiedź, bez ponownego uzbrojenia. Inna treść dla tego ID to
`id_conflict`, mniejsze ID to `stale_request`; bez zmiany wejścia. ESP
przechowuje ostatnią komendę i odpowiedź w ograniczonym buforze.

HELLO zawiera rozpoznany `boot` i nową `session`. Nowa sesja zatrzymuje
wejście, usuwa stare zdarzenia i zaczyna od ID 1. Ponowienie HELLO tej samej
sesji podlega regule ID i nie resetuje skanera. Nieznany/stary boot jest
odrzucany. Dopiero `hello` ze stanem czujników `ready` uprawnia do SET_INPUT;
samo uruchomienie procesora nie oznacza gotowości planszy.

## Kontekst, maski i tryby

`context` to rosnąca liczba 1…2³²−1 nadawana przez host, osobna od `id`
i rewizji ekranu. SET_INPUT zawsze tworzy nowszy kontekst. Nie modyfikujemy
maski działającego kontekstu; jej zmiana oznacza nowy kontekst i nową bramkę
zwolnienia styków. Powtórzenie tej samej komendy jest tylko retransmisją.
Przed wyczerpaniem liczników host otwiera nową sesję w stanie zatrzymanym;
liczniki nigdy nie zawijają się w ramach sesji/kontekstu.

`mask` jest uporządkowaną listą `[kolumna, "8 cyfr hex"]`. Bit N oznacza
wiersz N. Kolumny nie mogą się powtarzać, dwa najwyższe bity muszą być
zerowe, zapis hex jest małymi literami. Pomijamy kolumny o zerowej masce.
`[[19,"0000000e"]]` oznacza pola (19,1), (19,2), (19,3).
Pusta lista oznacza brak wejścia, nigdy całą planszę. Pełny skan diagnostyczny
to jawna maska wszystkich pól; nie jest automatycznym procesem w tle.

| `mode` | Zachowanie |
|---|---|
| `single` | Pierwsze naciśnięcie kończy wejście; wybór akcji, celu lub pola ruchu |
| `stream` | Kolejne naciśnięcia bez ponownego uzbrojenia; licznik kości |

`finish` ma ten sam format co maska i musi być jej podzbiorem. W `single`
jest pustą listą, ponieważ każde pole kończy wybór. W `stream` naciśnięcie
pola z `finish` emituje `press` z `final: true` i atomowo kończy wejście.
Wszystkie pozostałe press mają `final: false`. ESP nie wie, czy pole oznacza
zatwierdzenie, powrót czy anulowanie. W pojedynczym wyborze press zawsze ma
`final: true`.

SET_INPUT najpierw sprawdza całą wiadomość, następnie atomowo zastępuje
wejście i usuwa oczekujące zdarzenia poprzedniego kontekstu. Zdarzenia już
w kablu host odrzuca po ID kontekstu. Odpowiedź `input_set` poprzedza wszelkie
zdarzenia nowego kontekstu. Nieprawidłowa maska/tryb w świeżej komendzie
bieżącej sesji zatrzymuje wejście i zwraca `error`; nie pozostawia starego
menu aktywnego. Stare ID/konteksty lub obca sesja nie zatrzymują nowszego
wejścia. Niedająca się przypisać uszkodzona ramka jest odrzucana; host po
braku potwierdzenia nie traktuje nowego menu jako uzbrojonego.

STOP zawsze zawiera `context`; nie istnieje STOP bezwarunkowo zatrzymujący
przyszły wybór. Zatrzymanie bieżącego kontekstu unieważnia jego oczekujące
zdarzenia. Zatrzymanie już zatrzymanego jest sukcesem, starego względem
bieżącego daje `stale_context` bez zmiany. Po błędzie I²C samo SET_INPUT nie
wznawia pracy: potrzebna jest udana reinicjalizacja czujników i nowy kontekst.

## Przykład: wpisanie wyniku kości

Przykładowe pola odpowiadają obecnemu panelowi; firmware nie ma tych pozycji
na stałe. Wszystkie poniższe obiekty są pełnymi ramkami JSON wysyłanymi
w osobnych liniach. Założenie: HELLO i komendy do ID 11 już zakończone.

```json
{"v":2,"type":"SET_INPUT","boot":"a18b920000000001","session":"b42c810000000001","id":12,"context":7,"mode":"stream","mask":[[19,"0000000e"]],"finish":[[19,"00000002"]]}
{"v":2,"type":"input_set","boot":"a18b920000000001","session":"b42c810000000001","id":12,"context":7,"state":"waiting_release"}
{"v":2,"type":"input_ready","boot":"a18b920000000001","session":"b42c810000000001","context":7,"state":"scanning"}
{"v":2,"type":"press","boot":"a18b920000000001","session":"b42c810000000001","context":7,"seq":1,"col":19,"row":2,"final":false,"uptime_ms":15230}
{"v":2,"type":"ACK","boot":"a18b920000000001","session":"b42c810000000001","context":7,"seq":1}
{"v":2,"type":"press","boot":"a18b920000000001","session":"b42c810000000001","context":7,"seq":2,"col":19,"row":1,"final":true,"uptime_ms":16100}
{"v":2,"type":"ACK","boot":"a18b920000000001","session":"b42c810000000001","context":7,"seq":2}
```

Pierwszy press to +: aplikacja zmienia np. 10→11, bez SET_INPUT, STOP ani
aktualizacji LED, jeśli podświetlenie się nie zmieniło. Drugi to ✓: ESP już
nie przyjmuje kliknięć tego kontekstu, aplikacja zatwierdza wynik po wszystkich
wcześniejszych zdarzeniach i dopiero potem otwiera kolejny kontekst.

Przy wartościach 1 i 20 utrzymujemy tę samą maskę panelu. Host ogranicza
wartość do zakresu kości; kolejne + przy 20 nie zmienia wyniku. Zmiana liczby
nie zmienia kontekstu. Następna kość, podsumowanie, inny bohater lub inny
zestaw legalnych pól zawsze go zmieniają.

## Skanowanie i naciśnięcia

Stany: `idle`, `waiting_release`, `scanning`, `completed`, `fault`.
Boot/nowa sesja zaczyna od idle. Pusta maska daje idle, bez input_ready.
Niepusta maska zaczyna od waiting_release; 25 ms stabilnego zwolnienia
aktywnych pól prowadzi do scanning i input_ready. Stan oraz maskę aktualnie
przytrzymanych aktywnych pól można odczytać w status. Nieaktywny styk nie
uczestniczy w programowej bramce zwolnienia.

Wersja docelowa obsługuje pojedyncze naciśnięcia, bez multitouch i bez
automatycznego powtarzania przytrzymanego +. Akceptujemy jedno aktywne pole
stabilne przez 25 ms. Kilka wykrytych aktywnych pól jednocześnie nie daje
arbitralnego wyboru: skaner czeka na ich zwolnienie. Po każdym naciśnięciu
w stream ponownie wymaga zwolnienia aktywnych pól przez 25 ms. Przy final
przechodzi do completed, niezależnie od nadejścia ACK. Nowy kontekst także
wymaga zwolnienia, więc przytrzymane ✓ nie zatwierdzi następnego ekranu.

To świadomie prosta semantyka „naciśnij–puść”. Stale zwarty aktywny styk
może wstrzymać wejście i musi być widoczny w diagnostyce. Nie obiecujemy
odporności na elektryczny ghosting: matrycę trzeba sprawdzić na sprzęcie,
także z nieaktywnymi polami zwartymi jednocześnie z aktywnymi.

Pętla odczytuje tylko kolumny o niepustej masce i tylko potrzebne ekspandery
wierszy. Przywraca ostatnio aktywowaną kolumnę zamiast wykonywać 20 zapisów
na każdy przebieg. Pełny stan nieaktywnych kolumn ustawia przy inicjalizacji
i odzyskiwaniu. Odczyty i zapisy I²C muszą zwracać informację o powodzeniu;
błąd nie może udawać braku naciśnięcia. Przy błędzie zatrzymujemy generowanie
zdarzeń i próbujemy przywrócić nieaktywne wyjścia; nie zakładamy, że zapis
powiedzie się przy uszkodzonej magistrali.

## Dostarczenie zdarzeń i granice gwarancji

`seq` rośnie od 1 w każdym kontekście. Klucz deduplikacji to
`(boot, session, context, seq)`. Host przyjmuje press tylko z bieżącego
kontekstu, zgodny z maską i trybem, i stosuje kolejne numery w kolejności.
Nie przeskakuje brakującego numeru, również gdy późniejsze zdarzenie to ✓.

ESP przechowuje do 32 niepotwierdzonych press. ACK z seq=N potwierdza
wszystkie od 1 do N danego kontekstu. Host wysyła go po umieszczeniu zdarzeń
w ograniczonej kolejce transportu, nie przedtem. Duplikat jest ponownie
potwierdzany, lecz nie dopisywany jako kolejna akcja. ACK ze starym kontekstem
nie dotyczy nowego, ACK poza zakresem wysłanych numerów jest błędem.

Brak ACK najstarszego zdarzenia przez 250 ms powoduje jego retransmisję
z tym samym seq i czasem. Skanowanie trwa dalej, o ile kolejka ma miejsce.
Brak postępu ACK przez 2 s lub przepełnienie kolejki daje fault i zatrzymuje
nowe wejście; utraconej serii nie odtwarzamy po ponownym połączeniu. Host
nie wykonuje pozostałych zdarzeń unieważnionego kontekstu i uzbraja nowy
dopiero po uzgodnieniu stanu gry. Kolejka hosta również ma limit i nie może
po cichu usuwać starszych kliknięć.

To dostarczenie z retransmisją i deduplikacją w żywej sesji, nie gwarancja
zapisania akcji dokładnie raz mimo awarii procesu lub utraty zasilania.
ACK transportowy nie oznacza zatwierdzenia reguł ani zapisu gry na dysku.
Po restarcie nie odtwarzamy buforowanych dotknięć jako nowych decyzji.

## Łączność i błędy

Host wysyła JSON PING co 1 s. ESP odpowiada status i niezależnie wysyła go
co 1 s, także w idle/completed/fault. Status zawiera stan, kontekst lub null,
gotowość czujników, ostatni seq, ostatni ACK, rozmiar kolejki, przytrzymane
aktywne pola, liczniki błędów I²C oraz czas ostatniego/maksymalnego przebiegu.
Status nie wymaga ACK; powtarzane stany zastępują input_ready zgubione w kablu.
Zwykłe informacje diagnostyczne nie mogą blokować press ani pętli skanowania.

Robocze wartości do sprawdzenia na sprzęcie: potwierdzenie komendy do 500 ms,
maksymalnie dwa ponowienia z tym samym ID; po 3 s bez poprawnej wiadomości
bieżącej sesji host uznaje połączenie za utracone i unieważnia kontekst.
ESP po 5 s bez poprawnej komendy/ACK bieżącej sesji zatrzymuje wejście
i zamyka sesję. Samo PING tekstowe i błędne ramki nie przedłużają sesji.
Host nie czeka na kliknięcie, żeby wysyłać PING. Oczekiwanie gracza nie ma
limitu w protokole; aplikacja może osobno anulować wybór komendą STOP.

Nowy boot, błąd sensora, brak potwierdzenia SET_INPUT lub błąd kolejki nie
uruchamiają samoczynnie poprzedniego menu. Host przestaje przyjmować jego
zdarzenia, sprawdza połączenie i tworzy nowy kontekst z aktualnego stanu gry.
Przeglądarka podejmuje próbę połączenia przy wejściu do gry. Po awarii
pokazuje utratę połączenia i przycisk Ponów; nie odtwarza samoczynnie menu.

`error` zawiera kod oraz id, jeśli można wiarygodnie przypisać komendę.
`fault` zawiera kod, kontekst, stan i liczniki; bieżący fault powtarza status.
Minimalne kody: `invalid_frame`, `frame_too_long`, `unsupported_version`,
`wrong_boot`, `wrong_session`, `stale_request`, `id_conflict`, `stale_context`,
`invalid_mask`, `not_ready`, `i2c_error`, `event_overflow`, `ack_timeout`.
Odpowiedzi na uszkodzony strumień są ograniczane częstotliwościowo.
Firmware dodatkowo rozróżnia `invalid_ack`, `host_timeout` i `sequence_exhausted`.

## Integracja i wdrożenie

`board/` ma jeden czytnik portu, serializowany zapis, ścisły parser, obsługę
potwierdzeń i kolejki. Żądania Flask nie czytają bezpośrednio tego samego USB.
Adapter w `src/dnd_board_game/hardware/` przekazuje maskę i kontrakt wejścia
z aplikacji. Simulator zachowuje swój transport HTTP, walidację pól i anulowanie;
nie emuluje ramek USB, identyfikatorów ESP ani kolejki ACK.

Akcje z planszy i ekranu przetwarza sekcja krytyczna sesji gry. Oczekiwanie
na fizyczne wejście odbywa się poza nią, a przygotowanie kontekstu wewnątrz,
więc anulowanie nie może uzbroić spóźnionego skanu. Zatwierdzenie ekranem
zamyka kontekst i unieważnia oczekujące zdarzenia.

Zmiana wyniku tej samej kości nie zmienia maski ani kontekstu; transport
odbiera i potwierdza kolejne naciśnięcia niezależnie od przeglądarki i WLED.
Żądania HTTP odbierają po jednym zdarzeniu z kolejki i stosują reguły gry.
Zamknięta przeglądarka nie przetwarza samoczynnie akcji gry; kolejka jest
ograniczona, a przepełnienie zatrzymuje wejście z błędem.

Maska i podświetlenie wynikają z jednego opisu wejścia. WLED jest osobnym
transportem, obsługiwanym przez jednego pracownika `board/led_output.py`.
UI przekazuje pełną ramkę bez czekania na HTTP. Pracownik utrzymuje tylko
najnowszą żądaną ramkę, ponawia jej nieudane wysłanie i nie kolekcjonuje
nieaktualnych ekranów. Nie przerywa żądania HTTP, które już wysłano.

SET_INPUT nie czeka na potwierdzenie ramki WLED: brak odpowiedzi HTTP
nie może blokować odczytu przycisków. Anulowanie odcina stary skan,
a bieżące maska i kontekst oraz ACK poleceń USB nadal obowiązują.
Pracownik LED osobno raportuje oczekiwanie/błędy i ponawia aktualną ramkę.
Ta korekta hosta nie wymaga ponownego wgrania firmware. ACK HTTP potwierdza
odbiór przez WLED, nie stan optyczny każdej diody. Przy wolnej sieci światło
nadal może pojawić się później niż ekran. Szczegóły i pomiary:
`BOARD_WLED_LATENCY_2026-09-10.md`.

Stary backend USB i komendy v1 usunięto z aplikacji, firmware oraz skryptu
USB → WLED. Nazwa `mapping_id` kończy się `_v1`, ponieważ oznacza pierwszą
wersję fizycznego okablowania, a nie obsługę protokołu v1.

Testy wymagane przy implementacji: wszystkie 600 pól i maski brzegowe,
pusta/pełna maska, złe ramki i typy, duplikaty komend i press, zgubiony ACK,
stary STOP i opóźniony press, restart, błąd I²C, brak hosta, przepełnienie,
30 s namysłu, przytrzymanie przy zmianie kontekstu, kilka styków, szybkie +/−,
✓ kończące kolejkę, równoczesne sterowanie ekranem i planszą, wolny WLED.
Pomiar: czas przebiegu, naciśnięcie→zdarzenie→zmiana stanu/UI, p50/p95/max.
Wartości timeoutów i filtrów zatwierdzamy pomiarem, nie obietnicą z projektu.
