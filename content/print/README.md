# Kompletne wydruki

- [Misja 0 — kafle i handouty](../scenarios/misja_0_dzwon/maps/print/misja_0_komplet_A4.pdf)
- [Bohaterowie — karty i zestawy startowe](characters/bohaterowie_zestawy_startowe_A4.pdf)
- [Spis stron bohaterów](characters/bohaterowie_zestawy_startowe_A4.md)

Odbudowa: `python scripts/build_session_print_packs.py`.
Każdy bohater ma pięć arkuszy: postać i historia, mata many, akcje z runami,
pusta mata wyposażenia oraz startowy sprzęt do wycięcia. Na końcu kompletu
są wspólna ściągawka zasad i znaczniki pomocnicze. Ilość na żetonie stosu
określa liczbę sztuk. Nie trzeba dobierać osobnych PDF-ów ekwipunku.
Maty many i arkusz akcji Nimry są poziomo. Pozostałe strony są pionowo.
[Podgląd wszystkich postaci](characters/mats_v2/podglad.html) ·
[Instrukcja zestawu](characters/mats_v2/README.md).

Druk jednostronny A4, 100%, bez dopasowania. Kafle domyślnie mają dotychczasową
korektę 250/244. Dla nieskalowanej drukarki:
`python scripts/build_session_print_packs.py --only mission --nominal`.
Figurki, kości, wspólna talia many i posiadany podkład planszy są osobnymi,
wielokrotnie używanymi elementami. Starsze częściowe PDF-y można pominąć.
