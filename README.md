# KoboStat — Plateforme d'analyse statistique connectée à KoboToolbox

Version "production" de la plateforme, construite selon l'architecture que tu as proposée :
**Kobo API → Django → PostgreSQL → Analyse (pandas/scipy/statsmodels) → Dashboard interactif
(Plotly) → Export Word/PDF**.

## 1. Ce qui est fait et testé de bout en bout

| Brique | Statut |
|---|---|
| Connexion API KoboToolbox (token, liste des formulaires, récupération des soumissions JSON) | ✅ `core/kobo_client.py` |
| Bouton "Synchroniser" (remplace l'export manuel) | ✅ + génère des données de démo si aucun token n'est renseigné |
| Import alternatif CSV / Excel / SPSS (.sav) | ✅ |
| Stockage en base (Project / Submission / VariableMeta) | ✅ SQLite en dev, **PostgreSQL en un réglage** (voir §4) |
| Nettoyage : détection + **exclusion automatique des doublons** (clé configurable), % de valeurs manquantes | ✅ |
| Recodage de variables (ex: 1→"Homme", 2→"Femme") appliqué automatiquement avant analyse | ✅ |
| Statistiques descriptives, tableaux croisés + Khi² + V de Cramér | ✅ |
| Comparaison de moyennes (test t / ANOVA) | ✅ |
| Corrélation (Pearson/Spearman) + régression linéaire | ✅ |
| Fiabilité (Alpha de Cronbach) | ✅ |
| **Dashboard interactif** (graphiques Plotly zoomables/exportables) + filtres par variable (ex: centre, période) | ✅ |
| Textes d'interprétation automatiques FR/EN | ✅ |
| Export **Word (.docx) et PDF** du rapport cumulatif | ✅ |
| Authentification & gestion des comptes (Django admin natif) | ✅ 12 comptes étudiants + 1 admin préconfigurés |

## 2. Lancer en local

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_users        # crée admin + 12 comptes étudiants
python manage.py runserver 0.0.0.0:8000
```

### Comptes de connexion (à personnaliser avant diffusion)
| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Admin | `admin` | `Admin2026!` |
| Étudiants | `etudiant01` … `etudiant12` | `Memoire2026!` |

Gérez/ajoutez des comptes facilement via `/admin/` (interface Django native) une fois connecté en admin.

## 3. Connecter un vrai formulaire KoboToolbox

1. Dans Kobo : **Compte → Paramètres du compte → API** → copiez votre token.
2. Ouvrez votre formulaire → l'UID apparaît dans l'URL (`.../#/forms/aXXXXXXXXXXXX/...`).
3. Dans KoboStat : "+ Nouveau projet" → renseignez l'URL de base (`https://kf.kobotoolbox.org` ou
   `https://eu.kobotoolbox.org` selon votre serveur), le token, et l'UID.
4. Cliquez sur **"Synchroniser maintenant"** à chaque fois que vous voulez récupérer les nouvelles réponses
   (un vrai déclenchement automatique — cron/Celery beat toutes les X heures — se branche facilement sur
   la même fonction `core.views.project_sync`, à activer en production).

Sans token renseigné, le bouton "Synchroniser" génère un jeu de données de démonstration pour tester
toute la plateforme immédiatement.

## 4. Basculer sur PostgreSQL (recommandé en production)

Le projet est déjà prêt : il suffit de définir la variable d'environnement `DATABASE_URL` avant de lancer
le serveur — aucune modification de code nécessaire :

```bash
export DATABASE_URL="postgres://USER:PASSWORD@HOST:5432/NOM_BASE"
python manage.py migrate
```

Options gratuites/pas chères pour héberger le Postgres : **Neon.tech**, **Supabase**, **Render Postgres**.

## 5. Déploiement (12 utilisateurs → puis public)

- **Maintenant (12 personnes)** : héberger sur **Render** ou **Railway** (~5-10$/mois avec Postgres inclus),
  ou un VPS simple (Contabo/Hostinger) avec `gunicorn` + `nginx`.
- **Avant la mise en ligne réelle**, pense à :
  - changer `DJANGO_SECRET_KEY` (variable d'env, ne jamais garder la valeur par défaut)
  - mettre `DJANGO_DEBUG=False`
  - restreindre `ALLOWED_HOSTS` à votre vrai nom de domaine (actuellement ouvert à `*` pour la démo)
  - changer tous les mots de passe des comptes de démonstration

## 6. Feuille de route monétisation

1. **Comptes payants** : Django gère déjà l'authentification — il suffit d'ajouter un modèle `Plan`/`Subscription`
   lié à `User`, et de brancher **Stripe** (international) ou **Kkiapay / FedaPay** (mobile money, mieux adapté
   au Bénin) pour les paiements.
2. **Limiter les fonctionnalités** selon le plan (ex: gratuit = 1 projet + export Word seulement ;
   payant = projets illimités + Kobo + PDF + dashboard filtrable).
3. **Isolation multi-tenant** : déjà en place au niveau du modèle (`Project.owner`), chaque utilisateur ne voit
   que ses propres projets.
4. **Scheduled sync automatique** : ajouter Celery + Celery Beat (ou simplement `django-crontab`) pour
   synchroniser Kobo toutes les nuits sans action manuelle — utile pour les comptes payants "premium".
5. **Frontend plus riche** : à terme, remplacer les templates Django par une SPA React/Next.js consommant
   une API DRF (le code d'analyse dans `core/stats_engine.py`, `interpretation.py`, etc. resterait identique,
   seule la couche de présentation changerait).

## 7. Structure du projet

```
statmemoire_django/
├── manage.py
├── requirements.txt
├── statmemoire_django/settings.py, urls.py   # config Django (DB, hosts, etc.)
└── core/
    ├── models.py            # Project, Submission (JSON), VariableMeta, SavedReport
    ├── kobo_client.py       # client API KoboToolbox (+ générateur de données démo)
    ├── data_pipeline.py     # construction DataFrame, recodage, dédoublonnage, upload fichiers
    ├── stats_engine.py      # calculs statistiques (SPSS/R-like)
    ├── plotting_interactive.py  # graphiques Plotly pour le dashboard web
    ├── plotting_static.py       # graphiques matplotlib pour les exports Word/PDF
    ├── interpretation.py    # textes d'interprétation FR/EN
    ├── word_export.py / pdf_export.py
    ├── views.py, urls.py, forms.py, admin.py
    ├── management/commands/seed_users.py
    └── templates/core/*.html
```

## 8. Ce qui reste "prototype" (à muscler avant un vrai lancement public)

- Pas encore de synchronisation **automatique planifiée** (seulement le bouton manuel) — facile à ajouter (Celery/cron).
- Pas encore de tests non-paramétriques (Mann-Whitney, Kruskal-Wallis), d'ACP, ni d'analyse de questions
  à choix multiples Kobo (colonnes `question/option`) — extensions naturelles du même moteur.
- Le rapport est structuré mais reste "brut" (mise en page simple) — on peut ajouter des templates
  par filière (économie, santé, sociologie...) plus tard.
