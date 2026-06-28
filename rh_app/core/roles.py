"""Rôles applicatifs APDPVP — mappés sur les groupes Django auth."""


class Roles:
    ADMIN = "admin"
    SUPERUSER = "superuser"
    DIRECTEUR = "directeur"
    CHEF_SERVICE = "chef_service"
    AGENT_RH = "agent_rh"
    USAGER = "usager"

    # (valeur, libellé affiché)
    CHOICES = [
        (ADMIN, "Admin"),
        (SUPERUSER, "Superuser"),
        (DIRECTEUR, "Directeur(trice)"),
        (CHEF_SERVICE, "Chef de service"),
        (AGENT_RH, "Agent RH"),
        (USAGER, "Usager"),
    ]

    ALL = [ADMIN, SUPERUSER, DIRECTEUR, CHEF_SERVICE, AGENT_RH, USAGER]

    LABELS = dict(CHOICES)

    # Apps RH concernées par les permissions
    RH_APPS = ["employees", "leaves", "recruitment", "training", "documents"]
