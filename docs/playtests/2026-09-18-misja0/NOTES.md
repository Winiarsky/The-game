# Mission 0 — notatki w trakcie próby

Test w izolowanej sesji aplikacji, Chrome 1300×720, realny WLED 192.168.50.2 i serial /dev/ttyUSB0. Wejście: formularze i przyciski strony, runy/pola przez ten sam endpoint wyboru planszy. Bez podmiany PW, wyników, etapów lub talii w stanie gry. Karty i kości losowane przez sterownik z zapisywanym ziarnem. Nie oceniamy wzrokowo fizycznych LED ani rzeczywistych emocji ludzi.

Potwierdzone obserwacje do raportu:
- P3: Brakka, Dagna, Erynd. Nessa: kompromis w rundzie 2. Wóz: sukces w rundzie 4.
- Instrukcja drogi nadal podaje poziomy wóz (9,17)–(10,17); aktualny układ po obrocie to (9,16)–(9,17).
- Wybór akcji walki: sprzeczne instrukcje (panel planszy / ikony na ekranie / wyłączone runy). Runy ruchu i ataku w praktyce działają. Ekranowe ikony to nieprzyciskowe `span`, przyciski są w rozwinięciu awaryjnym.
- Podgląd ruchu Brakki mówi „Brak dostępnych pól ruchu”, choć lista LED/pól zawiera 100 pozycji, a ruch na (7,16) da się wykonać.
- Opisy zdolności w awaryjnym wyborze i przypomnieniach zawierają stare „Wydaj: czerwona”, choć deklaracja używa nowego progu/spalania, a Szał jest bez many.
- Stany UI: „Rodzaj rozpoczętej serii: 0”, „Ofensywa w tej turze: +1”, „Czas Rage”, „Zwykły ruch rozpoczęty · koszt tej tury: 0: 0” — wewnętrzne znaczniki zamiast zwięzłego opisu dla gracza.
- Inicjatywa: planszowe Accept nie przesuwało kreatora rzutu (powtarzalnie), ekranowe zatwierdzenie działało. Do odtworzenia na fizycznym przycisku podczas testu ręcznego.
- Brakka w uruchomionej drużynie: 32 PW; `build_print_hero` i `training_hero`: 35 PW. Wyjaśnić rozjazd zapisanej postaci i wydruku.

Ograniczenia/błędy samego sterownika (nie zaliczać do błędów gry):
- Przez przeoczenie Oddechu fizyczna talia drogi zgubiła trzy powroty kart C,F,C. Odtworzono je z kolejności spalania i udanych prób Brakki, bez zmiany stanu aplikacji.
- Próba ustawienia drugiego bohatera na zajętym polu (6,20) została odrzucona HTTP400. CDP potem nie odpowiadało, nie ustalono przyczyny; ponowne otwarcie /play zachowało sesję.
- W inicjatywie przed wykryciem problemu sterownik nadpisał wiele jeszcze niezatwierdzonych wyników. Nie były to wykonane rzuty gry; wyłączyć z statystyki rzeczywistych testów.
- Powtarzane Accept podczas żądania fizycznego przestawienia Woźnicy nie miały prawa kontynuować. Poprawiono sterownik, by wskazywał wymagane pole.
- Przy reakcji Brakki kreator k12 istnieje w DOM pod modalem deklaracji. Sterownik musi najpierw zatwierdzić wierzchnią deklarację; klikanie przykrytego kreatora nie jest błędem gry.

Dodatkowe obserwacje po pierwszym pełnym przebiegu:
- P3: rozejm po pokonaniu procarza w rundzie 2. Nie doszło do 21 pkt ani mana draina. Krótka ścieżka misji nie uczy więc szczytu naładowania i resetu.
- Zbrojownia i kwatera: sukcesy w rundzie 2. Dzwon pozostawiony wsi, dokumenty zabrane; rozliczenie 30 sz i koszt identyfikacji 5 sz, medalik oraz Pierścień Siły w wykazie.
- Narrator opisuje opcję Miry w dylemacie także bez Miry, a Nimrę przy pierścieniu także bez Nimry (warunkowo, lecz zbędnie). Same przyciski są filtrowane.
- Porównanie wydruku: pozostałych sześć postaci ma zgodne startowe PW; rozjazd dotyczy Brakki (wydruk 35 / uruchomiona postać 32). Generatory mat używają `build_print_hero`; launcher zapisanych `data/characters`.
- P4: Nessa sukces w rundzie 3, 9 kart w talii. Przedmiot 2k8+4. Pełna talia 40, opór 36.

P4 po odtworzeniu punktu kontrolnego drogi:
- Niezakończona pierwsza próba drogi przerwana wraz z serwerem testowym (proces wyszedł z kodem 0, zamknął Chrome). Nie zaliczać jej jako błąd gry ani wynik konfrontacji. Zwykłe menu → Wczytaj odtworzyło właściwy skład i etap.
- Druga próba: porażka w rundzie 3, brak kart na pełny koszt reakcji (3 pozostawały). Zmęczenie k4=2. Status -2 do ataku i obrażeń u wszystkich czterech bohaterów; w rundzie 3 statusów już nie było. Dowód: checks.jsonl.
- Rozejm po pokonaniu parobka w rundzie 2 odrzucony; oferta nie powróciła.
- AI używa aplikacyjnego `encounter_rng = random.Random(7)`, a nie oddzielnego losowego ziarna każdej próby. Uwzględnić ograniczenie przy ocenianiu balansu.

- P4 mikstura: dwa osobne rzuty k8 (8 i 1), premia +4 raz, 13 PW leczenia Garrana 7→20, zużyta akcja i fiolka. Garran 22 pkt w rundzie 4, +6 do testów, dalszy dobór zatrzymany.

- P4 pełna walka zakończona zwycięstwem w rundzie 7. Końcowe PW Garrana 6/28, pozostali 24/24,21/21,20/20. Talia 7, spalone 6, wygasłe 6; bez draina. Końcowy przycisk brzmi technicznie „Zastosuj wynik encountera”.
- Po odmowie rozejmu narrator poprawnie opisuje brak pomocy i zakup wskazówki za 1 sz; wskazówka obniża ST kwatery o 2. Wybrano poręczenie Garrana.

Nowy potwierdzony problem rozliczenia: Identyfikacja, plotka i potrącenia operują
`CurrencyWallet(cp=total_cp)` i zachowują wartość, ale zamieniają monety na
miedziaki. Zapis P3: Brakka cp=3500, weight_lb=70. P4: Garran cp=4400,
weight_lb=88, chociaż końcowa wartość to 44 sz. Wartość nagrody poprawna,
masa i liczba monet 100× większe niż przy wypłacie w złocie. Wpływa na udźwig
pierwszego bohatera i przyszłe misje. U pozostałych waluta pozostaje w gp.

Ocena decyzji: odmowa rozejmu wydłużyła walkę z 2 do 7 rund, przyniosła rany,
zużycie mikstury i opłatę za plotkę. XP w obu końcowych zapisach pozostaje 0,
nie widać osobnej premii za dokończenie walki. Rozejm wydaje się dominującą
opcją mechaniczną; to decyzja projektowa, nie awaria. Porównać z zamiarem
nadania obu ścieżkom plusów i minusów.

Kontrola talii P5 ujawniła błąd sterownika: komunikat Oddechu pozostaje po zmianie aktora, więc był liczony ponownie. Usunięto niedobraną dodatkową B na spodzie; odtąd powrót wymaga faktycznego zwiększenia licznika talii o 1. P4 miał jeden taki nadmiarowy F na spodzie podczas Nessy, ale karty nie dobrano przed następnym tasowaniem, więc nie zmienił wyników. Nie zaliczać do błędów aplikacji.

P5 ukończony: Nessa kompromis runda 3, wóz sukces runda 3 (19 kart), rozejm runda 3, Garran już 21 pkt. Zbrojownia bez przeszukania (brak medalika), kwatera sukces runda 2. Nimra 14+4=18 identyfikuje pierścień, ale BŁĘDNIE pobiera się 5 sz: mission_zero_recovery.py:279 wywołuje identify_paid. Dzwon do Gildii: +10 sz ponad 50 sz kontraktu. Zapis końcowy wykonany.

Ograniczenie strategii walki: po próbie ataku bez legalnego celu sterownik pomija ten atak do końca tury. Późniejszy ruch nie kasuje tego pominięcia, więc czasami postać podchodzi i kończy turę, choć mogłaby już zaatakować. To zaniża skuteczność walki wręcz w początkowym podejściu; nie jest błędem gry ani dowodem wolnego tempa wynikającego z zasad. Wszystkie cztery walki korzystały z tej prostej polityki.

P6 ukończony i zapisany: Nessa sukces runda 4, talia 1; wóz porażka runda 4, talia 0, zmęczenie 1 rundę. Brak zmęczenia w rundzie 2 potwierdzony. Rozejm po trafieniu Miry w parobka w rundzie 3; wszyscy bohaterowie kończą z pełnymi PW. Zbrojownia zebrana bez przeszukania; kwatera sukces w rundzie 2, 33 karty. Nimra naturalne 20+4 rozpoznaje pierścień, ponownie BŁĘDNIE pobrano 5 sz. Dzwon u kontaktu Miry: zachowane 20 sz odroczone do misja_2, paid=false. Podsumowanie i zakończenie działają także przy 1131×584. Serwer testowy zamknięty po ukończeniu czterech prób.
