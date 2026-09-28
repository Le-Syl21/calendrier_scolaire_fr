# Calendrier scolaire FR

<img src=".github/flags/gb.svg" height="14" alt="GB"> [English](#english) | <img src=".github/flags/fr.svg" height="14" alt="FR"> [Français](#français)

A Home Assistant integration that knows whether there is school today: French school holidays from the Ministry of Education, public holidays, and the school's own week.
Une intégration Home Assistant qui sait s'il y a école aujourd'hui : vacances scolaires de l'Éducation nationale, jours fériés, et la semaine propre à l'école.

<a name="français"></a>
## <img src=".github/flags/fr.svg" height="14" alt="FR"> Français

### Ce que ça donne

Vous ajoutez une école (ou une par enfant) en choisissant son **académie**, son **niveau** et ses **jours de classe**. Pour une école nommée « École de Léon », l'intégration crée :

| Entité | Quoi | Exemple |
|---|---|---|
| `binary_sensor.ecole_de_leon_jour_de_classe` | Allumé les jours de classe. Sinon, l'attribut `motif` dit pourquoi : `vacances`, `ferie`, `jour_sans_classe` ou `jour_sans_cours` (mercredi, week-end), et `libelle` le précise | Éteint, « Vacances de la Toussaint » |
| `binary_sensor.ecole_de_leon_demain_jour_de_classe` | La même chose pour demain | Allumé |
| `binary_sensor.ecole_de_leon_en_classe` | Allumé pendant les heures de cours d'un jour de classe | Allumé de 8 h 30 à 16 h 30 |
| `binary_sensor.ecole_de_leon_vacances` | Allumé pendant les vacances et les ponts du calendrier national ; attributs `nom`, `premier_jour`, `dernier_jour`, `reprise` | Allumé |
| `sensor.ecole_de_leon_prochaines_vacances` | Premier jour des prochaines vacances ; attributs `nom`, `reprise`, `dans_jours` | 17/10/2026 |
| `calendar.ecole_de_leon_calendrier` | Vacances, jours fériés et jours sans classe de l'école | |

Chaque attribut `prochain_jour_de_classe` donne le prochain jour où il y a école.

Un jour de classe, c'est un jour coché dans la semaine de l'école, qui n'est :
- ni dans une période du calendrier de l'Éducation nationale (vacances, pont de l'Ascension, journées vaquées) ;
- ni un jour férié — y compris ceux d'Alsace-Moselle et des outre-mer ;
- ni un jour sans classe que vous avez ajouté (pont local, journée pédagogique).

Le **niveau** compte : certaines académies publient des dates différentes pour le premier et le second degré (la Polynésie par exemple), et les dates des enseignants ne sont jamais prises. En été, c'est la date de reprise des **élèves** qui s'applique.

Exemple : chambre à 17 °C pendant que les enfants sont à l'école.

```yaml
automation:
  - alias: Chambre de Léon pendant l'école
    triggers:
      - trigger: state
        entity_id: binary_sensor.ecole_de_leon_en_classe
    actions:
      - action: climate.set_preset_mode
        target:
          entity_id: climate.thermostat_leon
        data:
          preset_mode: "{{ 'eco' if trigger.to_state.state == 'on' else 'comfort' }}"
```

### Installation

1. HACS → *Dépôts personnalisés* → `https://github.com/Le-Syl21/calendrier_scolaire_fr`, catégorie *Intégration*.
2. Installez *Calendrier scolaire FR*, redémarrez Home Assistant.
3. *Paramètres* → *Appareils et services* → *Ajouter une intégration* → *Calendrier scolaire FR*.
4. Donnez un nom, choisissez l'académie et le niveau, puis les jours et horaires de classe. La semaine habituelle du niveau est proposée : sans le mercredi en maternelle et élémentaire, avec au collège et au lycée. Une école à quatre jours et demi coche le mercredi et indique l'heure de fin du mercredi.
5. *Configurer* permet ensuite de changer la semaine et d'ajouter les jours sans classe de l'école, une date ou une période par ligne : `2026-11-10` ou `07/05/2027 .. 10/05/2027`.

Pour plusieurs enfants dans des écoles différentes, ajoutez une école par enfant.

### D'où viennent les dates

- **Vacances et ponts** : le [calendrier scolaire](https://data.education.gouv.fr/explore/dataset/fr-en-calendrier-scolaire/) publié en open data par le ministère de l'Éducation nationale, relu une fois par jour. La dernière réponse est gardée : si le service ne répond pas, rien ne change.
- **Jours fériés** : calculés sur place avec la bibliothèque [`holidays`](https://github.com/vacanza/holidays), celle qu'utilise déjà Home Assistant, avec les jours propres à l'Alsace, à la Moselle (une case à cocher dans l'académie de Nancy-Metz), aux DOM, à la Polynésie et à Saint-Pierre-et-Miquelon.
- **Jours sans classe de l'école** : ceux que vous saisissez. Aucune source publique ne les donne.

### Limites

- Les années lointaines ne sont parfois publiées que par leur premier jour (« Début des Vacances d'Été ») : la reprise est alors supposée (1er septembre en métropole, environ six semaines pour l'hiver austral) et les attributs indiquent `provisoire: true`. Elle se corrige d'elle-même quand le ministère publie la date.
- En Guadeloupe, choisissez le territoire (Guadeloupe, Saint-Martin, Saint-Barthélemy) : leurs dates diffèrent parfois.
- Les horaires sont les mêmes tous les jours, sauf le mercredi.

### 💬 Communauté & support

Des questions, un bug à signaler ou juste envie d'en discuter ? Rejoignez le Discord, section *Home Assistant* :

[![Discord](https://img.shields.io/badge/Discord-Le--Syl21%20Tools-5865F2?logo=discord&logoColor=white)](https://discord.gg/T37DYHmt2j)

<a name="english"></a>
## <img src=".github/flags/gb.svg" height="14" alt="GB"> English

### What you get

You add a school (or one per child) by picking its **académie**, its **level** and its **school days**. For a school named "École de Léon", the integration creates:

| Entity | What | Example |
|---|---|---|
| `binary_sensor.ecole_de_leon_jour_de_classe` | On on school days. Otherwise the `motif` attribute says why: `vacances` (holidays), `ferie` (public holiday), `jour_sans_classe` (the school's own day off) or `jour_sans_cours` (Wednesday, weekend), and `libelle` names it | Off, "Vacances de la Toussaint" |
| `binary_sensor.ecole_de_leon_demain_jour_de_classe` | The same for tomorrow | On |
| `binary_sensor.ecole_de_leon_en_classe` | On during class hours of a school day | On from 8:30 to 16:30 |
| `binary_sensor.ecole_de_leon_vacances` | On during the national calendar's holidays and bridges; `nom`, `premier_jour`, `dernier_jour`, `reprise` attributes | On |
| `sensor.ecole_de_leon_prochaines_vacances` | First day of the next holidays; `nom`, `reprise`, `dans_jours` attributes | 2026-10-17 |
| `calendar.ecole_de_leon_calendrier` | Holidays, public holidays and the school's days off | |

Entity ids are French and the same in every language, so automations can be shared; the displayed names are translated.

A school day is a day ticked in the school's week that is not in a period of the Ministry's calendar (holidays, Ascension bridge, "journées vaquées"), not a public holiday (Alsace-Moselle and overseas ones included) and not one of the school's own days off.

The **level** matters: some académies publish different dates for primary and secondary schools (French Polynesia, for one), and teachers' dates are never used. In summer, the pupils' return date applies.

### Installation

1. HACS → *Custom repositories* → `https://github.com/Le-Syl21/calendrier_scolaire_fr`, category *Integration*.
2. Install *Calendrier scolaire FR*, restart Home Assistant.
3. *Settings* → *Devices & services* → *Add integration* → *Calendrier scolaire FR*.
4. Give a name, pick the académie and the level, then the school days and hours. The level's usual week is offered: no Wednesday in nursery and primary, Wednesday included in collège and lycée.
5. *Configure* then changes the week and adds the school's own days off, one date or range per line: `2026-11-10` or `07/05/2027 .. 10/05/2027`.

### Where the dates come from

- **Holidays and bridges**: the Ministry of Education's [school calendar](https://data.education.gouv.fr/explore/dataset/fr-en-calendrier-scolaire/) open data, read once a day. The last answer is kept: if the service is down, nothing changes.
- **Public holidays**: computed locally with the [`holidays`](https://github.com/vacanza/holidays) library Home Assistant already uses, including Alsace, Moselle (a checkbox in the Nancy-Metz académie), overseas départements, French Polynesia and Saint Pierre and Miquelon.
- **The school's own days off**: the ones you type in. No public source has them.

### Limits

- Far-off years are sometimes published with their first day only ("Début des Vacances d'Été"): the return date is then assumed (1 September in mainland France, about six weeks for the austral winter) and the attributes say `provisoire: true`. It corrects itself once the Ministry publishes the date.
- In Guadeloupe, pick the territory (Guadeloupe, Saint Martin, Saint Barthélemy): their dates sometimes differ.
- Class hours are the same every day except Wednesday.

### 💬 Community & support

Questions, bug reports, or just want to chat? Join the Discord, *Home Assistant* section:

[![Discord](https://img.shields.io/badge/Discord-Le--Syl21%20Tools-5865F2?logo=discord&logoColor=white)](https://discord.gg/T37DYHmt2j)

## Development / Développement

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

## License / Licence

MIT. See [LICENSE](LICENSE).
