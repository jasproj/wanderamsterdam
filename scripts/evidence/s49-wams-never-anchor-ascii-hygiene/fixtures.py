#!/usr/bin/env python3
"""Fixture proof for the never-anchor ASCII-sibling hygiene fix (scripts/s49-wams-refresh-apply.py).

Hub context (ai-memory-hub wtpa/MEMORY.md, _network.md): "The never-anchor test must be
unicode-normalised everywhere (NFC, okina/macron folds) ... WENG and WAMS classifiers still
carry the ASCII form [incompletely]." This repo's own recon (s49-wams-refresh apply-stage
sweep, 2026-08-26) found the concrete gap: within WAMS's declared NL/ES/IT/DE never-anchor
vocabulary, some diacritic terms had no ASCII-normalized sibling in the pattern, unlike other
bilingual pairs already in the same regex (jóvenes|jovenes, privé|prive, één|een, bebé|bebe).
The sweep found zero live rows affected today, but the pattern asymmetry is a latent gap.

This fixture proves: (1) each newly added ASCII token now matches, word-bounded, same as its
accented sibling; (2) every pre-existing NEVER/AGE_RANGE fixture still matches unchanged.
Regex-only change; no data writes.
"""
import re, sys

NEVER = re.compile(r"\b(child|childs|child's|children|childrens|children's|kid|kids|kid's|infant|infants|baby|babies|toddler|junior|juniors|youth|youths|teen|teenager|teens|adolescent|adolescents|young adult|student|students|senior|seniors|oap|concession|concessions|pensioner|disabled|wheelchair|carer|companion|blue light|nhs|discount|under\s*\d+s?|\d+\s*(and|&)\s*under|family|families|bundle|package|add[- ]?on|extra(?!\s*(small|large|klein|groot|grote))|extras|additional|supplement|upgrade|gratuity|tip|tips|donation|deposit|voucher|gift card|redemption|per additional|spectator|non[- ]?participant|dog|dogs|pet|pets|kit|merchandise|parking|niño|niños|niña|niñas|nino|ninos|nina|ninas|bebé|bebe|infante|enfant|enfants|bébé|kind|kinder|bambino|bambini|neonato|neonati|ragazzo|ragazzi|ragazza|ragazze"
                   r"|kinderen|kindje|kids?tarief|peuter|peuters|baby's|jeugd|jongeren|studenten|senioren|65\+|korting|toeslag|bijboeking|extra's|optie|opties|fooi|borg|cadeaubon|hond|honden|huisdier|familie|gezin|gezinsticket|pakket|arrangement"
                   r"|joven|jóvenes|jovenes|criança|crianças|niñ[oa]s?|kinderfiets|kids? ?bike|child(?:ren'?s?)? bike|kinderzitje"
                   r"|aggiuntiv[oa]|adicional|adicionales|zusätzlich|zusätzliche|zusatzlich|zusatzliche|supplémentaire|extra persoon|bijboeken|optional|optioneel|upgrade|aanbetaling|voorschot|deposito|caparra|kaution|anzahlung"
                   r"|儿童|孩子|学生|老年|优惠)\b|^add (a|an|the)\b|儿童|孩子|学生|老年|优惠", re.I)
AGE_RANGE = re.compile(r"\b\d{1,2}\s*(-|–|to|t/m|tot)\s*\d{1,2}\s*(yrs|rys|years|year olds|yr olds|y/o|y/old|yo|años|anos|ans|anni|jaar|jr)\b", re.I)

# (label, pattern, should_match)
NEW_TOKEN_FIXTURES = [
    ("Nino",                 NEVER,     True),
    ("Ninos",                NEVER,     True),
    ("Nina",                 NEVER,     True),
    ("Ninas",                NEVER,     True),
    ("Zusatzlich",           NEVER,     True),
    ("Zusatzliche Person",   NEVER,     True),
    ("6-16 Anos",            AGE_RANGE, True),
    ("11-25 anos",           AGE_RANGE, True),
]

# pre-existing behavior that must NOT change (accented siblings + a representative sample
# of unrelated NEVER/AGE_RANGE/BASE terms already in the pattern)
REGRESSION_FIXTURES = [
    ("Niño",             NEVER,     True),
    ("Niños",            NEVER,     True),
    ("Niña",             NEVER,     True),
    ("Niñas",            NEVER,     True),
    ("Zusätzlich",       NEVER,     True),
    ("6-16 Años",        AGE_RANGE, True),
    ("Adult",            NEVER,     False),
    ("Adulto aggiuntivo",NEVER,     True),   # aggiuntivo already matched
    ("Bambino aggiuntivo",NEVER,    True),
    ("Volwassene",       NEVER,     False),
    ("Jóvenes",          NEVER,     True),
    ("Jovenes",          NEVER,     True),
    ("Privé",            NEVER,     False),  # not a never-anchor word; just confirms no accidental match
]

def run(fixtures, label):
    failures = []
    for text, pattern, expected in fixtures:
        got = bool(pattern.search(text))
        status = "OK" if got == expected else "FAIL"
        if got != expected:
            failures.append((text, expected, got))
        print(f"[{status}] {label}: {text!r} expected={expected} got={got}")
    return failures

fail1 = run(NEW_TOKEN_FIXTURES, "new-token")
fail2 = run(REGRESSION_FIXTURES, "regression")

total = len(NEW_TOKEN_FIXTURES) + len(REGRESSION_FIXTURES)
failed = len(fail1) + len(fail2)
print(f"\n{total - failed}/{total} fixtures passed")
sys.exit(1 if failed else 0)
