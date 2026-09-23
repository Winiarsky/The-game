# Korekty po audycie kart — 22.09.2026

Użytkownik zlecił wdrożenie wyboru wydawanych run i korekt opisanych w audycie.
Poniżej konkretne warianty wybrane do następnego testu. Starszy audyt 66 kart
pozostaje zapisem problemów przed zmianami; bieżący zestaw ma 65 kart, ponieważ
dwie zdolności odzysku Loriana zostały połączone.

## Wybór zasobów

Wymagane konkretne symbole są rezerwowane przed wyborem dowolnych run.
Zatwierdzenie podglądu otwiera osobny etap, jeśli potrzebny jest wybór zasobu.
Kliknięcie symbolu wybiera jedną dostępną kopię, a cofnięcie usuwa ostatni wybór.
Zatwierdzenie jest dostępne po wybraniu całego kosztu. Do tego momentu ręce,
stos odrzuconych i budżety działań pozostają bez zmian.

Dotyczy to dopłat dowolną runą, zastępowania brakującego kosztu dwiema dowolnymi,
podtrzymania Bastionu i runy sojusznika w Kontrataku. W Kontrataku oba koszty
są ustalane przed wykonaniem mocy. Strojenie wymaga wyboru runy do wymiany
spośród kart pozostałych po zapłacie. Odzysk pozwala wybrać konkretne runy
odrzucone przed rozpoczęciem płatności; właśnie płacony koszt jest wyłączony.

## Wybrane zmiany bohaterów

| Bohater | Wdrożony wariant do ogrania |
| --- | --- |
| Garran | Bastion jest stacjonarnym kręgiem zakotwiczonym na polu rzucenia. Obejmuje sojuszników znajdujących się wewnątrz, także po odejściu Garrana. Pierwszy kolejny początek jego tury nie wymaga opłaty; od drugiego podtrzymanie kosztuje wybraną dowolną runę i przywraca +1 KP oraz promień 2 pól. Pozostałe ochrony zachowują własne role. |
| Brakka | Pierwszy Szał w walce nie kosztuje run, ale zużywa specjalną. Następne aktywacje kosztują 1 × Rozwidlenie (symbol przycisku Szału). Utrata Szału nie odnawia darmowego użycia. |
| Mira | Zwód blokuje wskazanemu sąsiedniemu wrogowi ataki okazyjne przeciw całej frakcji Miry do początku jej następnej tury. Dym pozostaje osobnym stacjonarnym obszarem 3×3 z przewagą do Ukrycia. |
| Dagna | Zachowanie życia pozostawia 40 PW leczenia, lecz działa raz na walkę. Święty płomień obejmuje tylko wrogów, dając mu rolę bezpiecznego obszaru. |
| Lorian | Jeden Odzysk: S i Romb, do dwóch wybranych run. Wariant Wielkiego odzysku oddaje również zwykły atak/przedmiot (A+S) i odzyskuje do trzech, bez dodatkowej opłaty runą. Cała karta raz na walkę, bez odzysku własnego kosztu. Luneta za M+S przygotowuje zwykły strzał: +2 i pominięcie częściowej osłony; dopłata Bramy oraz A daje dwa takie strzały w jeden cel. |
| Nimra | Załamanie woli zadaje obrażenia psychiczne i po nieudanej obronie daje utrudnienie najbliższej obrony MDR, najpóźniej do początku następnej tury Nimry. Szpilka umysłu zachowuje odbieranie reakcji. Nowy znacznik nie zużywa się przy rzucie, który dopiero go nadaje. |
| Erynd | Podwójny strzał kosztuje A+S: dwa strzały zastępują zwykły atak i specjalną. Trzy strzały kontrolujące zachowują różne role. |

Przygotowanie Lunety nie odbiera zwykłego ataku i nie wykonuje strzału samo.
Premia wygasa przy użyciu odpowiedniego zwykłego strzału albo z końcem tury.
Odzysk nadal trafia do własnej ręki Loriana, z limitem 7; nie dodano przekazywania
run między graczami w trakcie walki.

## Granice tej próby

Dobór pozostaje N+2 tylko na początku walki. Wybrany model to rzadkie moce
i skończony zapas, dlatego nie podniesiono równocześnie wszystkich wielkich
mocy do kosztu kilku run. Ceny w runach i w działaniach pozostają oddzielne.
Limit Odzysku zamyka powtarzalny obieg jego własnej opłaty.

W następnym ograniu należy zanotować: liczbę specjalnych i reakcji na osobę,
czas przygotowania Brakki/Miry, użycia i utrzymanie Bastionu oraz karty,
które mimo dostępności były zawsze pomijane. Balans nie jest potwierdzony
samym przejściem testów technicznych.

## Weryfikacja wdrożenia

- `test_rune_payment_choices.py`: 13 przypadków wyboru, cofania, rezerwacji,
  odzysku i zapisu. Zmiana partnera Kontrataku podczas wyboru run jest blokowana.
- `test_rune_audit_effects.py`, `test_rune_garran.py`,
  `test_nimra_mind_break.py`: efekty, budżety działań, podglądy i wygasanie.
  Przeszły również regresje zasobów, kart bohaterów i wspólnych usług walki.
- Chrome, `test_tabletop_combat_browser.py` przy szerokości 1131:
  pełna tura przez skaner planszy, jawny wybór trzech run, duplikaty,
  cofanie, odrzucona stara rewizja, przewijanie i koszt dopiero po ✓.
- Chrome, `test_rune_prototype_browser.py`: makieta wraz z wyborem
  dowolnej runy i dwóch zastępczych run bez wydawania pozostałego Klucza.
- `test_rune_prototype_prints.py` i `test_tabletop_combat.py`: 15 testów;
  zgodność kart z makietą, pozycje symboli i podgląd efektów postaci.
  Generator sprawdził przepełnienia wszystkich siedmiu zestawów; zbiorczy
  PDF ma 35 stron A4. Sprawdzono też wizualnie stronę wycinanek Loriana.

Aktualne karty: [action_cards.json](../content/print/runes_v01/action_cards.json).
Pierwotna analiza: [HERO_ACTION_REVIEW.md](HERO_ACTION_REVIEW.md).
