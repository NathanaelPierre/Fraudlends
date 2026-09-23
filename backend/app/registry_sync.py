"""
Loads the registry_data.py snapshot into the RegistryEntity table.
Run this once after setting up the database, and re-run any time
registry_data.py is updated with fresher entries, it is idempotent
(clears and reloads), so re-running is always safe.

Usage:
    python -m app.registry_sync
"""
from datetime import datetime
from app.database import SessionLocal, engine, Base
from app import models
from app.entity_matcher import normalize_name
from app.registry_data import get_all_registry_entities, KNOWN_ALIASES, FSC_REVOKED_OR_SURRENDERED_ENTITIES

_SOURCE_URLS = {
    "BOM": "https://www.bom.mu/financial-stability/supervision/mcib/list-participants",
    "FSC": "https://www.fscmauritius.org/en/supervision/register-of-licensees-search-by-name",
}


def sync_registry():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_count = db.query(models.RegistryEntity).count()
        db.query(models.RegistryEntity).delete()
        db.commit()

        entities = get_all_registry_entities()
        for name, category, source in entities:
            entity = models.RegistryEntity(
                name=name,
                normalized_name=normalize_name(name),
                source=source,
                license_type=category,
                status="Active",
                source_url=_SOURCE_URLS[source],
                last_synced_at=datetime.utcnow(),
            )
            db.add(entity)

        # Known public aliases/abbreviations (e.g. "MCB" for "The
        # Mauritius Commercial Bank Ltd") are loaded as additional
        # entries alongside the formal names — see registry_data.py's
        # KNOWN_ALIASES docstring for why this is needed: short public
        # names don't reliably fuzzy-match their much longer formal
        # legal names, so "MCB" alone scored only 42.9% against "The
        # Mauritius Commercial Bank Ltd" without this. The alias entry
        # stores the REAL formal name in `name` (so results always show
        # the entity's proper registered name), with the alias only
        # used as the searchable normalized_name. All current aliases
        # map to BoM entities, hence the fixed source below — revisit
        # if an FSC-entity alias is ever added.
        for alias, real_name in KNOWN_ALIASES.items():
            entity = models.RegistryEntity(
                name=real_name,
                normalized_name=normalize_name(alias),
                source="BOM",
                license_type="Known Alias",
                status="Active",
                source_url=_SOURCE_URLS["BOM"],
                last_synced_at=datetime.utcnow(),
            )
            db.add(entity)

        # Entities named in real, dated FSC public notices as having
        # had their license surrendered or revoked — loaded with their
        # actual status (not "Active"), so entity_matcher.py's "revoked"
        # branch has real data to surface a specific, sourced fact
        # ("this entity's license was surrendered on X date") instead
        # of a generic not_found for a name that WAS genuinely real.
        for name, status_detail in FSC_REVOKED_OR_SURRENDERED_ENTITIES:
            entity = models.RegistryEntity(
                name=name,
                normalized_name=normalize_name(name),
                source="FSC",
                license_type="Investment Dealer / Forex Broker",
                status=status_detail,
                source_url=_SOURCE_URLS["FSC"],
                last_synced_at=datetime.utcnow(),
            )
            db.add(entity)

        db.commit()

        new_count = db.query(models.RegistryEntity).count()
        print(f"Registry sync complete: removed {existing_count} old entries, loaded {new_count} entities.")
    finally:
        db.close()


if __name__ == "__main__":
    sync_registry()
