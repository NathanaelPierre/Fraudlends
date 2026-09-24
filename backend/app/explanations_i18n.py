"""
Translated explanation text for the fraud-check pipeline's output:
registry-status explanations, indicator descriptions, and evidence
summaries, in English, French, and Kreol Morisyen.

This is deliberately a separate module from routers/checks.py (which
previously held all English text inline) so translated strings live in
one place, are easy to review or extend, and don't bloat the pipeline
logic itself. checks.py selects the right language's dict based on
the message's detected language (see app/language_detector.py) and
falls back to English for any string that doesn't yet have a
translation in a given language, so a partially-translated language
degrades gracefully rather than showing a missing-key error.

Honest limitation: French translations were reviewed carefully; Kreol
translations are a first pass, following the exact same "distinctive
tactic, not exact translation" principle already established in
indicator_extractor.py's Kreol pattern comments. Mauritian Kreol has no
single standardized spelling system, so these reflect one reasonable
informal spelling choice, not an authoritative orthography. See this
project's README for this stated plainly as a known limitation.
"""
from typing import Optional

SUPPORTED_LANGUAGES = ("en", "fr", "cr")


REGISTRY_EXPLANATIONS = {
    "en": {
        "verified": "The sender you named matches an entity in the Bank of Mauritius registry snapshot used by FraudLens.",
        "not_found": "The sender you named was not found in the Bank of Mauritius registry snapshot used by FraudLens (banks and other regulated financial participants). This does not prove the sender doesn't exist anywhere, many legitimate senders such as courier services, retailers, or individuals are not financial institutions and wouldn't be expected to appear in this registry. But if this message claims to be from a bank or financial institution, that specific claim could not be confirmed against the registry snapshot.",
        "no_sender_given": "No sender name was provided, so no registry check could be performed.",
        "registry_unavailable": "The financial institution registry snapshot has not been loaded yet, so this check could not be completed. Contact an administrator.",
    },
    "fr": {
        "verified": "L'expéditeur indiqué correspond à une entité présente dans l'instantané du registre de la Banque de Maurice utilisé par FraudLens.",
        "not_found": "L'expéditeur indiqué n'a pas été trouvé dans l'instantané du registre de la Banque de Maurice utilisé par FraudLens (banques et autres participants financiers réglementés). Cela ne prouve pas que l'expéditeur n'existe nulle part, de nombreux expéditeurs légitimes tels que les services de messagerie, les commerçants ou les particuliers ne sont pas des institutions financières et ne seraient pas censés figurer dans ce registre. Mais si ce message prétend provenir d'une banque ou d'une institution financière, cette affirmation spécifique n'a pas pu être confirmée dans l'instantané du registre.",
        "no_sender_given": "Aucun nom d'expéditeur n'a été fourni, aucune vérification du registre n'a donc pu être effectuée.",
        "registry_unavailable": "L'instantané du registre des institutions financières n'a pas encore été chargé, cette vérification n'a donc pas pu être effectuée. Contactez un administrateur.",
    },
    "cr": {
        "verified": "Non ki ou finn done a matche avek enn antite dan enn kopi registre Labank Moris ki FraudLens servi.",
        "not_found": "Non ki ou finn done pa finn ganny trouve dan kopi registre Labank Moris ki FraudLens servi (labank ek lezot participant finansie regile). Sa pa prouve ki sa dimoune la pa existe ditou, boukou expediter legitim kouma servis livrezon, komersan, ouswa dimoune ordiner pa institision finansie ek pa bizin paret dan sa registre la. Me si sa mesaz la pretann sorti kot enn labank ouswa institision finansie, nou pa finn kapav konfirm sa dan kopi registre la.",
        "no_sender_given": "Pa finn done okenn non expediter, alor nou pa finn kapav fer okenn verifikasion dan registre.",
        "registry_unavailable": "Kopi registre bann institision finansie pankor chardze, alor sa verifikasion la pa finn kapav fini. Kontakte enn administrater.",
    },
}


def build_revoked_explanation(language: str, matched_entity: str, status_detail: str) -> str:
    templates = {
        "en": (
            f"The sender you named exactly matches \"{matched_entity}\" in the registry snapshot, "
            f"but this entity's license status is recorded as: {status_detail}. A message claiming "
            f"to be from an entity whose license is no longer active is a real reason for caution, "
            f"even though the name itself is genuine rather than fabricated."
        ),
        "fr": (
            f"L'expéditeur indiqué correspond exactement à « {matched_entity} » dans l'instantané du registre, "
            f"mais le statut de licence de cette entité est enregistré comme : {status_detail}. Un message "
            f"prétendant provenir d'une entité dont la licence n'est plus active est une véritable raison "
            f"de prudence, même si le nom lui-même est authentique plutôt que fabriqué."
        ),
        "cr": (
            f"Non ki ou finn done a matche exakteman avek \"{matched_entity}\" dan kopi registre la, "
            f"me lisans sa antite la finn note kouma: {status_detail}. Enn mesaz ki pretann sorti kot "
            f"enn antite ki so lisans nepli aktif se enn bon rezon pou fer atansion, mem si non la "
            f"limem li vre e pa invante."
        ),
    }
    return templates.get(language, templates["en"])


def build_name_mismatch_explanation(language: str, matched_entity: str) -> str:
    templates = {
        "en": (
            f"The sender you named closely resembles \"{matched_entity}\", an entity in the "
            f"Bank of Mauritius registry snapshot, but does not exactly match it. This is a "
            f"potential impersonation pattern: a name that looks almost right is a common "
            f"tactic used in real cases Mauritius has seen, such as Bank of Mauritius's 2026 "
            f"alert about a fake 'digital bank' using a near-identical name to a real one. A "
            f"close name match is evidence worth treating with caution, not proof of intent."
        ),
        "fr": (
            f"L'expéditeur indiqué ressemble fortement à « {matched_entity} », une entité présente dans "
            f"l'instantané du registre de la Banque de Maurice, mais ne correspond pas exactement. Il "
            f"s'agit d'un schéma potentiel d'usurpation d'identité : un nom qui semble presque correct "
            f"est une tactique courante observée dans des cas réels à Maurice, comme l'alerte de 2026 de "
            f"la Banque de Maurice concernant une fausse « banque numérique » utilisant un nom presque "
            f"identique à un nom réel. Une correspondance de nom proche est une preuve à traiter avec "
            f"prudence, pas une preuve d'intention."
        ),
        "cr": (
            f"Non ki ou finn done resanble bokou avek \"{matched_entity}\", enn antite dan kopi registre "
            f"Labank Moris, me li pa matche exakteman. Sa se enn model posib inpersonasion: enn non ki "
            f"paret preski bon se enn taktik komen dan bann ka reel Moris finn trouve, kouma lalert 2026 "
            f"Labank Moris lor enn fos 'labank dizital' ki servi enn non preski parey ar enn vre labank. "
            f"Enn non ki preski matche se enn levidans pou fer atansion, pa enn prev intansion."
        ),
    }
    return templates.get(language, templates["en"])


INDICATOR_DESCRIPTIONS = {
    "en": {
        "requests_otp": "asks you to send or enter a one-time password or verification code",
        "requests_card_details": "asks for card details such as a card number or CVV",
        "urgency": "uses urgent language (e.g. an account suspension deadline) to pressure a quick response",
        "payment_request": "asks you to send money or make a payment",
        "investment_promise": "promises guaranteed or unusually high investment returns",
        "contains_url": "contains a link",
    },
    "fr": {
        "requests_otp": "vous demande d'envoyer ou de saisir un mot de passe à usage unique ou un code de vérification",
        "requests_card_details": "demande des informations de carte telles qu'un numéro de carte ou un CVV",
        "urgency": "utilise un langage urgent (par exemple, une date limite de suspension de compte) pour vous pousser à réagir rapidement",
        "payment_request": "vous demande d'envoyer de l'argent ou d'effectuer un paiement",
        "investment_promise": "promet des rendements d'investissement garantis ou inhabituellement élevés",
        "contains_url": "contient un lien",
    },
    "cr": {
        "requests_otp": "demande ou pou anvoy ouswa rant enn mo-de-pas si-yous-servi enn fwa ouswa enn kod verifikasion",
        "requests_card_details": "demande detay kart kouma nimero kart ouswa CVV",
        "urgency": "servi lang irzan (par exanp, enn dat limit pou sispansion kont) pou fors ou reazir vit",
        "payment_request": "demande ou pou anvoy larzan ouswa fer enn peyman",
        "investment_promise": "promet retour investisman garanti ouswa extra-ordinerman elve",
        "contains_url": "kontenir enn lien",
    },
}


def build_indicator_summary(language: str, triggered_flags) -> str:
    """
    Turns the deterministic indicator flags into a short, plain-language
    sentence, mirrors the original English-only version previously
    inline in routers/checks.py, now dispatching per language.
    """
    descriptions_by_lang = INDICATOR_DESCRIPTIONS.get(language, INDICATOR_DESCRIPTIONS["en"])
    fallback = INDICATOR_DESCRIPTIONS["en"]

    descriptions = []
    for flag in triggered_flags:
        text = descriptions_by_lang.get(flag) or fallback.get(flag)
        if text:
            descriptions.append(text)

    if not descriptions:
        return ""

    joiners = {"en": "; and ", "fr": " ; et ", "cr": "; ek "}
    also_prefix = {
        "en": "This message also ",
        "fr": "Ce message ",
        "cr": "Sa mesaz la osi ",
    }
    joiner = joiners.get(language, joiners["en"])
    prefix = also_prefix.get(language, also_prefix["en"])

    if len(descriptions) == 1:
        joined = descriptions[0]
    else:
        joined = "; ".join(descriptions[:-1]) + joiner + descriptions[-1]

    return f"{prefix}{joined}."


def build_domain_summary(language: str, domain_mismatches):
    if not domain_mismatches:
        return ""

    templates = {
        "en": 'the link to "{domain}" is not a known domain for {entity}',
        "fr": "le lien vers « {domain} » n'est pas un domaine connu pour {entity}",
        "cr": 'lien ver "{domain}" pa enn domenn nou konnen pou {entity}',
    }
    prefixes = {
        "en": "Also worth noting: ",
        "fr": "À noter également : ",
        "cr": "Enportan osi pou remarke: ",
    }
    template = templates.get(language, templates["en"])
    prefix = prefixes.get(language, prefixes["en"])

    parts = [template.format(domain=d.domain, entity=d.matched_entity) for d in domain_mismatches]
    return f"{prefix}{'; '.join(parts)}."


def build_phone_summary(language: str, phone_mismatches):
    if not phone_mismatches:
        return ""

    templates = {
        "en": 'the phone number "{phone}" is not a known contact number for {entity}',
        "fr": "le numéro de téléphone « {phone} » n'est pas un numéro de contact connu pour {entity}",
        "cr": 'nimero telefonn "{phone}" pa enn nimero kontakt nou konnen pou {entity}',
    }
    prefixes = {
        "en": "Also worth noting: ",
        "fr": "À noter également : ",
        "cr": "Enportan osi pou remarke: ",
    }
    template = templates.get(language, templates["en"])
    prefix = prefixes.get(language, prefixes["en"])

    parts = [template.format(phone=p.phone, entity=p.matched_entity) for p in phone_mismatches]
    return f"{prefix}{'; '.join(parts)}."


def build_sender_detection_note(language: str, source_text: str, resolved_entity: str) -> str:
    templates = {
        "en": (
            f'Klaro noticed "{source_text}" in your message, which matches '
            f'{resolved_entity} in the registry snapshot, so the check below is against that entity.'
        ),
        "fr": (
            f"Klaro a remarqué « {source_text} » dans votre message, ce qui correspond à "
            f"{resolved_entity} dans l'instantané du registre, la vérification ci-dessous porte donc sur cette entité."
        ),
        "cr": (
            f'Klaro finn remarke "{source_text}" dan ou mesaz, ki matche avek '
            f'{resolved_entity} dan kopi registre la, alor verifikasion anba la se pou sa antite la.'
        ),
    }
    return templates.get(language, templates["en"])


REGISTRY_EVIDENCE_DESCRIPTIONS = {
    "en": {
        "verified": 'Sender "{entity}" matches the registry snapshot.',
        "not_found": "Claimed sender was not found in the registry snapshot.",
        "revoked": 'Sender matches "{entity}", but its license status is: {detail}.',
        "name_mismatch": 'Claimed sender closely resembles "{entity}" but does not exactly match it.',
        "no_sender_given": "No sender name was provided for a registry check.",
        "registry_unavailable": "The registry snapshot has not been loaded.",
        "default": "Registry check completed.",
    },
    "fr": {
        "verified": "L'expéditeur « {entity} » correspond à l'instantané du registre.",
        "not_found": "L'expéditeur indiqué n'a pas été trouvé dans l'instantané du registre.",
        "revoked": "L'expéditeur correspond à « {entity} », mais son statut de licence est : {detail}.",
        "name_mismatch": "L'expéditeur indiqué ressemble fortement à « {entity} » mais ne correspond pas exactement.",
        "no_sender_given": "Aucun nom d'expéditeur n'a été fourni pour une vérification du registre.",
        "registry_unavailable": "L'instantané du registre n'a pas été chargé.",
        "default": "Vérification du registre terminée.",
    },
    "cr": {
        "verified": 'Expediter "{entity}" matche avek kopi registre la.',
        "not_found": "Non ki ou finn done pa finn ganny trouve dan kopi registre la.",
        "revoked": 'Expediter matche avek "{entity}", me so lisans se: {detail}.',
        "name_mismatch": 'Non ki ou finn done resanble bokou avek "{entity}" me li pa matche exakteman.',
        "no_sender_given": "Pa finn done okenn non expediter pou enn verifikasion registre.",
        "registry_unavailable": "Kopi registre la pankor chardze.",
        "default": "Verifikasion registre finn fini.",
    },
}


def build_registry_evidence_description(language: str, status: str, entity=None, detail=None) -> str:
    descriptions = REGISTRY_EVIDENCE_DESCRIPTIONS.get(language, REGISTRY_EVIDENCE_DESCRIPTIONS["en"])
    fallback = REGISTRY_EVIDENCE_DESCRIPTIONS["en"]
    template = descriptions.get(status) or fallback.get(status) or descriptions["default"]
    return template.format(entity=entity, detail=detail)


DOMAIN_EVIDENCE_DESCRIPTIONS = {
    "en": {
        "mismatch": 'The link to "{domain}" is not a known domain for {entity}.',
        "structure": "A link in this message has a structurally unusual domain (e.g. an uncommon top-level domain or excessive subdomain nesting).",
    },
    "fr": {
        "mismatch": "Le lien vers « {domain} » n'est pas un domaine connu pour {entity}.",
        "structure": "Un lien dans ce message a un domaine structurellement inhabituel (par exemple, un domaine de premier niveau peu courant ou une imbrication excessive de sous-domaines).",
    },
    "cr": {
        "mismatch": 'Lien ver "{domain}" pa enn domenn nou konnen pou {entity}.',
        "structure": "Enn lien dan sa mesaz la ena enn domenn ki structireman biza (par exanp, enn top-level domain ki pa komen ouswa tro boukou subdomain).",
    },
}


def build_domain_evidence_description(language: str, kind: str, domain=None, entity=None) -> str:
    descriptions = DOMAIN_EVIDENCE_DESCRIPTIONS.get(language, DOMAIN_EVIDENCE_DESCRIPTIONS["en"])
    fallback = DOMAIN_EVIDENCE_DESCRIPTIONS["en"]
    template = descriptions.get(kind) or fallback.get(kind)
    return template.format(domain=domain, entity=entity)


PHONE_EVIDENCE_DESCRIPTIONS = {
    "en": 'The phone number "{phone}" is not a known contact number for {entity}.',
    "fr": "Le numéro de téléphone « {phone} » n'est pas un numéro de contact connu pour {entity}.",
    "cr": 'Nimero telefonn "{phone}" pa enn nimero kontakt nou konnen pou {entity}.',
}


def build_phone_evidence_description(language: str, phone: str, entity: str) -> str:
    template = PHONE_EVIDENCE_DESCRIPTIONS.get(language, PHONE_EVIDENCE_DESCRIPTIONS["en"])
    return template.format(phone=phone, entity=entity)


def build_indicator_evidence_description(language: str, flag: str) -> str:
    """
    Same underlying phrase-bank as build_indicator_summary(), but
    capitalized and used standalone (as one evidence item's
    description) rather than joined into a sentence with others.
    """
    descriptions_by_lang = INDICATOR_DESCRIPTIONS.get(language, INDICATOR_DESCRIPTIONS["en"])
    fallback = INDICATOR_DESCRIPTIONS["en"]
    text = descriptions_by_lang.get(flag) or fallback.get(flag) or ""
    return text[:1].upper() + text[1:] if text else ""
