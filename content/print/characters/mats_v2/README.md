# Zestawy postaci — A4 v2

Jeden komplet: `../bohaterowie_zestawy_startowe_A4.pdf`.
Pierwsza strona zawiera spis. Następnie Garran, Brakka, Mira, Dagna, Lorian,
Nimra i Erynd, po pięć stron każdej postaci. Na końcu czterostronicowy pomocnik
oraz arkusz znaczników. Łącznie 41 stron.

## Arkusze postaci

1. Historia, motywacja, cel osobisty i statystyki. Pod portretem i historią:
   skaza oraz „Aktualne zobowiązania” z kropkowanymi liniami na notatki.
   Zasady eksploracji są we wspólnym pomocniku, bez powtórzenia na karcie postaci.
2. Mata many A4 poziomo: pięć miejsc na pełne karty **63 × 88 mm** bez koszulek.
   Osobiste punkty i pasywy pozostają widoczne obok kart. Walka ma czarny
   nagłówek, eksploracja jasny. Każdy tryb ma osobny symbol z obwódką:
   gruba — kumuluje się, cienka — nie kumuluje się. Dzięki temu ten sam kolor
   może kumulować się w jednym trybie, a w drugim nie.
3. Wszystkie akcje na jednym A4, z bieżącymi runami, progami, kosztami i podbiciami.
   Sześć postaci ma po 9 ramek **62 × 76 mm**. Nimra ma 12 ramek **68 × 53 mm**
   na A4 poziomo. Nowe karty rozwoju powinny odpowiadać wymiarom i runom
   właściwej postaci. Sam rozwój i zmiana zestawu akcji nie są częścią tej zmiany.
4. Pusta mata wyposażenia: ręce, pancerz, głowa, szyja, pierścień,
   przybory magiczne / instrument i zbiorczy plecak. Ramki plecaka nie wprowadzają limitu
   liczby przedmiotów; można układać żetony w stos.
5. Startowy sprzęt do wycięcia: ilustracja, nazwa, slot, mechanika.
   Żetony mają **60 × 42 mm**. × przy nazwie oznacza ilość w stosie, a cztery
   osobne noże Miry mają cztery osobne żetony. Pod wycinankami jest rozpisane
   startowe rozmieszczenie wyposażonego sprzętu; reszta trafia do plecaka.

## Wspólne dodatki

Pomocnik (strony 37–40): podstawy i słownik, walka, rozmowy z NPC, obiekty.
Każdy tryb ma procedurę i przykład liczbowy. Drukuj jedną kopię dla drużyny.
Strona 41 zawiera znaczniki. Znaczniki: sześć zajętej
drugiej ręki i sześć wykorzystania zdolności do draina. Tych drugich używaj
tylko wtedy, gdy opis zdolności określa takie ograniczenie. Nie nakładają
nowych limitów na pasywy. Znaleziska i handouty Misji 0 są w pakiecie scenariusza.

Drukuj jednostronnie, A4, **100% / rzeczywisty rozmiar**, bez dopasowania.
Automatyczny obrót stron jest dozwolony, zmiana skali nie. Sprawdź linijką
odcinek 50 mm lub prostokąt miejsca na kartę many. Przy wymianie wyposażenia
przekaż też fizyczny żeton; stan musi odpowiadać aplikacji.

## Edycja i odbudowa

- `python scripts/build_hero_mats.py` buduje, sprawdza i publikuje cały komplet.
- `python scripts/build_session_print_packs.py --only heroes` robi to samo.
- `python scripts/build_hero_mats.py --check-only` sprawdza wszystkie układy bez PDF.
  Można dodać `--actor nimra`, by obejrzeć wybraną postać. Publikacja wymaga wszystkich.
- **Wszystkie opisy edytuj w `content/characters/karty_postaci.json`.**
  Instrukcja sekcji: `content/characters/README.md`.
- Ten sam plik zasila grę, karty, pasywy obu trybów, lekcje samouczka,
  opisy wycinanek, cztery strony pomocnika i słownik pogrubień.
- Statystyki, progi, koszt, runy i wyposażenie pochodzą z reguł gry.
  Zmiana tekstu nie zmienia naliczanej mechaniki.
- `source_snapshot.json` zapisuje dane siedmiu postaci użyte do eksportu.
- `validation.json` zawiera kontrolę przepełnienia tekstu, grafik i wymiarów.
- W katalogu każdej postaci są pojedyncze HTML, PDF i PNG. `podglad.html`
  pokazuje je razem i pozwala otworzyć wybrany arkusz.

Generator używa dotychczasowego stylu Garrana i istniejących ilustracji.
Nie dodaje zależności. Lokalne Chrome i Poppler zapewniają skład i weryfikację.
Jeżeli dostępny jest Ghostscript, końcowy PDF ogranicza rozdzielczość zbyt dużych
ilustracji do 300 dpi. Tekst, runy i ramki pozostają wektorowe.
Pliki `.sha256` oznaczają poprawnie wyrenderowane wersje; niezmienione strony
są używane ponownie. Usunięcie takiego pliku wymusza ponowny render arkusza.
