# Misja 0 — rejestr krytyki i odpowiedzi

Przegląd Codex, 27.11.2026, źródło: [MASTERPLAN.md](MASTERPLAN.md).
Odniesienia: `PROJECT_CONTEXT.md`, `GAME_DESIGN.md` (konfrontacje, postawa,
brak twardych blokad), `ARCHITECTURE.md`, `mechanics/rewards.json`,
`mechanics/ethos.json`, teksty scen oraz rzeczywisty kod konfrontacji i rozliczenia.
To odczyt krytyczny; wynik botów nie zastępuje obserwacji przy stole.

Wpisy opisują diagnozę i wdrożoną odpowiedź techniczną. Pola `Response` i
`Status` pozostają dla autora (`accepted`, `rejected`, `deferred`, `discuss`).
Czerwony wpis oznacza błąd w działaniu, pomarańczowy słabość decyzji/tempa,
żółty sprzeczność reguł lub informacji.

## A. Błędy w działaniu

### A1 🔴 — Borut pobiera opłatę za niedziałającą wskazówkę

> [!CAUTION]
> `text/rumor.md` obiecuje −2 ST, lecz `mission_zero.scene` zmieniało stare
> pole `dc`, ignorowane przez `progress_v1`. Odtworzono ST 14 po zakupie.
> Naprawa: wspólny konstruktor uwzględnia korektę również dla bieżących ST;
> adapterem zatwierdzono sukces przy sumie 12, po czym wczytano ten wynik.

→ Response:
→ Status:

## B. Alternatywne zachowania graczy

### B1 🟡 — Po porażce narrator obiecuje niedostępny wybór dzwonu

> [!IMPORTANT]
> `after_defeated.md` i masterplan pozostawiają dzwon wieśniakom.
> Wspólny tekst finału proponował jednak Gildię i kontakt Miry. Wdrożono
> `dilemma_defeated.md`: gracze potwierdzają wcześniej ustalony warunek;
> kontrakt nadal można rozliczyć. Obie zabronione akcje odrzuca także serwer.

→ Response:
→ Status:

### B2 🟠 — Zakup wskazówki po zamknięciu kwatery jest bezwartościowy

> [!WARNING]
> Bezpieczny odbiór i rozstrzygnięte przeszukanie zamykają pomieszczenie,
> lecz rozmowa nadal oferowała płatną plotkę. Opcja znika po odbiorze kwatery;
> odrzucone żądanie nie zmienia pieniędzy. Nie dodajemy ponownych przeszukań.

→ Response:
→ Status:

## C. Wiarygodność pamięci świata

### C1 🟡 — Rozejm nie zawsze przywraca środek postawy

> [!IMPORTANT]
> `after_accepted.md` pomijał wpływ kradzieży mikstury. Kradzież → zamiana
> wozu → rozejm to pozycje 3→4→5→4, a nie powrót do 3. Tekst opisuje teraz
> rzeczywiste przesunięcie o jedno pole, bez kasowania poprzednich decyzji.

→ Response:
→ Status:

## D. Tempo i ryzyko monotonii

### D1 🟠 — Dwa przeszukania mogą powtarzać tę samą decyzję

> [!WARNING]
> To hipoteza do ogrania, nie wykryty błąd. Oba pokoje pozwalają porównać
> bezpieczny odbiór z jednorazową próbą zdobycia przedmiotu, ryzykując 2 sz.
> Obserwować w drużynie 3- i 6-osobowej czas scen oraz to, czy gracze
> rozumieją moment zobowiązania. Nie zmieniać pętli na podstawie samych botów.

→ Response:
→ Status:

## E. Pytania przy stole

### E1 🟠 — „Ile dostaniemy za dzwon i kiedy?”

> [!WARNING]
> Kwoty ujawniano po wyborze. Finał pokazuje teraz premię Gildii przy
> rozliczeniu, brak premii za pozostawienie dzwonu i odroczoną zapłatę pasera.
> Tekst czyta wartości z `rewards.json`. Dokładny termin przyszłej Misji 2
> pozostaje ukryty zgodnie z masterplanem; gracze wiedzą, że nie dostaną
> pieniędzy od razu. Wybór długu nadal jest odrębny od losu dzwonu.

→ Response:
→ Status:

## F. Spójność instrukcji i systemu

### F1 🟡 — Narrator wymaga przygotowania nieistniejącej talii

> [!IMPORTANT]
> `after_accepted.md`, `after_refused.md`, `cart_coerced.md` i `surrender.md`
> zawierały instrukcje dawnej many. Usunięto je z aktywnej narracji. Teksty
> wznowienia opisują zachowany postęp i działania; nie obiecują jednej próby
> na bohatera w starym zapisie, którego silnik celowo pozostaje niezmieniony.

→ Response:
→ Status:

## Triage

A1, B1, B2, C1, E1 i F1 mają wdrożone poprawki i kontrole regresji lub
przegląd zgodności tekstu z regułami. D1 pozostaje zadaniem dla ludzi przy stole.
Nie znaleziono blokady dostawy po porażce przeszukania: ładunek jest dostępny,
a dokumenty długu i dzwon pozostają niezależnymi konsekwencjami. Masterplan
celowo wyklucza śmierć wieśniaków przy 0 PW; nie wymaga dodatkowej gałęzi
„zabity Borut”.
