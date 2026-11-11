"""Final check (UF), a read-only probe: does a furniture word written as the Check step writes it (the family name as the
flag shows it) classify that family? The kit (vendor/furniture_kit.py, unchanged) matches office words against the
family split at camel case. Run with the builder Python: node tools/run-builder-py.mjs <this file>"""
from walkthrough_builder.vendor.load import load
from walkthrough_builder.build.bank import family

fk = load('furniture_kit')
cases = ['TF2092P', 'TF0560P', 'A$C2619574F', 'A$C238E5230', 'A$C5BF14633', 'A$Ce0b21054', 'BASE', 'klkjlll',
         'Fritz-Hansen_SH200 - Default', 'HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range',
         'Gruppo-19', 'SmartTable - Default']
for fam in cases:
    as_written = fk.classify(fam, 'FUR', {'sofa': [fam]})        # the word = the family as the Check step shows it
    camel = fk._camel(fam)
    as_split = fk.classify(fam, 'FUR', {'sofa': [camel]})        # the word with the kit's own camel-case split
    print(f'{fam!r}: the kit reads it as {camel!r}; word as shown -> {as_written}; word as the kit splits it -> {as_split}')
