"""Player-facing explanations for class features granted at level 1."""

from __future__ import annotations

from dataclasses import dataclass

from .feature_help import OriginFeatureHelp, OriginFeatureUseMode
from .implementation_audit import feature_implementation_kind
from .models import CharacterCatalog


def _help(
    feature_id: str,
    name: str,
    rule_text: str,
    game_text: str,
    use_mode: OriginFeatureUseMode,
) -> OriginFeatureHelp:
    return OriginFeatureHelp(feature_id, name, rule_text, game_text, use_mode)


_CLASS_FEATURE_HELP = {
    item.id: item
    for item in (
        _help("rage", "Szał", "Jako akcję dodatkową wpadasz w szał: zyskujesz przewagę w testach i rzutach obronnych Siły, premię do obrażeń ataków wręcz opartych na Sile oraz odporność na obrażenia kłute, cięte i obuchowe.", "Przycisk Szał zużywa jedno użycie, nakłada efekty i pilnuje warunków oraz czasu trwania.", OriginFeatureUseMode.ACTION),
        _help("unarmored_defense_constitution", "Obrona bez pancerza (Kondycja)", "Bez pancerza twoja KP wynosi 10 + modyfikator Zręczności + modyfikator Kondycji; możesz używać tarczy.", "Kreator automatycznie wylicza ten wariant KP i silnik wybiera najlepszą legalną wartość.", OriginFeatureUseMode.AUTOMATIC),
        _help("spellcasting", "Rzucanie czarów", "Otrzymujesz sztuczki, czary i sloty właściwe dla klasy oraz używasz jej cechy czarującej.", "Kreator pilnuje legalnych wyborów, a runtime rozlicza sloty, cele, testy, rzuty obronne i efekty czarów.", OriginFeatureUseMode.CREATOR),
        _help("bardic_inspiration", "Inspiracja bardowska", "Akcją dodatkową dajesz sojusznikowi kość k6, którą może dodać do jednego testu cechy, ataku lub rzutu obronnego.", "Akcja wybiera sojusznika, zużywa użycie i udostępnia kość przy odpowiednich rzutach.", OriginFeatureUseMode.ACTION),
        _help("divine_domain", "Domena boska", "Na 1. poziomie wybierasz domenę, która przyznaje dodatkowe zdolności i czary domenowe.", "Wybór domeny pojawia się w wyborach klasowych, a jej profity są kompilowane na kartę postaci.", OriginFeatureUseMode.CREATOR),
        _help("druidic", "Druidycki", "Znasz sekretny język druidów i możesz zostawiać w nim ukryte wiadomości.", "Postać otrzymuje język i znacznik fabularny; treść wiadomości oraz reakcję świata rozstrzyga scena lub stół.", OriginFeatureUseMode.TABLE_ASSISTED),
        _help("fighting_style", "Styl walki", "Wybierasz specjalizację bojową, np. Obronę, Łucznictwo, Pojedynki albo Walkę dwiema broniami.", "Kreator wymaga jednego legalnego stylu, a jego premie są automatycznie stosowane w walce.", OriginFeatureUseMode.CREATOR),
        _help("second_wind", "Drugi oddech", "Akcją dodatkową odzyskujesz 1k10 + poziom wojownika punktów wytrzymałości; ponownie po krótkim lub długim odpoczynku.", "Osobna akcja wykonuje rzut, leczy postać, zużywa użycie i odnawia je po odpoczynku.", OriginFeatureUseMode.ACTION),
        _help("unarmored_defense_wisdom", "Obrona bez pancerza (Mądrość)", "Bez pancerza i tarczy twoja KP wynosi 10 + modyfikator Zręczności + modyfikator Mądrości.", "Kreator automatycznie wylicza ten wariant KP i silnik wybiera najlepszą legalną wartość.", OriginFeatureUseMode.AUTOMATIC),
        _help("martial_arts", "Sztuki walki", "Bez pancerza i tarczy możesz używać Zręczności z bronią mnisią, zadawać co najmniej k4 obrażeń i wykonać dodatkowy nieuzbrojony atak.", "Silnik poprawia źródła ataku i udostępnia legalny atak akcją dodatkową po spełnieniu warunków.", OriginFeatureUseMode.AUTOMATIC),
        _help("divine_sense", "Boski zmysł", "Akcją wykrywasz niebiańskich, czarty i nieumarłych w promieniu 60 stóp, jeśli nie mają pełnej osłony.", "Osobna akcja zużywa użycie i ujawnia pasujące, wykrywalne istoty na planszy.", OriginFeatureUseMode.ACTION),
        _help("lay_on_hands", "Nakładanie rąk", "Masz pulę leczenia równą 5 × poziom paladyna; akcją możesz leczyć dotknięty cel albo wydać 5 punktów na neutralizację trucizny lub choroby.", "Akcja pozwala wskazać cel i liczbę punktów, pilnuje zasięgu oraz rozlicza pulę leczenia.", OriginFeatureUseMode.ACTION),
        _help("favored_enemy", "Ulubiony wróg", "Wybierasz typ ulubionego wroga; masz przewagę w testach Przetrwania do tropienia go oraz Inteligencji do przypominania sobie o nim informacji.", "Wybór trafia na kartę, a oznaczone testy eksploracji automatycznie uwzględniają przewagę.", OriginFeatureUseMode.CREATOR),
        _help("natural_explorer", "Naturalny odkrywca", "Wybierasz ulubiony teren i podczas podróży w nim zyskujesz pakiet korzyści nawigacyjnych, tropiących i aprowizacyjnych.", "Wybór trafia do profilu podróży; system nawigacji stosuje korzyści w scenach oznaczonych odpowiednim terenem.", OriginFeatureUseMode.CREATOR),
        _help("expertise", "Ekspertyza", "Wybierasz dwie posiadane biegłości; przy ich testach podwajasz premię z biegłości.", "Kreator ogranicza wybór do posiadanych biegłości, a silnik testów automatycznie podwaja premię.", OriginFeatureUseMode.CREATOR),
        _help("sneak_attack", "Podstępny atak", "Raz na turę zadajesz dodatkowe 1k6 obrażeń trafionym atakiem finezyjnym lub dystansowym, gdy masz przewagę albo wróg jest związany walką z twoim sojusznikiem.", "Silnik wykrywa legalność, udostępnia wybór użycia i dopisuje dodatkową kość obrażeń tylko raz na turę.", OriginFeatureUseMode.AUTOMATIC),
        _help("thieves_cant", "Gwara złodziejska", "Znasz tajny kod mowy i znaków używany przez przestępców.", "Postać otrzymuje język i znacznik fabularny; znaczenie wiadomości rozstrzyga scena lub stół.", OriginFeatureUseMode.TABLE_ASSISTED),
        _help("sorcerous_origin", "Pochodzenie czarodzieja", "Na 1. poziomie wybierasz źródło wrodzonej magii, które przyznaje zdolności pochodzenia.", "Wybór pochodzenia pojawia się w wyborach klasowych, a jego profity są kompilowane na kartę.", OriginFeatureUseMode.CREATOR),
        _help("otherworldly_patron", "Nadnaturalny patron", "Na 1. poziomie wybierasz patrona, który przyznaje dodatkowe zdolności i rozszerza dostęp do czarów.", "Wybór patrona pojawia się w wyborach klasowych, a jego profity są kompilowane na kartę.", OriginFeatureUseMode.CREATOR),
        _help("pact_magic", "Magia paktu", "Znasz ograniczoną liczbę czarów czarnoksiężnika i rzucasz je ze slotów paktu odnawianych po krótkim lub długim odpoczynku.", "Kreator pilnuje znanych czarów, a runtime rozlicza osobne sloty paktu oraz ich regenerację.", OriginFeatureUseMode.CREATOR),
        _help("arcane_recovery", "Odzyskiwanie magiczne", "Raz dziennie po krótkim odpoczynku odzyskujesz zużyte sloty o łącznym poziomie nie większym niż połowa poziomu czarodzieja, zaokrąglona w górę.", "Podczas krótkiego odpoczynku interfejs oferuje legalny wybór slotów i pilnuje dziennego użycia.", OriginFeatureUseMode.ACTION),
    )
}


@dataclass(frozen=True, slots=True)
class ClassFeatureHelpCoverage:
    feature_ids: frozenset[str]
    missing_help_ids: tuple[str, ...]
    missing_runtime_contract_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_help_ids and not self.missing_runtime_contract_ids


def class_feature_help(feature_id: str) -> OriginFeatureHelp | None:
    return _CLASS_FEATURE_HELP.get(feature_id)


def all_class_feature_help() -> tuple[OriginFeatureHelp, ...]:
    return tuple(_CLASS_FEATURE_HELP.values())


def audit_level_one_class_feature_help(
    catalog: CharacterCatalog,
) -> ClassFeatureHelpCoverage:
    feature_ids = frozenset(
        feature_id
        for character_class in catalog.classes
        for feature_id in character_class.feature_ids
    )
    return ClassFeatureHelpCoverage(
        feature_ids=feature_ids,
        missing_help_ids=tuple(sorted(feature_ids - _CLASS_FEATURE_HELP.keys())),
        missing_runtime_contract_ids=tuple(
            sorted(
                feature_id
                for feature_id in feature_ids
                if feature_implementation_kind(feature_id) is None
            )
        ),
    )


__all__ = [
    "ClassFeatureHelpCoverage",
    "all_class_feature_help",
    "audit_level_one_class_feature_help",
    "class_feature_help",
]
