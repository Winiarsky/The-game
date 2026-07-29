# Arena mechanik

`mechanics_playground` jest scenariuszem diagnostycznym widocznym w menu
**Nowa gra**. Nie jest częścią kampanii, nie przyznaje doświadczenia ani łupu
i może być bezpiecznie resetowany między próbami.

## Moduły

- **Arena walki** — ruch, zasięg, osłony, ataki, obszary, stany i cele
  wybierane przez fizyczną planszę.
- **Laboratorium magii** — przypomnienie przepływu celowania czarów
  pojedynczych, wielocelowych, linii, stożków i obszarów.
- **Tor eksploracyjny** — zamknięte drzwi, skrzynia, uszkadzalny obiekt,
  aktywne Szukanie oraz użycie przedmiotu, broni lub czaru.
- **Pracownia rozmów** — NPC MISTRZ-0 z próbami informacji, Perswazji,
  Oszustwa i Zastraszania oraz swobodną rozmową z MG.
- **Stacja odpoczynku** — powtarzalny krótki odpoczynek, kości
  wytrzymałości i regeneracja zasobów.

Wszystkie stanowiska są logicznymi lokacjami na jednej planszy 20x30.
Przejście między nimi nie wymaga wymiany papierowej mapy.

## Konfiguracja próby

Po wejściu do **Sterowni areny** albo **Areny walki** konfigurator pojawia
się bezpośrednio w głównym strumieniu rozmowy. Jego kopia diagnostyczna jest
również dostępna w panelu **Menu → Tryb twórcy → Arena mechanik**. Można ustawić:

- od 1 do 6 manekinów,
- KP, PW, szybkość oraz wspólną wartość sześciu cech,
- typ stworzenia,
- odporność, niewrażliwość albo podatność na wybrany typ obrażeń,
- odporność na wybrany stan.

Gotowe profile obejmują cel standardowy, opancerzony, odporny,
niewrażliwy, podatny, odporny na stan, nieumarłego oraz grupę sześciu
celów do prób obszarowych.

Przycisk **Przygotuj próbę** uruchamia zwykły encounter. Dalej obowiązuje
normalny przepływ gry: setup figurek, inicjatywa, tury, fizyczne wybieranie
celów i obszarów, rzuty oraz LED-y. **Resetuj próbę** przywraca bohaterom
PW, czary i zasoby, odtwarza obiekty oraz usuwa wynik bieżącej walki,
zachowując ostatnią konfigurację manekinów.

## Zalecany test klasy lub czaru

1. Uruchom Arenę mechanik i wybierz własne postacie.
2. Dobierz profil manekina do sprawdzanej reguły.
3. Dla czaru obszarowego wybierz profil „Grupa celów obszarowych”.
4. Rozegraj akcję przez planszę i sprawdź opis mechaniczny oraz LED-y.
5. Zapisz wynik w logu sesji.
6. Zresetuj próbę i powtórz z innym profilem albo położeniem figurek.

Arena potwierdza działanie runtime, ale nie zastępuje jednostkowych testów
reguł ani audytu zgodności ze SRD.
