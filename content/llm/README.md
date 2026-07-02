# LLM Content

Ten katalog przechowuje ogólny content wspólny dla integracji LLM.

- `dnd5e_core_rules.json` - mały słownik bazowy D&D 5e używany w prompt payloadach i walidacji, np. cechy i umiejętności.
- `freeform_grounding_terms.json` - ogólne aliasy/hasła używane do wykrywania deklarowanych zasobów, które muszą istnieć w ekwipunku albo materiale sceny.
- `intent_catalog.json` - globalna lista intencji, których mogą używać interakcje NPC/obiektów. Scenariusz nie definiuje nowych typów intencji ad hoc, tylko lokalnie ustawia dla nich `allowed`, `blocked`, `locked` albo `allowed_with_consequence`.

Zasada odpowiedzialności:

- kod Pythona trzyma mechanikę walidacji i rozstrzygania,
- ten katalog trzyma ogólne słowniki i konfigurację LLM,
- scenariusze trzymają szczegółowy content interakcji, np. `llm_context`, `llm_policy`, konkretne zasoby, opcje i przeszkody.
