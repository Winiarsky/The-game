"""Player-facing explanations for species and background features.

These descriptions explain both the 2014 rule intent and the concrete runtime
contract used by this board-assisted implementation.  They are deliberately
kept outside Flask so completeness can be audited in unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .implementation_audit import FeatureImplementationKind, feature_implementation_kind
from .models import CharacterCatalog


class OriginFeatureUseMode(StrEnum):
    AUTOMATIC = "automatic"
    CREATOR = "creator"
    ACTION = "action"
    CONTEXTUAL = "contextual"
    TABLE_ASSISTED = "table_assisted"


_USE_MODE_LABELS = {
    OriginFeatureUseMode.AUTOMATIC: "Działa automatycznie",
    OriginFeatureUseMode.CREATOR: "Rozliczane w kreatorze",
    OriginFeatureUseMode.ACTION: "Osobna akcja w grze",
    OriginFeatureUseMode.CONTEXTUAL: "Dostępne w pasującej scenie",
    OriginFeatureUseMode.TABLE_ASSISTED: "Obsługa przy stole lub przez scenariusz",
}


@dataclass(frozen=True, slots=True)
class OriginFeatureHelp:
    id: str
    name: str
    rule_text: str
    game_text: str
    use_mode: OriginFeatureUseMode

    @property
    def use_mode_label(self) -> str:
        return _USE_MODE_LABELS[self.use_mode]

    @property
    def implementation_kind(self) -> FeatureImplementationKind | None:
        return feature_implementation_kind(self.id)

    @property
    def accessibility_text(self) -> str:
        return (
            f"{self.name}. {self.rule_text} "
            f"W grze: {self.game_text} {self.use_mode_label}."
        )


@dataclass(frozen=True, slots=True)
class OriginFeatureCoverage:
    feature_ids: frozenset[str]
    missing_help_ids: tuple[str, ...]
    missing_runtime_contract_ids: tuple[str, ...]
    background_feature_ids_without_permissions: tuple[str, ...]
    table_assisted_feature_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return (
            not self.missing_help_ids
            and not self.missing_runtime_contract_ids
            and not self.background_feature_ids_without_permissions
        )


def _help(
    feature_id: str,
    name: str,
    rule_text: str,
    game_text: str,
    use_mode: OriginFeatureUseMode,
) -> OriginFeatureHelp:
    return OriginFeatureHelp(feature_id, name, rule_text, game_text, use_mode)


_ORIGIN_FEATURE_HELP = {
    item.id: item
    for item in (
        _help(
            "human_versatility",
            "Ludzka wszechstronność",
            "Każda z sześciu cech zwiększa się o 1, a postać wybiera dodatkowy język.",
            "Premie są doliczane do wartości końcowych, a wybrany język trafia na kartę postaci.",
            OriginFeatureUseMode.CREATOR,
        ),
        _help(
            "darkvision",
            "Widzenie w ciemności",
            "W półmroku widzisz jak w jasnym świetle, a w ciemności jak w półmroku, do zasięgu rasy.",
            "Silnik widoczności automatycznie uwzględnia zasięg zmysłu podczas eksploracji i walki.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "fey_ancestry",
            "Fey Ancestry",
            "Masz przewagę w rzutach obronnych przeciw zauroczeniu, a magia nie może cię uśpić.",
            "Przewaga i odporność na magiczny sen są nakładane automatycznie na oznaczone efekty.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "trance",
            "Trans",
            "Cztery godziny medytacji dają korzyści odpowiadające ośmiu godzinom snu.",
            "Pełny odpoczynek tej postaci wymaga 240 zamiast 480 minut.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "elf_weapon_training",
            "Elfie wyszkolenie bronią",
            "Otrzymujesz biegłość w długim i krótkim mieczu oraz długim i krótkim łuku.",
            "Biegłości są zapisane na postaci i używane przy wyliczaniu ataków.",
            OriginFeatureUseMode.CREATOR,
        ),
        _help(
            "high_elf_cantrip",
            "Elficki cantrip",
            "Znasz jeden wybrany cantrip czarodzieja; jego cechą czarującą jest Inteligencja.",
            "Wybrany cantrip trafia do legalnych akcji postaci i nie zużywa slotu.",
            OriginFeatureUseMode.CREATOR,
        ),
        _help(
            "dwarven_resilience",
            "Krasnoludzka odporność",
            "Masz przewagę w rzutach obronnych przeciw truciźnie i odporność na obrażenia od trucizny.",
            "Silnik automatycznie ustawia przewagę oraz zmniejsza odpowiednie obrażenia o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "dwarven_speed",
            "Krasnoludzki pewny krok",
            "Ciężki pancerz nie zmniejsza twojej szybkości z powodu zbyt niskiej Siły.",
            "Kalkulator ruchu pomija karę pancerza, zachowując bazową szybkość krasnoluda.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "stonecunning",
            "Znajomość kamienia",
            "Do testów Historii dotyczących pochodzenia kamiennych konstrukcji dodajesz podwójną premię z biegłości.",
            "Premia jest dodawana automatycznie, gdy scenariusz oznaczy test tagiem wiedzy o kamieniu.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "dwarven_toughness",
            "Krasnoludzka wytrzymałość",
            "Maksymalne PW zwiększa się o 1 na każdym poziomie postaci.",
            "Dodatkowe PW są wliczane podczas tworzenia postaci i awansu.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "lucky",
            "Szczęście",
            "Gdy wyrzucisz naturalne 1 w ataku, teście cechy lub rzucie obronnym, przerzucasz tę kość.",
            "UI prosi o fizyczny przerzut i zachowuje oba wyniki w rozstrzygnięciu.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "brave",
            "Odważny",
            "Masz przewagę w rzutach obronnych przeciw przerażeniu.",
            "Przewaga pojawia się automatycznie przy efektach oznaczonych jako strach.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "halfling_nimbleness",
            "Niziołcza zwinność",
            "Możesz przechodzić przez pola istot większych od ciebie.",
            "Pathfinding pozwala przejść przez takie pole jako trudny teren, ale nie zakończyć na nim ruchu.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "naturally_stealthy",
            "Naturalna skrytość",
            "Możesz próbować ukryć się za istotą większą od siebie.",
            "System widoczności uznaje większą istotę na linii obserwacji za zasłonę umożliwiającą ukrycie.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "breath_weapon",
            "Smoczy oddech",
            "Raz na odpoczynek zioniesz energią swojego pochodzenia w stożku lub linii; cele wykonują odpowiedni rzut obronny.",
            "Oddech jest osobną akcją obszarową z podświetleniem pól, fizycznym rzutem obrażeń i zasobem odnawianym po odpoczynku.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_acid_line_dex",
            "Oddech: linia kwasu",
            "Smoczy oddech tworzy linię kwasu; cele wykonują rzut obronny na Zręczność.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_lightning_line_dex",
            "Oddech: linia błyskawicy",
            "Smoczy oddech tworzy linię błyskawicy; cele wykonują rzut obronny na Zręczność.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_fire_line_dex",
            "Oddech: linia ognia",
            "Smoczy oddech tworzy linię ognia; cele wykonują rzut obronny na Zręczność.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_fire_cone_dex",
            "Oddech: stożek ognia",
            "Smoczy oddech tworzy stożek ognia; cele wykonują rzut obronny na Zręczność.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_poison_cone_con",
            "Oddech: stożek trucizny",
            "Smoczy oddech tworzy stożek trucizny; cele wykonują rzut obronny na Kondycję.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "breath_weapon_cold_cone_con",
            "Oddech: stożek zimna",
            "Smoczy oddech tworzy stożek zimna; cele wykonują rzut obronny na Kondycję.",
            "Wybrana genealogia ustawia kształt, typ obrażeń i właściwy rzut obronny akcji Smoczy oddech.",
            OriginFeatureUseMode.ACTION,
        ),
        _help(
            "damage_resistance_acid",
            "Odporność na kwas",
            "Masz odporność na obrażenia od kwasu.",
            "Silnik automatycznie zmniejsza obrażenia od kwasu o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "damage_resistance_lightning",
            "Odporność na błyskawice",
            "Masz odporność na obrażenia od błyskawic.",
            "Silnik automatycznie zmniejsza obrażenia od błyskawic o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "damage_resistance_fire",
            "Odporność na ogień",
            "Masz odporność na obrażenia od ognia.",
            "Silnik automatycznie zmniejsza obrażenia od ognia o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "damage_resistance_poison",
            "Odporność na truciznę",
            "Masz odporność na obrażenia od trucizny.",
            "Silnik automatycznie zmniejsza obrażenia od trucizny o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "damage_resistance_cold",
            "Odporność na zimno",
            "Masz odporność na obrażenia od zimna.",
            "Silnik automatycznie zmniejsza obrażenia od zimna o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "gnome_cunning",
            "Gnomi spryt",
            "Masz przewagę w rzutach obronnych na Inteligencję, Mądrość i Charyzmę przeciw magii.",
            "Przewaga jest dodawana automatycznie do magicznych efektów używających jednej z tych cech.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "artificers_lore",
            "Wiedza rzemieślnicza",
            "Do odpowiednich testów Historii dotyczących magii, alchemii lub technologii dodajesz podwójną premię z biegłości.",
            "Premia działa automatycznie w testach oznaczonych przez scenariusz tagiem wiedzy rzemieślniczej.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "tinker",
            "Majsterkowicz",
            "Za pomocą narzędzi majsterkowicza możesz tworzyć niewielkie mechaniczne urządzenia o prostym działaniu.",
            "Biegłość w narzędziach jest aktywna. Samo urządzenie wymaga pasującej receptury lub okazji przygotowanej w scenariuszu; nie istnieje jeszcze uniwersalny kreator takich gadżetów.",
            OriginFeatureUseMode.TABLE_ASSISTED,
        ),
        _help(
            "skill_versatility",
            "Wszechstronność umiejętności",
            "Otrzymujesz biegłość w dwóch wybranych umiejętnościach.",
            "Wybrane biegłości trafiają na kartę i automatycznie wpływają na odpowiednie testy.",
            OriginFeatureUseMode.CREATOR,
        ),
        _help(
            "relentless_endurance",
            "Nieustępliwa wytrzymałość",
            "Raz na długi odpoczynek, gdy obrażenia obniżyłyby twoje PW do 0 bez natychmiastowej śmierci, pozostajesz z 1 PW.",
            "Silnik uruchamia efekt automatycznie i zużywa odnawiany zasób.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "savage_attacks",
            "Brutalne ataki",
            "Przy trafieniu krytycznym bronią wręcz dodajesz jeszcze jedną kość obrażeń broni.",
            "Dodatkowa kość jest automatycznie dopisywana do instrukcji obrażeń trafienia krytycznego.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "hellish_resistance",
            "Odporność na ogień",
            "Masz odporność na obrażenia od ognia.",
            "Silnik automatycznie zmniejsza obrażenia od ognia o połowę.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "infernal_legacy",
            "Piekielne dziedzictwo",
            "Otrzymujesz Thaumaturgy, a na kolejnych poziomach jednorazowe Hellish Rebuke i Darkness.",
            "Czary są dodawane zgodnie z poziomem, nie zużywają zwykłych slotów i odnawiają się po długim odpoczynku.",
            OriginFeatureUseMode.AUTOMATIC,
        ),
        _help(
            "shelter_of_the_faithful",
            "Opieka współwyznawców",
            "W odpowiedniej wspólnocie religijnej możesz oczekiwać podstawowej pomocy, opieki i schronienia.",
            "Opcja pojawi się tylko w scenie oznaczonej jako wspierająca dane uprawnienie; silnik sprawdza pochodzenie postaci przed jej użyciem.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "false_identity",
            "Fałszywa tożsamość",
            "Posiadasz przygotowaną drugą tożsamość wraz z potrzebnymi dokumentami i wiarygodną historią.",
            "W pasującej interakcji możesz powołać się na przykrywkę bez jej ponownego tworzenia. Scenariusz nadal może wymagać testu, jeśli ktoś ma powód ją podejrzewać.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "criminal_contact",
            "Kontakt w półświatku",
            "Znasz pośrednika pozwalającego przekazywać wiadomości do lokalnej sieci przestępczej.",
            "W scenie z dostępnym półświatkiem otrzymasz specjalną opcję nawiązania kontaktu; nie oznacza ona automatycznego spełnienia każdej prośby.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "by_popular_demand",
            "Popularny artysta",
            "W miejscu, gdzie możesz występować, zwykle znajdujesz skromne utrzymanie i nocleg w zamian za występ.",
            "Pasująca karczma lub społeczność może udostępnić opcję występu i zakwaterowania bez standardowej opłaty.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "rustic_hospitality",
            "Wiejska gościnność",
            "Zwykli ludzie są skłonni ukryć cię, nakarmić lub zapewnić odpoczynek, o ile nie narażasz ich bezpośrednio.",
            "W przyjaznej społeczności scenariusz może udostępnić specjalną opcję schronienia dla drużyny.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "guild_membership",
            "Członkostwo w gildii",
            "Możesz liczyć na kontakty, informacje i ograniczone wsparcie swojej organizacji zawodowej.",
            "Opcja wsparcia pojawia się przy właściwej gildii lub jej przedstawicielu; zakres pomocy określa scena.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "discovery",
            "Odkrycie",
            "Podczas odosobnienia poznałeś ważną prawdę, sekret albo wskazówkę ustaloną dla tej postaci.",
            "Postać zachowuje uprawnienie do powołania się na odkrycie, gdy scenariusz przygotuje związany z nim moment. Konkretna treść wymaga ustalenia z graczami.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "position_of_privilege",
            "Uprzywilejowana pozycja",
            "Twój status ułatwia uzyskanie audiencji i sprawia, że ludzie wysokiego stanu traktują cię jak członka swojej sfery.",
            "Pasujące sceny społeczne mogą udostępnić audiencję lub uprzywilejowane przyjęcie bez zwykłego zdobywania dostępu.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "wanderer",
            "Wędrowiec",
            "Dobrze pamiętasz teren i potrafisz zdobywać żywność oraz wodę tam, gdzie środowisko na to pozwala.",
            "Podróż lub eksploracja może udostępnić automatyczne rozpoznanie geografii albo zdobywanie zapasów; niedostępne zasoby nadal nie powstają z niczego.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "researcher",
            "Badacz",
            "Jeżeli nie znasz potrzebnej informacji, zwykle wiesz, gdzie lub u kogo można jej szukać.",
            "Scena może wskazać wiarygodne źródło wiedzy albo odblokować drogę do niego; profit nie daje automatycznie samej odpowiedzi.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "ships_passage",
            "Przejazd statkiem",
            "Możesz próbować zapewnić drużynie bezpłatny przejazd na przyjaznym statku, pomagając załodze podczas podróży.",
            "W porcie lub przy odpowiedniej załodze scenariusz może odblokować przeprawę; termin i trasa zależą od dostępnego statku.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "military_rank",
            "Stopień wojskowy",
            "Żołnierze rozpoznający twoją dawną organizację respektują rangę i mogą udzielić ograniczonej pomocy.",
            "Przy właściwej formacji pojawi się opcja powołania na rangę albo prośby o pomoc; nie daje ona kontroli nad dowolnymi wojskami.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
        _help(
            "city_secrets",
            "Sekrety miasta",
            "Znasz miejskie skróty i rytm ulic, dzięki czemu poza walką szybciej przemieszczasz się między punktami miasta.",
            "Na mapie miejskiej scenariusz może udostępnić krótszą trasę lub mniejszy koszt czasu podróży.",
            OriginFeatureUseMode.CONTEXTUAL,
        ),
    )
}


def origin_feature_help(feature_id: str) -> OriginFeatureHelp | None:
    return _ORIGIN_FEATURE_HELP.get(feature_id)


def all_origin_feature_help() -> tuple[OriginFeatureHelp, ...]:
    return tuple(_ORIGIN_FEATURE_HELP.values())


def audit_origin_feature_coverage(
    catalog: CharacterCatalog,
) -> OriginFeatureCoverage:
    species_feature_ids = {
        feature_id
        for species in catalog.species
        for feature_id in (
            *species.trait_ids,
            *(
                feature_id
                for variant in species.variant_choices
                for feature_id in variant.trait_ids
            ),
        )
    }
    background_feature_ids = {
        feature_id
        for background in catalog.backgrounds
        for feature_id in background.feature_ids
    }
    feature_ids = frozenset((*species_feature_ids, *background_feature_ids))
    background_feature_ids_without_permissions = tuple(
        sorted(
            feature_id
            for background in catalog.backgrounds
            if not background.permission_ids
            for feature_id in background.feature_ids
        )
    )
    return OriginFeatureCoverage(
        feature_ids=feature_ids,
        missing_help_ids=tuple(
            sorted(feature_ids - _ORIGIN_FEATURE_HELP.keys())
        ),
        missing_runtime_contract_ids=tuple(
            sorted(
                feature_id
                for feature_id in feature_ids
                if feature_implementation_kind(feature_id) is None
            )
        ),
        background_feature_ids_without_permissions=(
            background_feature_ids_without_permissions
        ),
        table_assisted_feature_ids=tuple(
            sorted(
                feature_id
                for feature_id in feature_ids
                if feature_implementation_kind(feature_id)
                == FeatureImplementationKind.TABLE_ASSISTED
            )
        ),
    )


__all__ = [
    "OriginFeatureCoverage",
    "OriginFeatureHelp",
    "OriginFeatureUseMode",
    "all_origin_feature_help",
    "audit_origin_feature_coverage",
    "origin_feature_help",
]
