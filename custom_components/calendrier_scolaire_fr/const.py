"""Constants for Calendrier scolaire FR."""

from __future__ import annotations

from datetime import time, timedelta
from typing import Final

DOMAIN: Final = "calendrier_scolaire_fr"

API_URL: Final = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "fr-en-calendrier-scolaire/records"
)
USER_AGENT: Final = "calendrier_scolaire_fr (+https://github.com/Le-Syl21/calendrier_scolaire_fr)"
UPDATE_INTERVAL: Final = timedelta(hours=24)
STORAGE_VERSION: Final = 1

CONF_ACADEMIE: Final = "academie"
CONF_NIVEAU: Final = "niveau"
CONF_JOURS: Final = "jours"
CONF_DEBUT: Final = "debut"
CONF_FIN: Final = "fin"
CONF_FIN_MERCREDI: Final = "fin_mercredi"
CONF_MOSELLE: Final = "moselle"
CONF_TERRITOIRE: Final = "territoire"
CONF_JOURS_SANS_CLASSE: Final = "jours_sans_classe"

NIVEAU_PRIMAIRE: Final = "primaire"
NIVEAU_COLLEGE: Final = "college"
NIVEAU_LYCEE: Final = "lycee"
NIVEAUX: Final = (NIVEAU_PRIMAIRE, NIVEAU_COLLEGE, NIVEAU_LYCEE)

# Weekday keys in Python order (Monday = 0).
JOURS: Final = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")
JOURS_PAR_DEFAUT: Final = {
    # The four-day week most primary schools run; a school on four and a half
    # days adds Wednesday morning in the options.
    NIVEAU_PRIMAIRE: ["lun", "mar", "jeu", "ven"],
    NIVEAU_COLLEGE: ["lun", "mar", "mer", "jeu", "ven"],
    NIVEAU_LYCEE: ["lun", "mar", "mer", "jeu", "ven"],
}
DEBUT_PAR_DEFAUT: Final = time(8, 30)
FIN_PAR_DEFAUT: Final = time(16, 30)
FIN_MERCREDI_PAR_DEFAUT: Final = time(12, 0)

TERRITOIRES: Final = ("guadeloupe", "saint_martin", "saint_barthelemy")

# Académie (the dataset's `location`) -> zone, as the dataset spells both.
ACADEMIES: Final = {
    "Besançon": "Zone A",
    "Bordeaux": "Zone A",
    "Clermont-Ferrand": "Zone A",
    "Dijon": "Zone A",
    "Grenoble": "Zone A",
    "Limoges": "Zone A",
    "Lyon": "Zone A",
    "Poitiers": "Zone A",
    "Aix-Marseille": "Zone B",
    "Amiens": "Zone B",
    "Lille": "Zone B",
    "Nancy-Metz": "Zone B",
    "Nantes": "Zone B",
    "Nice": "Zone B",
    "Normandie": "Zone B",
    "Orléans-Tours": "Zone B",
    "Reims": "Zone B",
    "Rennes": "Zone B",
    "Strasbourg": "Zone B",
    "Créteil": "Zone C",
    "Montpellier": "Zone C",
    "Paris": "Zone C",
    "Toulouse": "Zone C",
    "Versailles": "Zone C",
    "Corse": "Corse",
    "Guadeloupe": "Guadeloupe",
    "Guyane": "Guyane",
    "Martinique": "Martinique",
    "Mayotte": "Mayotte",
    "Polynésie": "Polynésie",
    "Réunion": "Réunion",
    "Saint Pierre et Miquelon": "Saint Pierre et Miquelon",
}

# Public holidays: `holidays.France` subdivision for the académies that have
# their own. Strasbourg covers the two Alsace départements; Moselle, the third
# département with the extra days, sits in Nancy-Metz and is an option there.
SUBDIVISIONS: Final = {
    "Strasbourg": "6AE",
    "Guadeloupe": "971",
    "Martinique": "972",
    "Guyane": "973",
    "Réunion": "974",
    "Mayotte": "976",
    "Polynésie": "PF",
    "Saint Pierre et Miquelon": "PM",
}
SUBDIVISION_MOSELLE: Final = "57"
SUBDIVISIONS_TERRITOIRE: Final = {"saint_martin": "MF", "saint_barthelemy": "BL"}

# Fixed entity ids (object id suffix after the entry's slug): the same in
# every language, so automations can be shared.
OBJECT_IDS: Final = {
    "school_day": "jour_de_classe",
    "school_day_tomorrow": "demain_jour_de_classe",
    "in_class": "en_classe",
    "holidays": "vacances",
    "next_holidays": "prochaines_vacances",
    "calendar": "calendrier",
}
