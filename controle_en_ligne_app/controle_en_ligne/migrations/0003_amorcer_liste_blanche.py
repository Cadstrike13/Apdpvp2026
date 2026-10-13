"""Amorce la liste blanche avec les 18 chemins de la version codée en dur."""

from django.db import migrations

CHEMINS_INITIAUX = [
    ("/robots.txt", "Fichier public standard : révèle parfois des zones sensibles."),
    ("/sitemap.xml", "Fichier public standard : inventaire des pages déclarées."),
    ("/.well-known/security.txt", "Contact sécurité publié (RFC 9116)."),
    ("/.git/config", "Dépôt Git exposé : code source et historique accessibles."),
    ("/.env", "Fichier de configuration : secrets et accès base de données."),
    ("/.env.local", "Variante locale du fichier de configuration."),
    ("/wp-config.php.bak", "Sauvegarde de configuration WordPress lisible en clair."),
    ("/backup.zip", "Archive de sauvegarde laissée à la racine."),
    ("/backup.sql", "Export de base de données laissé à la racine."),
    ("/phpinfo.php", "Page de diagnostic : versions et configuration du serveur."),
    ("/.DS_Store", "Métadonnées macOS : liste le contenu du répertoire."),
    ("/config.json", "Configuration applicative exposée."),
    ("/swagger.json", "Description d'API exposée publiquement."),
    ("/swagger-ui.html", "Console d'API exposée publiquement."),
    ("/admin", "Interface d'administration accessible depuis Internet."),
    ("/administrator", "Interface d'administration (Joomla et autres)."),
    ("/server-status", "Statut Apache : requêtes et adresses des visiteurs."),
    ("/.htaccess", "Configuration Apache lisible."),
]


def amorcer(apps, schema_editor):
    Chemin = apps.get_model("controle_en_ligne", "CheminListeBlanche")
    for chemin, justification in CHEMINS_INITIAUX:
        Chemin.objects.get_or_create(chemin=chemin, defaults={"justification": justification})


def retirer(apps, schema_editor):
    Chemin = apps.get_model("controle_en_ligne", "CheminListeBlanche")
    Chemin.objects.filter(chemin__in=[c for c, _ in CHEMINS_INITIAUX]).delete()


class Migration(migrations.Migration):
    dependencies = [("controle_en_ligne", "0002_liste_blanche_editable")]
    operations = [migrations.RunPython(amorcer, retirer)]
