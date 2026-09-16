"""Species reference: vector status and disease association per model class.

Transcribed from ``VectorGate_mosquito_reference_consolidated.xlsx`` (sheet
``Consolidated``), which merges two literature compilations with provenance
preserved. It is held here as code rather than read from the workbook at
runtime because the workbook is a working document, not a deployment artifact.

What these records are, and are not
-----------------------------------
A disease association is a published, species-level fact: this species is a
known vector for these diseases somewhere in its range. It is not a statement
about the individual insect that triggered a detection. VectorGate measures
wingbeat signatures optically. It does not detect pathogens, test any mosquito
for infection, diagnose illness, or estimate transmission risk. A detection
labelled *Aedes aegypti* means the classifier matched a wingbeat signature; it
does not mean dengue is present.

Classification is also uncertain in a way the dashboard must not hide.
Wingbeat frequency ranges overlap heavily between species -- Kim et al. 2021
found 26 of 29 North American species overlapping with at least one other -- so
a species label is a probabilistic match, reported with its confidence, and
anything below threshold is returned as Unknown.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

#: Shown wherever disease associations appear. Keep it attached to the data.
DISEASE_DISCLAIMER = (
    "Disease associations are published species-level vector facts, not findings about "
    "this detection. VectorGate measures wingbeat signatures only: it does not detect "
    "pathogens, test mosquitoes for infection, or indicate disease presence or risk."
)

#: Groups the diseases for display. Not a clinical taxonomy.
TRANSMISSION_GROUPS = {
    "arbovirus": "Mosquito-borne virus",
    "parasite": "Parasitic infection",
    "filarial": "Parasitic worm infection",
}


@dataclass(frozen=True)
class Disease:
    name: str
    group: str
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpeciesReference:
    """One model class, with everything the dashboard needs to describe it."""

    key: str
    scientific_name: str
    common_name: str
    genus: str
    vector_status: str
    headline_disease: str
    diseases: list[Disease]
    india_relevance: str
    evidence_level: str
    sources: list[str]
    notes: str = ""
    is_unknown: bool = False

    def as_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["diseases"] = [disease.as_dict() for disease in self.diseases]
        return record


_DENGUE_GROUP = [
    Disease("Dengue", "arbovirus"),
    Disease("Chikungunya", "arbovirus"),
    Disease("Zika", "arbovirus"),
]

SPECIES: tuple[SpeciesReference, ...] = (
    SpeciesReference(
        key="Ae. aegypti",
        scientific_name="Aedes aegypti",
        common_name="Yellow fever mosquito",
        genus="Aedes",
        vector_status="Established vector",
        headline_disease="Dengue",
        diseases=[*_DENGUE_GROUP, Disease("Yellow fever", "arbovirus")],
        india_relevance=(
            "Recognised dengue and chikungunya vector in India, monitored under the "
            "NCVBDC/NVBDCP programme."
        ),
        evidence_level="High",
        sources=[
            "Mandal et al. 2024 (Acta Tropica)",
            "Kim et al. 2021 (Scientific Reports)",
            "WHO / NCVBDC",
        ],
        notes=(
            "Only females bite and transmit. Day-biting and strongly associated with "
            "stored water in urban settings."
        ),
    ),
    SpeciesReference(
        key="Ae. albopictus",
        scientific_name="Aedes albopictus",
        common_name="Asian tiger mosquito",
        genus="Aedes",
        vector_status="Established vector",
        headline_disease="Dengue",
        diseases=list(_DENGUE_GROUP),
        india_relevance=(
            "Identified as a dengue vector in an Indian field vector-composition study, "
            "though at very low relative abundance (0.05%) in that survey."
        ),
        evidence_level="High",
        sources=["Mandal et al. 2024 (Acta Tropica)", "Peer-reviewed acoustic studies"],
        notes="Container-breeding and expanding in range; secondary to Ae. aegypti for dengue.",
    ),
    SpeciesReference(
        key="An. gambiae",
        scientific_name="Anopheles gambiae",
        common_name="African malaria mosquito",
        genus="Anopheles",
        vector_status="Established vector",
        headline_disease="Malaria",
        diseases=[Disease("Malaria", "parasite", "Plasmodium spp., transmitted by females")],
        india_relevance=(
            "Primary Afrotropical malaria vector. Not an established Indian vector species "
            "in the sources reviewed."
        ),
        evidence_level="Medium",
        sources=["Peer-reviewed acoustic studies"],
        notes="Part of the An. gambiae species complex, whose members are hard to separate morphologically.",
    ),
    SpeciesReference(
        key="An. arabiensis",
        scientific_name="Anopheles arabiensis",
        common_name="Member of the An. gambiae complex",
        genus="Anopheles",
        vector_status="Established vector",
        headline_disease="Malaria",
        diseases=[Disease("Malaria", "parasite", "Plasmodium spp., transmitted by females")],
        india_relevance=(
            "Major Afrotropical malaria vector. Not recorded as an established Indian vector "
            "in the sources reviewed."
        ),
        evidence_level="High",
        sources=["Peer-reviewed acoustic studies"],
        notes="Sibling species of An. gambiae; the two are the hardest pair for this classifier to separate.",
    ),
    SpeciesReference(
        key="C. quinquefasciatus",
        scientific_name="Culex quinquefasciatus",
        common_name="Southern house mosquito",
        genus="Culex",
        vector_status="Established vector",
        headline_disease="Lymphatic filariasis",
        diseases=[
            Disease("Lymphatic filariasis", "filarial", "Wuchereria bancrofti"),
            Disease("Japanese encephalitis", "arbovirus"),
            Disease("West Nile virus", "arbovirus"),
        ],
        india_relevance=(
            "Listed as a lymphatic filariasis vector, co-associated with Japanese encephalitis, "
            "in an Indian field vector-composition study."
        ),
        evidence_level="High",
        sources=[
            "Kim et al. 2021 (Scientific Reports)",
            "WHO / NCVBDC",
            "Peer-reviewed acoustic studies",
        ],
        notes="Night-biting and tolerant of polluted water; common in urban India.",
    ),
    SpeciesReference(
        key="C. pipiens",
        scientific_name="Culex pipiens",
        common_name="Northern house mosquito",
        genus="Culex",
        vector_status="Documented vector",
        headline_disease="West Nile virus",
        diseases=[
            Disease("West Nile virus", "arbovirus"),
            Disease("St. Louis encephalitis", "arbovirus"),
        ],
        india_relevance="Not recorded as an Indian vector in the reference set.",
        evidence_level="High",
        sources=["Peer-reviewed acoustic studies"],
        notes="Temperate-zone counterpart of C. quinquefasciatus; the two hybridise where ranges meet.",
    ),
)

UNKNOWN = SpeciesReference(
    key="UNKNOWN",
    scientific_name="Unresolved signature",
    common_name="Below classifier confidence threshold",
    genus="",
    vector_status="Not determined",
    headline_disease="Not determined",
    diseases=[],
    india_relevance="",
    evidence_level="",
    sources=[],
    notes=(
        "The wingbeat signature did not match any trained species above the confidence "
        "threshold. Reported as Unknown rather than forced into the nearest class. "
        "Non-target insects and mechanical sources such as a fan land here."
    ),
    is_unknown=True,
)

_BY_KEY: dict[str, SpeciesReference] = {record.key: record for record in (*SPECIES, UNKNOWN)}


def get(key: str | None) -> SpeciesReference | None:
    """Look up one class label, or ``None`` when it is not a known class."""
    if key is None:
        return None
    return _BY_KEY.get(key)


def all_species() -> list[SpeciesReference]:
    return [*SPECIES, UNKNOWN]
