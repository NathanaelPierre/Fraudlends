# Research: Mauritius Fintech Fraud

Compiled during the Finnovate Hackathon 2026, used to ground FraudLens AI's problem statement and design decisions in real, current, sourced facts rather than generic assumptions.

## The core framing

Mauritius has 89.8 percent financial inclusion, the highest in Africa, ahead of the high-income country average of 73.1 percent, and more than double the sub-Saharan average of 42.6 percent. This matters because it rules out a "banking the unbanked" pitch as uninformed. The real gap is not access, it is trust and verification: people are already banked and digital, but increasingly targeted by impersonation and social engineering.

## The scale of the problem

- Mauritius' Financial Crimes Commission reached over 94,500 individuals through awareness and sensitisation programmes in a single bulletin period, December 2025 to March 2026.
- In the same period: 824 complaints examined, 108 cases actively pursued before the courts, 26 arrests, and approximately Rs 160 million in assets restrained.
- Cyber-enabled fraud is explicitly named as the most prevalent financial crime type in Mauritius, with young professionals and retirees frequently targeted. Named scam types: fraudulent job offers, e-commerce fraud, romance scams, investment fraud.
- A specific, concrete case: one individual extorted Rs 1.2 million from 79 Mauritian victims through a fake cryptocurrency investment scheme run entirely over Facebook, posing as an investment expert.

## Real, current, named impersonation incidents (2026)

- Bank of Mauritius (January 2026): public warning about a fake, unlicensed "digital bank" (Tranz Digital Bank) impersonating a real institution using a near-identical name.
- MCB: warned of business email compromise fraud, hacked email accounts used to redirect real invoice payments to fraudulent accounts, described as steadily increasing.
- Absa Mauritius (September 2026): fraudulent Facebook pages and websites promoting a fake mobile banking app.

Common thread across all three: impersonation and social engineering, not purely technical exploits. This is the specific pattern FraudLens AI's registry-check feature is built to catch.

## The FSC Register of Licensees

The Financial Services Commission of Mauritius maintains a real, public, searchable Register of Licensees. Anyone can look up a company name and see whether a license exists, its issue date, license type, and regulatory notes. The FSC's own stated reason this matters: some entities falsely claim to be regulated by the FSC when they are not, and the FSC publishes memos calling out these frauds after the fact.

FraudLens's current registry snapshot uses Bank of Mauritius's own official "List of Participants" page (banks, leasing companies, insurance companies, microfinance companies, P2P operators, utility bodies) as its first data source; the separate FSC register (covering non-bank financial services such as forex brokers and investment funds) is a natural next addition.

## Sources

- IMF Financial Access Survey (via MFW4A), SME account/loan/deposit share statistics
- Mauritius National Fintech Strategy 2026-2030
- Bank of Mauritius, "List of Participants" (bom.mu, last updated 5 May 2026), the direct source for FraudLens's registry snapshot
- Bank of Mauritius Scam Alerts (bom.mu/financial-stability/supervision/scam-alerts)
- Mauritius Financial Crimes Commission enforcement bulletins, Dec 2025-Mar 2026
- OC Index (Global Organized Crime Index) country profile, Mauritius
- INTERPOL Global Financial Fraud Threat Assessment, March 2026
