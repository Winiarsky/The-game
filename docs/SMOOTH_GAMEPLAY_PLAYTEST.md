# Playtest płynności rozgrywki

Checklista obejmuje jeden pełny przebieg scenariusza testowego na fizycznej
planszy. Nie ocenia jakości fabuły. Każdy problem zanotuj razem z nazwą lokacji,
tekstem aktywnego kroku i przybliżonym czasem.

## Automatyczne nasłuchiwanie planszy

- Po pojawieniu się przestrzennego wyboru UI samo przechodzi przez
  „Przygotowuję planszę” do „Plansza nasłuchuje”.
- Ruch, cel, obszar czaru i kafelek interakcji nie wymagają wcześniejszego
  kliknięcia „Skanuj planszę”.
- Kliknięcie legalnego pola uruchamia dokładnie jeden krok.
- Kliknięcie kafelka w UI podczas aktywnego skanu anuluje stary skan; jego
  spóźniona odpowiedź nie zmienia nowego stanu.
- Po timeoutcie pojawia się „Spróbuj ponownie”, a przy rozłączeniu dostępny jest
  wybór awaryjny.

## Czat i tempo decyzji

- W danym momencie widoczna jest jedna dominująca karta bieżącej decyzji.
- Zakończone deklaracje, rzuty i wyniki zostają w historii we właściwej kolejności.
- Gdy historia jest przewinięta wyżej, nowy krok nie wyrywa widoku i pokazuje
  przycisk „Nowy krok”.
- Działanie bez opisu przechodzi automatycznie tylko wtedy, gdy wszystkie wybory
  są jednoznaczne.
- Działanie z opisem opcjonalnym można wykonać pustym polem; działanie z opisem
  wymaganym nadal go żąda.

## Gemini

- Wiadomość graczy pojawia się natychmiast, zanim Gemini odpowie.
- UI pokazuje „MG zastanawia się…” albo nazwę aktywnego NPC.
- Podczas oczekiwania nie można drugi raz uruchomić tej samej mechaniki, ale można
  czytać historię i korzystać z paneli Postać, Stany, Czary i Ekwipunek.
- Wolna odpowiedź zmienia komunikat bez dokładania kolejnego okna.
- Błąd lub timeout oferuje bezpieczne ponowienie i nie zapisuje fałszywego wyniku.

## LED-y

- Zmiana legalnych pól jest płynna i nie zawiera widocznej czarnej klatki.
- Identyczny stan nie powoduje migotania ani ponownego rozbłysku.
- Animacja ataku dystansowego biegnie od źródła do celu, zachowując kontekst
  aktora i pola walki, a po zakończeniu przywraca właściwe podświetlenie.
- Obszary, stożki i linie pozostają czytelne przed zatwierdzeniem.

## Przebieg referencyjny

1. Uruchom scenariusz testowy i przejdź setup mapy.
2. Wybierz co najmniej dwa kafelki interakcji w wiosce wyłącznie planszą.
3. Wykonaj po jednym działaniu: skryptowym bez opisu, z opisem opcjonalnym oraz
   z oceną Gemini.
4. Przejdź do strażnicy i sprawdź anulowanie skanu przez wybór ekranowy.
5. Rozpocznij walkę, wykonaj ruch, atak dystansowy i czar obszarowy.
6. Poczekaj na jeden timeout skanu, ponów i dokończ wybór.
7. W trakcie odpowiedzi Gemini otwórz boczny panel i wróć do czatu.

Test jest zaliczony, jeśli żaden krok nie uruchamia się podwójnie, stary skan nie
zmienia nowego promptu, a gracz ani razu nie musi zgadywać, czy aplikacja czeka na
planszę, rzut, opis czy odpowiedź Gemini.
