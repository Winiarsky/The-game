# Formularz Interakcji: Ranny Zwiadowca

## 1. Typ Interakcji
NPC

## 2. Nazwa
Ranny zwiadowca

Id robocze / obecne id: `wounded_scout`

## 3. Gdzie Na Mapie
- Strefa/lokacja: `courtyard` / Dziedziniec
- Pole albo obszar na planszy: `(8, 8)`
- Jawność: ukryty na starcie; ujawnia się po ukończeniu wyzwania `closed_gate`
- Status contentu: punkt istnieje w `points.json`, ale formularz opisuje docelową, bogatszą wersję interakcji

## 4. Opis Dla Graczy
Za zamkniętą bramą rozciąga się niewielki, zarośnięty dziedziniec dawnej strażnicy. Popękane kamienie są śliskie od wilgoci, a między nimi wyrosły kępy trawy, ciernie i dzikie pnącza. Po jednej stronie leżą resztki zawalonej drewnianej konstrukcji; stare deski czernieją od deszczu, a rdzewiejące metalowe elementy wystają z ziemi jak kości dawno martwego miejsca.

Wśród zarośli, częściowo oparty o omszały mur, leży ranny zwiadowca. Jego płaszcz jest rozdarty i ubłocony, oddech płytki, a jedna dłoń kurczowo zaciska się na pasku torby przewieszonej przez ramię. Na kamieniach obok niego widać ciemne ślady krwi rozmywane przez wilgoć. Gdy brama porusza się z głuchym skrzypnięciem, mężczyzna drga słabo i unosi głowę, jakby nie był pewien, czy usłyszał ratunek, czy coś znacznie gorszego.

## 5. Informacje Dla MG / LLM
Zwiadowca jest ranny, przestraszony i wycieńczony. Nie jest wrogiem, ale nie zaufa drużynie automatycznie. Boi się, że gracze są bandytami, goblinami albo ludźmi odpowiedzialnymi za atak.

Prawda scenariusza:
- Zwiadowca został ranny przez bestię grasującą w okolicy strażnicy.
- Bestią jest przeklęty komendant strażnicy, który przemienia się w sowoniedźwiedzia.
- Rany nie wyglądają jak zadane zwykłą bronią. To ważny trop.
- Zwiadowca widział, że coś ciężkiego przeciągnięto w stronę wieży obserwacyjnej.
- Zwiadowca ma torbę z meldunkami. Dla niego jest bardzo cenna, ale ma niewielką wartość rynkową.
- W rękawie ukrywa mały nóż. Użyje go tylko w desperacji, np. przy brutalnej kradzieży, próbie dobicia albo krytycznej porażce zastraszania.
- Pnącza, szmata z płaszcza i fragmenty materiału można wykorzystać jako improwizowany opatrunek/opaskę uciskową, ale tylko jeśli gracze sami szukają czegoś do stabilizacji krwotoku.

Zasady prowadzenia:
- Łagodne, konsyliacyjne podejście albo realna pomoc medyczna powinny ułatwiać zdobycie zaufania.
- Zastraszanie jest możliwe, ale trudne i ryzykowne.
- Kradzież jest możliwa, ale powinna mieć konsekwencje moralne i mechaniczne.
- Nie podawaj od razu wszystkich informacji. Kluczowe informacje są zablokowane flagami.
- Podpowiedzi dawaj dopiero, gdy gracze pytają albo wykonują działanie, które naturalnie je odsłania.

## 6. Rola Interakcji W Scenie
- [ ] cel sceny
- [x] trop/informacja
- [x] zasób: meldunki, możliwy trop do skrytki
- [x] ryzyko/komplikacja
- [ ] przejście do innej lokacji
- [ ] walka/encounter bezpośrednio
- [x] klimat
- [x] dylemat moralny
- [x] zapowiedź przyszłego encountera z bestią

## 7. Stan Początkowy
Dla NPC:
- emocje: przestraszony, podejrzliwy, obolały
- zdrowie: ciężko ranny, ale przytomny
- nastawienie do drużyny: nieufny
- co robi teraz: leży pod zawalonym wozem / przy zbutwiałej konstrukcji, ściska torbę z meldunkami
- zdolność rozmowy: może mówić krótkimi zdaniami
- zdolność obrony: bardzo ograniczona; ukryty nóż tylko jako desperacka reakcja

### 7A. Cele Widoczne Dla Graczy

- `calm_scout`: Uspokójcie zwiadowcę.
- `help_scout`: Udzielcie mu pomocy.
- `ask_scout`: Dowiedzcie się, co się stało; kafelek pojawia się dopiero po
  zdobyciu zaufania.
- `pressure_scout`: Wywrzyjcie presję.

Kafelka ogólnego „Własny sposób” nie ma. Gracze wybierają cel, ale sposób jego
osiągnięcia nadal opisują całkowicie swobodnie.

### 7AA. Flow Rozmowy

- `scout_untrusted`: dostępne są uspokojenie, pomoc i presja.
- `scout_trusted`: uspokojenie znika, a pojawia się możliwość zdobywania
  informacji; pomoc i presja pozostają dostępne.
- `calm_scout` prowadzi zawsze do intencji `social`.
- `help_scout` prowadzi zawsze do intencji `medical`.
- `ask_scout` prowadzi zawsze do intencji `information`.
- `pressure_scout` prowadzi zawsze do intencji `intimidation`.
- Flow wybiera intencję przed wywołaniem LLM. Model interpretuje metodę i
  odgrywa NPC, ale nie może przerzucić deklaracji na inny rodzaj działania.
- `medical` ma autorski test `wisdom/medicine`, ST 12. Sukces ustawia leczenie,
  stabilizację i zaufanie; porażka zapisuje komplikację medyczną.
- Dla `social` ST nadal wynika z deterministycznej tabeli nastawienia i
  sklasyfikowanego ryzyka prośby, natomiast flagi obu wyników pochodzą z policy,
  nie z odpowiedzi LLM.
- Przed opisaniem metody gracze wybierają prowadzącego i opcjonalnego
  pomocnika. Presję wykonuje dokładnie jedna postać.

### 7B. Kluczowe Kwestie NPC

- `reports_must_survive` (`priority`, ukryte): najważniejsze jest bezpieczne
  dostarczenie meldunków.
- Ugruntowana obietnica ich uratowania lub dostarczenia natychmiast uspokaja
  zwiadowcę i buduje zaufanie, bez rzutu.
- Kwestia działa tylko raz; zwykłe pytanie o zawartość torby nie jest obietnicą i
  nie powinno jej uruchomić.

### 7C. Styl Narracji

- Instancja: przygodowy ton D&D z lekkim, nerwowym humorem zwiadowcy.
- `ask_scout`: `serious_revelation`; zero humoru i ironii, wysoki dramatyzm.
- Kluczowa kwestia meldunków ma własną autorską narrację, więc nie potrzebuje
  dodatkowego żartu generowanego przez LLM.

## 8. Co Gracze Mogą Realnie Próbować
- uspokoić go i porozmawiać
- opatrzyć rany
- znaleźć improwizowany opatrunek w okolicy
- użyć pnączy jako opaski uciskowej
- zbadać charakter ran
- zapytać, co go zaatakowało
- zapytać, co widział na dziedzińcu albo przy wieży
- rozpoznać emblematy, przynależność, miasto albo rangę
- przeszukać okolice miejsca ataku
- spróbować ukraść torbę z meldunkami
- zabrać torbę siłą
- spróbować zauważyć ukryty nóż
- zastraszyć go
- zostawić go
- dobić go
- ukryć ewentualne zwłoki
- uciszyć go, jeśli zacznie panikować

## 9. Czego Nie Powinno Się Dać Zrobić
- Bez magii albo wyjątkowo mocnej dźwigni fabularnej nie da się natychmiast złamać jego woli.
- Nie da się bezpiecznie zabrać go ze sobą jako aktywnego towarzysza; jest zbyt ranny.
- Nie zna pełnego planu przeciwników.
- Nie wie, że komendant jest przeklęty, jeśli nie zostanie odpowiednio wypytany lub uspokojony; może opisać bestię, ale nie rozumie całej prawdy.
- Torba z meldunkami nie zawiera dużej ilości złota ani magicznego przedmiotu.
- Jeśli gracze nie szukają materiałów opatrunkowych, LLM nie powinien sam „dawać” im pnączy jako bonusu.

## 10. Intencje
Docelowo użyć `intent_permissions`, nie ad hoc `allowed_actions`.

Proponowany model intencji dla tego NPC:

```json
{
  "social": {
    "status": "allowed",
    "notes": "Uspokajanie, rozmowa, budowanie zaufania."
  },
  "medical": {
    "status": "allowed",
    "notes": "Opatrywanie, stabilizacja, badanie ran."
  },
  "information": {
    "status": "locked",
    "unlock_if_flags": ["scout_trusts_party"]
  },
  "search": {
    "status": "allowed",
    "notes": "Badanie ran, okolicy, śladów i emblematów."
  },
  "theft": {
    "status": "allowed_with_consequence",
    "limits": {
      "max_loot": "meldunki i drobiazgi osobiste",
      "no_significant_gold": true
    },
    "consequences": {
      "on_success": ["scout_robbed", "trust_lost"],
      "on_failure": ["scout_panicked", "noise_added"],
      "on_critical_failure": ["hidden_knife_response", "noise_added"]
    }
  },
  "harm": {
    "status": "allowed_with_consequence",
    "consequences": {
      "on_any": ["moral_consequence", "noise_added"],
      "on_kill": ["scout_dead"]
    }
  },
  "intimidation": {
    "status": "allowed_with_consequence",
    "uses_social_reaction": false,
    "check": {
      "ability": "charisma",
      "skill": "intimidation",
      "dc": 18
    },
    "notes": "Możliwe, ale trudne i ryzykowne. Zawsze prowadzi do rzutu zamiast automatycznej odmowy z tabeli reakcji społecznej."
  },
  "magic": {
    "status": "allowed_with_context",
    "notes": "Tylko jeśli gracz faktycznie ma odpowiedni czar lub zasób."
  },
  "trade": {
    "status": "blocked"
  },
  "gambling": {
    "status": "blocked"
  }
}
```

## 11. Informacje Do Odkrycia
Informacja 1:
- id robocze: `tower_hint`
- treść: Zwiadowca widział, jak gobliny albo napastnicy przeciągnęli coś ciężkiego w stronę wieży obserwacyjnej.
- warunek ujawnienia: `scout_stabilized` albo `scout_trusts_party`
- flaga po ujawnieniu: `tower_hint_learned`

Informacja 2:
- id robocze: `beast_hint`
- treść: Rany wyglądają jak po wielkich pazurach i dziobie; zwiadowca mamrocze o „czymś z sowią głową i cielskiem niedźwiedzia”.
- warunek ujawnienia: sukces przy badaniu ran albo rozmowa po uspokojeniu
- flaga po ujawnieniu: `beast_hint_learned`

Informacja 3:
- id robocze: `commander_curse_hint`
- treść: Zwiadowca rozpoznał fragment starego płaszcza komendanta albo znak strażnicy na bestii.
- warunek ujawnienia: krytyczny sukces przy wypytywaniu, badaniu ran/śladów albo połączeniu tropów
- flaga po ujawnieniu: `commander_curse_suspected`

Informacja 4:
- id robocze: `hidden_cache_hint`
- treść: Zwiadowca wskazuje luźną deskę przy wozie i mówi, że ukrył tam awaryjny nóż albo zwój unieruchamiający.
- warunek ujawnienia: `scout_trusts_party`
- flaga po ujawnieniu: `cache_hint_learned`

## 12. Możliwe Efekty Mechaniczne
Flagi NPC:
- `scout_calmed`
- `scout_treated`
- `scout_stabilized`
- `scout_trusts_party`
- `scout_panicked`
- `scout_robbed`
- `scout_dead`
- `trust_lost`

Flagi informacji:
- `tower_hint_learned`
- `beast_hint_learned`
- `commander_curse_suspected`
- `cache_hint_learned`

Zasoby możliwe do uzyskania:
- `scout_reports` / meldunki zwiadowcy
- implementacja: `theft/scout_reports` ma stały test i cztery wykonywalne gałęzie wyniku; `intimidation/scout_information` łączy te gałęzie z tabelą reakcji społecznej.
- `cache_key` albo `cache_hint`
- opcjonalnie `field_bandage_materials`, jeśli gracze znajdą i przygotują improwizowany opatrunek

Punkty/lokacje możliwe do ujawnienia:
- `hidden_cache`
- przyszły punkt: `beast_tracks` albo `commander_clue`

Komplikacje:
- `noise_added`
- `scout_panicked`
- `hidden_knife_response`
- `medical_complication`
- `beast_attention`

TODO mechaniczne:
- globalny licznik hałasu sceny
- próg hałasu, po którym bestia wchodzi do sceny i zaczyna się encounter
- model stanu NPC: `panicked`, `calmed`, `stabilized`, `dead`
- zasoby/loot table dla torby zwiadowcy

## 13. Testy I Trudności
Docelowa skala:
- łatwe: ST 10
- średnie: ST 12-13
- trudne: ST 15-16
- bardzo trudne: ST 18+

Sytuacje:
- uspokoić i porozmawiać: średnie, zwykle `charisma/persuasion`
- opatrzyć: średnie, zwykle `wisdom/medicine`
- znaleźć improwizowany opatrunek: łatwe, `wisdom/perception` albo `intelligence/investigation`
- użyć pnączy i szmat jako opaski: łatwe/średnie, zależnie od opisu
- zastraszyć: bardzo trudne, `charisma/intimidation`; porażka zwiększa panikę/hałas
- okraść po cichu: trudne, docelowo `dexterity/sleight_of_hand`; obecny policy może wymagać dopisania tej umiejętności
- zabrać torbę siłą: trudne, `strength/athletics` albo konflikt z konsekwencją `hidden_knife_response`
- zbadać rany: średnie, `wisdom/medicine` albo `intelligence/investigation`
- rozpoznać emblematy/jednostkę/rangę: łatwe, `intelligence/history` albo `intelligence/investigation`
- rozejrzeć się po okolicy pod kątem napastnika: średnie, `wisdom/survival` albo `wisdom/perception`
- zauważyć ukryty nóż: trudne, `wisdom/perception` albo krytyczny sukces przy bliskiej interakcji
- ukryć zwłoki: łatwe/średnie, zależnie od pośpiechu i hałasu
- uciszyć panikę bez krzywdzenia: średnie, `charisma/persuasion` albo `wisdom/medicine`, zależnie od opisu

## 14. Sukces / Porażka / Krytyczne Wyniki
Sukces:j
- NPC uspokaja się, daje część informacji albo pozwala sobie pomóc.
- Mechanicznie: ustawienie jednej z flag `scout_calmed`, `scout_treated`, `scout_stabilized`, `scout_trusts_party`.

Porażka:
- NPC pozostaje nieufny, wpada w ból albo reaguje paniką.
- Mechanicznie: `scout_panicked`, możliwy `noise_added`, brak dostępu do zablokowanej informacji.

Krytyczny sukces:
- NPC szybko ufa drużynie albo udaje się jednocześnie pomóc mu i wydobyć ważny trop.
- Mechanicznie: dodatkowa flaga, np. `scout_trusts_party` albo `beast_hint_learned`.
- Możliwa premia przyszła: advantage / bonus do pierwszego działania przeciw bestii, jeśli gracze dobrze wykorzystają trop.

Krytyczna porażka:
- NPC krzyczy, szarpie się, doznaje większego bólu albo próbuje bronić się ukrytym nożem.
- Mechanicznie: większy hałas, utrata zaufania, możliwa komplikacja `hidden_knife_response`.
- Implementacja: kradzież meldunków i zastraszanie prowadzą do
  `scout_knife_escalation`. UI zatrzymuje automatyczny alarm i pokazuje w czacie
  reakcje drużyny: wycofanie, próbę uspokojenia albo — gdy teren nie jest jeszcze
  zabezpieczony — pozostanie na miejscu i uruchomienie `scout_panic_alarm`.

## 15. Limity I Parametry
- maksymalna nagroda informacyjna: trop o wieży, trop o bestii, trop o przeklętym komendancie, trop o skrytce
- maksymalna nagroda materialna: meldunki, drobiazgi osobiste, ewentualny dostęp do skrytki
- brak dużego złota
- liczba prób: rozmowa może trwać kilka wymian, ale brutalne akcje szybko pogarszają stan NPC
- implementacja: test budowania zaufania ma dwie próby; druga wymaga wcześniejszego opatrzenia albo ustabilizowania zwiadowcy. Zastraszanie ma jedną próbę.
- koszt czasu: dłuższa pomoc medyczna może zwiększać ryzyko nadejścia bestii, jeśli hałas/scena to uzasadnia
- poziom hałasu: docelowo istotny globalny zasób sceny
- limit zasobów: zasoby medyczne tylko jeśli drużyna je ma albo znajdzie improwizowane materiały

## 16. Czy Interakcja Ma Progres?
Nie w formie paska progressu.

Lepszy model:
- stan NPC jako flagi/stany: `panicked -> calmed -> stabilized -> trusts_party`
- informacje zablokowane przez flagi
- konsekwencje długoterminowe zależne od tego, czy NPC przeżył i czy ufa drużynie

## 17. Konsekwencje Długoterminowe
- NPC pamięta pomoc, kradzież, groźby albo przemoc.
- Jeśli przeżyje i zaufa drużynie, może wrócić jako świadek albo sojusznik.
- Jeśli zostanie skrzywdzony, może pojawić się konsekwencja reputacyjna.
- Trop o bestii może zmienić przyszły encounter.
- Trop o komendancie może zmienić sposób rozwiązania klątwy.

## 18. Przykładowe Deklaracje Graczy
- "Spokojnie, nie zrobimy ci krzywdy, chcemy pomóc."
- "Opatrujemy mu ranę i odsuwamy deski."
- "Rozglądam się za czymś, czym mogę zatamować krwawienie."
- "Sprawdzam, czy rany wyglądają jak od broni, pazurów czy czegoś innego."
- "Pytamy, co widział na dziedzińcu."
- "Przeszukuję go, kiedy reszta odwraca jego uwagę."
- "Grożę mu, żeby powiedział wszystko od razu."
- "Próbuję zauważyć, czemu tak mocno trzyma torbę."
- "Zostawiamy go, ale staramy się go uciszyć, żeby nie ściągnął zagrożenia."

## 19. Oczekiwany Feeling
- [x] napięcie
- [x] tajemnica
- [ ] humor
- [x] moralny dylemat
- [ ] szybka przeszkoda
- [x] ważna rozmowa
- [x] groza
- [x] zapowiedź większego zagrożenia

## 20. Uwagi Implementacyjne
Obecny JSON `wounded_scout` jest prostszy niż ten formularz. Przy następnym etapie warto przenieść z formularza do contentu:
- pełniejszy `gm_context`
- `intent_permissions`
- nowe informacje: `beast_hint`, `commander_curse_hint`
- flagi `scout_dead`, `trust_lost`, `beast_hint_learned`, `commander_curse_suspected`
- policy dla `sleight_of_hand`, `survival`, `history`
- konsekwencje hałasu i próg wejścia bestii do encountera
- zasób `scout_reports`
