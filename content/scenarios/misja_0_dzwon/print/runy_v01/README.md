# Runy v0.1 — wydruki i makieta

Otwórz [aktualny spis materiałów](index.html). Prowadzi do kart osobistych
koszyków run v0.2 w `../runy_koszyki_v01/` (42 strony, 6 na bohatera).
PDF-y postaci w tym katalogu są poprzednią wersją do starszych zapisów.
Poniższy opis kart i generator dotyczy tych starszych plików.
Plansza i kafle pozostają aktualne. Druk A4, 100%, bez dopasowania.
Plansza: 12 arkuszy A1–D3. Tnij zewnętrzny obrys; pasy 10 mm służą jako zakładki.
Składaj od górnego lewego A1 w wierszach A–D. Panel znajduje się przy dolnej krawędzi.
Plansza oraz wszystkie 18 kafli Misji 0 mają skalę `(250/244) × 1,03`.
Przed pełnym drukiem porównaj kilka sąsiednich pól z fizycznymi czujnikami.

Każdy bohater: 3 niecięte maty + 2 arkusze wycinanek, łącznie 5 stron.
Zdolności 60 × 54 mm; sprzęt 60 × 42 mm. Nie skaluj tych elementów o 3%.
Mata zdolności ma 12 pustych miejsc; znaki run i zasady są na wymiennych kartach.
Karty siedmiu bohaterów zawierają koszty run, budżet akcji i do trzech wzmocnień.
Koszty i efekty pochodzą ze wspólnego źródła używanego przez aplikację.
Statystyki i wyposażenie pochodzą z obecnych postaci.

Źródło kart: `content/print/runes_v01/action_cards.json`.
Odbudowa: `PYTHONPATH=src .venv/bin/python scripts/build_rune_prototype.py`.
Można użyć `--only heroes` lub `--only maps`. Generator sprawdza układ przed publikacją.

Nowa aplikacja używa tego nadruku: ruch, atak, przedmiot, koniec tury, przerwa,
runy, przerwa, +, −, ✓, ↩. Gwiazda oznacza informację o bohaterze.
Runy dobieracie tylko na początku walki; reputacja jest osobnym zasobem drużyny.
Zwykły atak okazyjny bronią nie kosztuje run; zużywa dostępną reakcję.
Przy kilku dostępnych reakcjach wybiera się jedną, a koszt płaci po potwierdzeniu.
