from datetime import date
from decimal import Decimal

from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee


class TauxCotisation(SoftDeleteModel):
    """Taux de cotisation sociale (CNSS, CNAMGS...). Valeurs configurables."""

    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)
    taux_salarial = models.DecimalField(max_digits=5, decimal_places=2, help_text="% part salariale")
    taux_patronal = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% part patronale")

    class Meta:
        verbose_name = "Taux de cotisation"
        verbose_name_plural = "Taux de cotisation"
        ordering = ["code"]

    def __str__(self):
        return f"{self.libelle} ({self.taux_salarial}%)"


class Salaire(SoftDeleteModel):
    """Historique du salaire de base d'un agent."""

    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="salaires")
    montant_base = models.DecimalField(max_digits=12, decimal_places=2)
    date_effet = models.DateField()
    motif = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Salaire"
        ordering = ["-date_effet"]

    def __str__(self):
        return f"{self.employe} — {self.montant_base} ({self.date_effet})"


class Prime(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="primes")
    libelle = models.CharField(max_length=150)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    imposable = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Prime"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.libelle} — {self.employe}"


class AvanceSalaire(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="avances")
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    motif = models.CharField(max_length=200, blank=True)
    rembourse = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Avance sur salaire"
        verbose_name_plural = "Avances sur salaire"
        ordering = ["-date"]

    def __str__(self):
        return f"Avance {self.montant} — {self.employe}"


class AllocationConge(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="allocations_conge")
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    libelle = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "Allocation de congé"
        verbose_name_plural = "Allocations de congé"
        ordering = ["-date"]

    def __str__(self):
        return f"Allocation congé {self.montant} — {self.employe}"


# ============ Calcul des droits ============
def calcul_droits(employe, jour=None):
    """
    Calcule les droits du mois pour un agent :
    brut = salaire de base courant + primes du mois ;
    cotisations salariales (somme des taux) ; avances non remboursées ; net.
    """
    jour = jour or date.today()
    salaire = employe.salaires.filter(date_effet__lte=jour).order_by("-date_effet").first()
    base = salaire.montant_base if salaire else Decimal("0")

    primes = employe.primes.filter(date__year=jour.year, date__month=jour.month)
    total_primes = sum((p.montant for p in primes), Decimal("0"))

    brut = base + total_primes

    taux = TauxCotisation.objects.all()
    cotisations = []
    total_cotis_sal = Decimal("0")
    for t in taux:
        part = (brut * t.taux_salarial / Decimal("100")).quantize(Decimal("0.01"))
        total_cotis_sal += part
        cotisations.append({"libelle": t.libelle, "taux": t.taux_salarial, "montant": part})

    avances = employe.avances.filter(rembourse=False)
    total_avances = sum((a.montant for a in avances), Decimal("0"))

    net = brut - total_cotis_sal - total_avances
    return {
        "base": base,
        "total_primes": total_primes,
        "brut": brut,
        "cotisations": cotisations,
        "total_cotisations": total_cotis_sal,
        "total_avances": total_avances,
        "net": net,
    }
