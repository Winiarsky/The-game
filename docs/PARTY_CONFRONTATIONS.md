# Drużynowe konfrontacje eksploracji — wersja 1

Aktualny model rozmów i obiektów w Arenie. Zastępuje aktywny samouczek blackjacka; starsze rozpoczęte próby nadal odczytuje silnik zgodności. Zwykłe rozmowy fabularne i pułapki walki zachowują swoje dotychczasowe przepływy.

## Wspólna procedura

Jedna figurka drużyny, osobna pula i tura każdego uczestnika. W aplikacji skład liczy 1–5 bohaterów, wybieranych spośród siedmiu. Prowadzący działa pierwszy, następni w kolejności składu; bez dodatkowego rzutu inicjatywy. NPC i obiekt mają wspólny opór oraz profil ST i kości wpływu dla każdej metody.

1. Przygotuj pełny komplet: po `max(5, 2 × liczba bohaterów)` każdego koloru, przetasuj. Osobiste pule puste.
2. Poniżej 21 punktów obowiązkowo dobierz jedną z dwóch odkrytych kart. Druga pozostaje; następny dobierający uzupełnia ofertę. Jeśli została tylko jedna karta, można ją wziąć. Przy 21+ nie dobierasz; przekroczenie nie szkodzi.
3. Kolor uruchamia pasyw. Punkty korzystają z tej samej tabeli bohatera co w walce.
4. Po doborze wybierz siłę testu albo pomoc innemu uczestnikowi.
5. Test: `k20 + cecha + wybrana premia naładowania + pasywy + pomoc`. Naturalne 20 nie omija ST, naturalne 1 nie przesądza porażki.
6. Sukces: `kość wpływu podatności + modyfikator cechy + pasywy wpływu`, minimum 0. Odejmij od wspólnego oporu. Biegłość i premia many nie zwiększają wpływu.
7. Po efekcie spal zadeklarowaną liczbę kart z wierzchu, również po nieudanym teście. Zgłaszaj kolory; aplikacja zachowuje bilans wszystkich fizycznych kart. Osobisty ładunek zostaje.
8. Po działaniach wszystkich postaci następuje jedna reakcja sytuacji, potem kolejna runda.

| Ładunek wymagany | Premia many do testu | Spalanie |
|---|---|---|
| 0 | +0 | 1 |
| 6 | +2 | 1 |
| 12 | +4 | 2 |
| 21 | +6 | 3 |

Możesz świadomie wybrać słabszy próg. Pomoc zajmuje działanie, nie spala, daje +2 do następnego własnego testu wybranego sojusznika. Nie kumuluje się; pozostaje wyższa premia. Trzeba ją wykorzystać w tej konfrontacji. Nie ma wsparcia siebie.

## Metody i podatności

| Bohater | Rozmowa | Cecha | Obiekt | Cecha |
|---|---|---|---|---|
| Garran | Autorytet | Siła | Zabezpieczenie | Kondycja |
| Brakka | Zastraszanie | Kondycja | Siłowe otwarcie | Siła |
| Mira | Blef | Inteligencja | Manipulacja | Zręczność |
| Dagna | Empatia | Mądrość | Oczyszczenie | Mądrość |
| Lorian | Inspiracja | Charyzma | Improwizacja | Inteligencja |
| Nimra | Argument | Inteligencja | Analiza | Inteligencja |
| Erynd | Dociekanie | Mądrość | Rozpoznanie | Mądrość |

Nazwy i cechy pochodzą z katalogu metod. Biegłości i ekspertyzy nie dodajemy; premia wybranego progu naładowania jest liczona tylko raz. Obycie Loriana daje +2 do testów opartych na Charyzmie; Praktyka terenowa Erynda +2 do własnych testów obiektów. Są uwzględnione w UI i na wydrukach, nie dodawane drugi raz do wpływu.

Wartości startowe: podatna metoda ST 15/k8, neutralna ST 20/k6, odporna ST 25/k4. Podwójny wpływ podatności jest celowy. W rozmowie o podwyżce Nessa jest podatna na Dagnę i Loriana, odporna na Brakkę, Mirę i Nimrę. Schowek premiuje Brakkę, Mirę i Erynda. Profile są jawne w panelach uczestników.

## Pasywy kolorów

Każdy bohater ma pięć wpisów w `content/balance/confrontation.json`. Pięć prostych efektów przypisano różnym kolorom:

- Stanowczość: +1 do wpływu za kartę, maksymalnie +2.
- Skupienie: +1 do testu za kartę, maksymalnie +2.
- Współpraca: pomoc +3 zamiast +2, bez kumulacji.
- Opanowanie: chroni jedną kartę osobistej puli przed każdą reakcją, bez kumulacji.
- Oddech: przy dobraniu tej karty oddaj najstarszą spaloną kartę na spód talii. UI wskazuje jej kolor; to jednorazowy efekt doboru.

Premie utrzymują się tylko tak długo, jak odpowiednie karty są w puli. Utrata karty usuwa jej premię i może przywrócić dobieranie poniżej 21. Kolorowe pasywy eksploracji są oddzielne od bojowych. Wszystkie 35 przypisań widnieje w UI i na kartach.

## Presja i zakończenie

Początkowy opór: 9 × liczba osób dla Nessy, 10 × liczba osób dla schowka. Po każdej rundzie reakcja spala `max(3, liczba osób)` kart. Cykl reakcji to presja, presja z odebraniem ostatniej karty największego ładunku, presja z odzyskaniem k4 oporu. Przy remisie utraty decyduje kolejność drużyny. K4 aplikacja losuje jednokrotnie i zapisuje wynik; odświeżenie nie przerzuca.

Opór 0 oznacza sukces. Wyczerpanie oznacza brak kart do **wymaganej operacji**, nie sam pusty stos. Jeżeli nie da się pokryć pełnego spalania, konfrontacja kończy się. Rozpoczęty test i jego wpływ rozstrzyga się wcześniej: zwycięski cios pozostaje sukcesem. Brak karty do obowiązkowego doboru także kończy scenę. Nie ma ostatniej darmowej rundy ani automatycznego resetu i dalszej rozmowy. Przed następną próbą zbierz wszystkie pule i spalone karty do nowej talii.

Nie dodajemy bojowego wygasania jednej karty na rundę: zegarem tej konfrontacji jest reakcja sytuacji. Nie ma też osobnych manewrów, ruchu w sporze ani bojowych ataków/ultów.

Cztery opcjonalne warunki zachowane w nowej procedurze: kompromis po zbiciu połowy oporu; dodatkowa informacja za sukces z dwiema niebieskimi w całej drużynie; czerwony drażliwy temat zmieniający cenę sukcesu; jednorazowy odzysk karty za zobowiązanie. Wyniki i zobowiązania zapisują się w historii prób.

## Obsługa i samouczek

Postać → Eksploracja → Skład drużyny / Po kolei / Wybierz ćwiczenie. Domyślnie prowadzący i dwoje towarzyszy. Skład można zmienić przed próbą. Dwanaście przypadków dla każdej postaci (84): NPC, obiekt, pomoc, 21+, reakcja, drain, cztery warunki, dwie samodzielne konfrontacje. Postęp nowego kursu nie dziedziczy zaliczeń starego blackjacka.

Próg 21, reakcja i drain mają jawne przygotowane stany fizycznych stosów, opisane przed rozpoczęciem. Pozostałe próby startują od pełnego kompletu. Ćwiczenie pomocy wymaga co najmniej dwóch osób. Powrót i restart działają także podczas doboru, spalania i rzutu. Pojedyncza próba nie przesuwa postępu kursu.

Wybory idą przez podświetlone runy. Naturalne wyniki testu i wpływu wprowadza się osobno przez fokus, −/+, podsumowanie, korektę i końcowe ✓. Premie doliczane są raz. Po wczytaniu trzeba potwierdzić zachowanie fizycznych stosów albo powtórzyć próbę. Zapisy przechowują profil sceny i uczestników, etap rzutu, premie, karty oraz wynik reakcji.

## Granice i ewaluacja

To wersja startowa do ręcznego sprawdzenia. `python scripts/evaluate_party_confrontations.py --trials 30` uruchamia 2520 prób w produkcyjnym silniku. [Raport](reports/PARTY_CONFRONTATIONS_V01.md) porównuje ciągłe testowanie ze wsparciem przy niskiej szansie. Dla 3–5 osób średnia wynosi około 3–3,3 rundy; solo bywa dłuższe. Symulacja nie mierzy czasu zgłaszania fizycznych kart ani jakości decyzji ludzi.

Silnik: `rules/confrontation.py`; budowanie profili i przygotowane lekcje: `application/confrontation.py`; katalog: `scenarios/confrontation.py`; transport i zapis: `ui/confrontation.py`. Niskopoziomowe `board/` pozostaje bez zmian.
