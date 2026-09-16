"""Species reference route: vector status and disease association per class."""

from fastapi import APIRouter, HTTPException

from software.reference import species as reference

router = APIRouter(prefix="/species", tags=["species"])


@router.get("")
def list_species() -> dict:
    """Every class the classifier can emit, with its published vector associations."""
    return {
        "disclaimer": reference.DISEASE_DISCLAIMER,
        "transmission_groups": reference.TRANSMISSION_GROUPS,
        "species": [record.as_dict() for record in reference.all_species()],
    }


@router.get("/{key}")
def get_species(key: str) -> dict:
    record = reference.get(key)
    if record is None:
        raise HTTPException(status_code=404, detail="species not found")
    return {"disclaimer": reference.DISEASE_DISCLAIMER, **record.as_dict()}
