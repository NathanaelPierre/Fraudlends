"""
Seed data for the registry snapshot, compiled from Bank of Mauritius's
own official "List of Participants" page (bom.mu, last updated 5 May
2026, fetched directly during development). This is first-party,
authoritative data, not a secondary or aggregator source.

This deliberately covers BANKS plus the other categories BoM itself
groups on the same official page (leasing companies, insurance
companies, microfinance companies, P2P operators, utility bodies).
Scammers impersonate more than just banks, for example fake insurance
payouts or fake utility refund messages, so limiting this to banks
alone would under-cover the real threat surface described in the
research.

This is a snapshot, not a live feed, see registry_sync.py for the
loader that reads this into the database. In a real, non-hackathon
deployment, this would be refreshed periodically against the live BoM
and FSC pages rather than hand-maintained. For a three-day build, a
periodically-refreshed snapshot is the realistic, demoable approach,
and it is also a legitimate sustainability story on its own, since the
data needs upkeep over time, same as the real BoM and FSC pages do.

Not included yet: the FSC Register of Licensees (non-bank financial
services such as insurance intermediaries, investment funds, and forex
brokers). That register is large and would need its own targeted
fetch. This file focuses on BoM's participant list first since it is
smaller, covers the most commonly-impersonated entities (banks), and
was directly confirmed accessible during research.
"""

# Known official domains for a subset of registry entities, used by
# app/domain_analyzer.py to check whether a URL in a message actually
# belongs to the institution it claims to represent. This is
# deliberately a small, hand-curated, sourced table — the same
# tradeoff as the registry snapshot itself: not exhaustive, but real
# and instantly checkable with no network call, versus a live lookup
# that would be slow, unreliable (most companies don't publish "these
# are our domains" pages), and would reintroduce exactly the external
# dependency the local-only architecture is built to avoid. Each
# domain here was found via that institution's own public
# website/documentation, not guessed.
KNOWN_OFFICIAL_DOMAINS = {
    "The Mauritius Commercial Bank Ltd": ["mcb.mu"],
    "Absa Bank (Mauritius) Limited": ["absa.mu"],
    "AfrAsia Bank Limited": ["afrasiabank.com"],
    "SBM Bank (Mauritius) Ltd": ["sbmgroup.mu"],
    "The Hongkong and Shanghai Banking Corporation Limited": ["hsbc.co.mu", "hsbc.com"],
    "Standard Chartered Bank (Mauritius) Ltd": ["sc.com"],
    "Bank One Limited": ["bankone.mu"],
    "MauBank Ltd": ["maubank.mu"],
    "Mauritius Telecom Ltd": ["telecom.mu", "myt.mu"],
    "Emtel Ltd": ["emtel.com"],
    "Bank of Mauritius": ["bom.mu"],
}

# Known official phone numbers for a subset of registry entities, used
# by app/phone_analyzer.py — the phone-number equivalent of
# KNOWN_OFFICIAL_DOMAINS above. Same tradeoff: a small, hand-curated,
# sourced table rather than an exhaustive or live-looked-up one. Each
# number here was found on that institution's own official contact
# page, not guessed or scraped from a directory. Numbers are stored
# normalized (digits only, no spaces/punctuation, no leading +) for
# reliable comparison — see phone_analyzer.py's normalize_phone().
KNOWN_OFFICIAL_PHONE_NUMBERS = {
    "The Mauritius Commercial Bank Ltd": ["2302025000"],
    "Absa Bank (Mauritius) Limited": ["2304021000", "23059190001"],
    "AfrAsia Bank Limited": ["2304035500", "2302085500"],
}

BOM_BANKS = [
    "Bank of Mauritius",
    "ABC Banking Corporation Ltd",
    "Absa Bank (Mauritius) Limited",
    "AfrAsia Bank Limited",
    "Bank of Baroda",
    "Bank One Limited",
    "Banque Patronus Limitée",
    "BCP Bank (Mauritius) Ltd",
    "HSBC Bank (Mauritius) Limited",
    "Investec Bank (Mauritius) Ltd",
    "MauBank Ltd",
    "SBI (Mauritius) Limited",
    "Standard Bank (Mauritius) Limited",
    "Standard Chartered Bank (Mauritius) Ltd",
    "SBM Bank (Mauritius) Ltd",
    "The Hongkong and Shanghai Banking Corporation Limited",
    "The Mauritius Commercial Bank Ltd",
]

BOM_LEASING_COMPANIES = [
    "Cim Financial Services Ltd",
    "Dölberg Asset Finance Limited",
    "Expert Leasing Ltd",
    "La Prudence Leasing Finance Co. Ltd",
    "MCB Leasing Limited",
    "SICOM Financial Services Ltd",
    "SPICE Finance Ltd",
]

BOM_INSURANCE_COMPANIES = [
    "Afri Life Insurance Ltd",
    "Indian Ocean General Assurance Co Ltd",
    "Island Life Assurance Co Ltd",
    "LAMCO International Insurance Ltd",
    "Mauritius Union Assurance Co Ltd",
    "MUA Life Ltd",
    "National Insurance Co Ltd",
    "State Insurance Company of Mauritius Ltd",
    "Swan Life Ltd",
]

BOM_MICROFINANCE_COMPANIES = [
    "MCB Microfinance Ltd",
    "NIC Micro Finance Co Ltd",
]

BOM_P2P_OPERATORS = [
    "Finance Club Ltd",
    "Fundkiss Technologies Limited",
]

BOM_OTHER_PARTICIPANTS = [
    "Development Bank of Mauritius Ltd",
    "Employees Welfare Fund",
    "Industrial Finance Corporation of Mauritius Ltd",
    "J Kalachand & Co Ltd",
    "Kalachand Finance Ltd",
    "Mauritius Housing Company Ltd",
    "MTL Credit Finance Ltd",
    "NanoSAIO Ltd",
    "National Housing Development Co Ltd",
    "Rogers Capital Finance Ltd",
    "Rogers Capital Credit Ltd",
    "The Mauritius Civil Service Mutual Aid Association Ltd",
]

BOM_UTILITY_BODIES = [
    "Central Electricity Board",
    "Central Water Authority",
    "Emtel Ltd",
    "Mauritius Telecom Ltd",
    "Wastewater Management Authority",
]

# FSC (Financial Services Commission of Mauritius) — non-bank financial
# services: investment dealers, forex/CFD brokers, and similar entities
# regulated under the Securities Act 2005, separate from BoM's banking
# remit above. This is the category directly implicated in the
# investment-scam pattern from research.md (the Rs 1.2M/79-victim fake
# crypto investment scheme run via Facebook) — a scam impersonating a
# "forex broker" or "investment platform" name would never appear in
# BoM's bank list at all, since it was never claiming to be a bank.
#
# This is a hand-curated snapshot of well-known, currently-licensed
# entities confirmed via public sources during research (not a scrape
# of the FSC's full register, which runs to hundreds of entries across
# many license categories) — see README's "Known limitations" section
# for the honest scope of this. Chosen for recognizability: these are
# the names most likely to appear, genuinely or impersonated, in a
# message a real user might receive.
FSC_INVESTMENT_DEALERS_AND_FOREX_BROKERS = [
    "Exinity Limited",  # FXTM's Mauritius-licensed entity
    "XS.com",
    "Fortrade",
    "SimpleFX",
    "BelleoFX",
    "Orbex",
    "ZuluTrade",
    "Adamas Capital",
    "YWO",
]

# Entities named in real, dated FSC public notices as having had their
# license surrendered or revoked — included so a message claiming to
# be from one of these can be flagged with the SPECIFIC, sourced fact
# that the license is no longer active, rather than a generic
# not_found result. Loaded with license_type/status distinct from the
# active entities above; see registry_sync.py and entity_matcher.py
# for how a revoked-but-matched entity should be surfaced differently
# from a genuinely unknown one — the matcher and verdict engine treat
# any registry hit the same today, since they don't yet branch on
# `status`. Reading this list's status field is intentionally left
# reserved for that surfacing improvement rather than acted on now.
FSC_REVOKED_OR_SURRENDERED_ENTITIES = [
    ("Trade T Capital Markets", "Surrendered — Global Business & Investment Dealer licence, 30 June 2026"),
    ("Paka Group", "Revoked, late 2025"),
    ("Yuragi", "Revoked, late 2025"),
    ("Yukai", "Revoked, late 2025"),
]

# Common public abbreviations/shorthand that real users type but which
# don't literally appear as substrings of the registry's formal legal
# names, so fuzzy matching alone doesn't reliably catch them. Found
# during testing: "MCB" alone scored only 42.9% against "The Mauritius
# Commercial Bank Ltd" even though it's the bank's universally-used
# public name in Mauritius. This maps the alias directly to the
# registry's exact stored name, added as an extra searchable entry
# rather than replacing the formal name (both need to remain matchable).
KNOWN_ALIASES = {
    "MCB": "The Mauritius Commercial Bank Ltd",
    "HSBC": "The Hongkong and Shanghai Banking Corporation Limited",
    "SBM": "SBM Bank (Mauritius) Ltd",
    "SBI": "SBI (Mauritius) Limited",
    "Standard Chartered": "Standard Chartered Bank (Mauritius) Ltd",
    "Absa": "Absa Bank (Mauritius) Limited",
    "AfrAsia": "AfrAsia Bank Limited",
    "Emtel": "Emtel Ltd",
    "myt": "Mauritius Telecom Ltd",
    "Mauritius Telecom": "Mauritius Telecom Ltd",
    # FXTM is the globally-recognized consumer brand; Exinity Limited
    # is the formal name under which the brand's Mauritius entity is
    # actually FSC-licensed — found the same way the bank aliases
    # above were: the brand name a real user would type does not
    # reliably fuzzy-match the formal registered name.
    "FXTM": "Exinity Limited",
}


def get_all_registry_entities():
    """
    Returns a flat list of (name, category, source) tuples across
    every BoM and FSC category loaded into this snapshot. Category and
    source are stored as extra context, not used in matching logic —
    the matcher treats every entity the same regardless of category or
    source, since a scammer could impersonate any of them equally.
    """
    bom_categorized = [
        (BOM_BANKS, "Bank"),
        (BOM_LEASING_COMPANIES, "Leasing Company"),
        (BOM_INSURANCE_COMPANIES, "Insurance Company"),
        (BOM_MICROFINANCE_COMPANIES, "Microfinance Company"),
        (BOM_P2P_OPERATORS, "P2P Operator"),
        (BOM_OTHER_PARTICIPANTS, "Other Financial Participant"),
        (BOM_UTILITY_BODIES, "Utility Body"),
    ]
    result = []
    for names, category in bom_categorized:
        for name in names:
            result.append((name, category, "BOM"))

    for name in FSC_INVESTMENT_DEALERS_AND_FOREX_BROKERS:
        result.append((name, "Investment Dealer / Forex Broker", "FSC"))

    return result


# Backward-compatible alias — registry_sync.py and any external caller
# written against the original BoM-only name continue to work
# unchanged; it now simply also includes FSC entities.
get_all_bom_entities = get_all_registry_entities
