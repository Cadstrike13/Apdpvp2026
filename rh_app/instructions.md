# Recréer APDPVP-RH avec Django + HTMX

Ce document explique comment recréer l'application RH (actuellement en React/Vite) avec Django et HTMX.

---

## Stack technologique

| Couche | Technologie |
|--------|-------------|
| Backend | Django 5.x |
| Templates | Django Templates + HTMX |
| Style | Tailwind CSS (via CDN ou npm) |
| Icônes | Lucide (via CDN) |
| Base de données | PostgreSQL (ou SQLite en dev) |
| Auth | Django auth intégré |

---

## 1. Initialisation du projet

```bash
# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Installer les dépendances
pip install django django-htmx django-crispy-forms crispy-tailwind pillow psycopg2-binary

# Créer le projet
django-admin startproject config .
```

### Créer les applications

```bash
python manage.py startapp dashboard
python manage.py startapp employees
python manage.py startapp recruitment
python manage.py startapp leaves
python manage.py startapp training
python manage.py startapp documents
```

---

## 2. Configuration (`config/settings.py`)

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "django_htmx",
    "crispy_forms",
    "crispy_tailwind",
    # Applications
    "dashboard",
    "employees",
    "recruitment",
    "leaves",
    "training",
    "documents",
]

MIDDLEWARE = [
    ...
    "django_htmx.middleware.HtmxMiddleware",  # ajouter après les middlewares Django
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Statiques
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

---

## 3. Structure des URLs (`config/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("employes/", include("employees.urls")),
    path("recrutement/", include("recruitment.urls")),
    path("conges/", include("leaves.urls")),
    path("formations/", include("training.urls")),
    path("documents/", include("documents.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 4. Modèles de données

### `employees/models.py`

```python
from django.db import models

class Department(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom

class Employee(models.Model):
    STATUS_CHOICES = [("actif", "Actif"), ("inactif", "Inactif")]

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    poste = models.CharField(max_length=100)
    date_embauche = models.DateField()
    salaire = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default="actif")
    photo = models.ImageField(upload_to="photos/", blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"
```

### `leaves/models.py`

```python
from django.db import models
from employees.models import Employee

class LeaveRequest(models.Model):
    TYPE_CHOICES = [
        ("conge", "Congé annuel"),
        ("maladie", "Maladie"),
        ("maternite", "Maternité"),
        ("paternite", "Paternité"),
        ("autre", "Autre"),
    ]
    STATUS_CHOICES = [
        ("en_attente", "En attente"),
        ("approuve", "Approuvé"),
        ("refuse", "Refusé"),
    ]

    employe = models.ForeignKey(Employee, on_delete=models.CASCADE)
    type_conge = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    date_demande = models.DateTimeField(auto_now_add=True)

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1
```

### `recruitment/models.py`

```python
from django.db import models
from employees.models import Department

class JobPosting(models.Model):
    STATUS_CHOICES = [("ouvert", "Ouvert"), ("ferme", "Fermé"), ("pourvu", "Pourvu")]

    titre = models.CharField(max_length=200)
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    lieu = models.CharField(max_length=100)
    date_publication = models.DateField(auto_now_add=True)
    date_limite = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ouvert")
    description = models.TextField()

class Candidate(models.Model):
    STATUS_CHOICES = [
        ("examen", "En examen"),
        ("entretien", "Entretien"),
        ("offre", "Offre"),
        ("refuse", "Refusé"),
    ]

    offre = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    nom = models.CharField(max_length=200)
    email = models.EmailField()
    date_candidature = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="examen")
    note = models.PositiveSmallIntegerField(default=0)  # /5
    cv = models.FileField(upload_to="cvs/", blank=True)
```

### `training/models.py`

```python
from django.db import models
from employees.models import Employee

class TrainingProgram(models.Model):
    TYPE_CHOICES = [
        ("technique", "Technique"),
        ("soft_skills", "Soft-skills"),
        ("management", "Management"),
    ]
    STATUS_CHOICES = [
        ("planifie", "Planifié"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
    ]

    titre = models.CharField(max_length=200)
    prestataire = models.CharField(max_length=200)
    type_formation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    duree_heures = models.PositiveIntegerField()
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planifie")
    participants = models.ManyToManyField(Employee, blank=True)

    @property
    def nb_participants(self):
        return self.participants.count()
```

### `documents/models.py`

```python
from django.db import models
from employees.models import Employee

class Document(models.Model):
    CATEGORY_CHOICES = [
        ("contrat", "Contrat"),
        ("politique", "Politique"),
        ("formation", "Formation"),
        ("evaluation", "Évaluation"),
        ("autre", "Autre"),
    ]

    nom = models.CharField(max_length=200)
    categorie = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    fichier = models.FileField(upload_to="documents/")
    uploade_par = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    date_upload = models.DateTimeField(auto_now_add=True)
    acces_employes = models.ManyToManyField(Employee, blank=True, related_name="documents_accessibles")

    @property
    def taille(self):
        try:
            return f"{self.fichier.size / 1024:.0f} KB"
        except Exception:
            return "N/A"
```

---

## 5. Template de base (`templates/base.html`)

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}APDPVP RH{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-gray-50 text-gray-800">

<div class="flex h-screen overflow-hidden">

  <!-- Sidebar -->
  {% include "partials/sidebar.html" %}

  <!-- Contenu principal -->
  <div class="flex-1 flex flex-col overflow-hidden">
    {% include "partials/header.html" %}

    <main class="flex-1 overflow-y-auto p-6" id="main-content">
      {% block content %}{% endblock %}
    </main>
  </div>

</div>

<script>lucide.createIcons();</script>
{% block extra_js %}{% endblock %}
</body>
</html>
```

---

## 6. Navigation HTMX (`templates/partials/sidebar.html`)

Le principe clé : les liens utilisent `hx-get` pour charger le contenu sans rechargement de page.

```html
<aside class="w-64 bg-white shadow-md flex flex-col">
  <div class="p-6 border-b">
    <h1 class="text-xl font-bold text-emerald-600">APDPVP RH</h1>
  </div>

  <nav class="flex-1 p-4 space-y-1">
    {% with nav_items=sidebar_nav %}
    {% for item in nav_items %}
    <a href="{{ item.url }}"
       hx-get="{{ item.url }}"
       hx-target="#main-content"
       hx-push-url="true"
       class="flex items-center gap-3 px-4 py-2 rounded-lg
              {% if request.path == item.url %}bg-emerald-50 text-emerald-600 font-semibold{% else %}text-gray-600 hover:bg-gray-100{% endif %}">
      <i data-lucide="{{ item.icon }}" class="w-5 h-5"></i>
      {{ item.label }}
    </a>
    {% endfor %}
    {% endwith %}
  </nav>
</aside>
```

---

## 7. Vues avec HTMX (`employees/views.py`)

```python
from django.shortcuts import render, get_object_or_404
from django_htmx.http import retarget
from .models import Employee

def employee_list(request):
    q = request.GET.get("q", "")
    employees = Employee.objects.select_related("departement").all()
    if q:
        employees = employees.filter(
            nom__icontains=q
        ) | employees.filter(
            email__icontains=q
        )

    # Réponse partielle si requête HTMX
    template = "employees/partials/table.html" if request.htmx else "employees/list.html"
    return render(request, template, {"employees": employees, "query": q})


def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        emp.delete()
        # Retourner une ligne vide pour retirer la ligne du tableau
        return HttpResponse("")
    return render(request, "employees/partials/confirm_delete.html", {"employee": emp})
```

---

## 8. Template liste employés (`templates/employees/list.html`)

```html
{% extends "base.html" %}
{% block content %}

<div class="flex justify-between items-center mb-6">
  <h2 class="text-2xl font-bold">Employés</h2>
  <a href="{% url 'employees:create' %}" class="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700">
    + Nouvel employé
  </a>
</div>

<!-- Recherche en temps réel avec HTMX -->
<input type="search"
       name="q"
       placeholder="Rechercher un employé..."
       value="{{ query }}"
       hx-get="{% url 'employees:list' %}"
       hx-trigger="input changed delay:300ms"
       hx-target="#employee-table"
       hx-swap="innerHTML"
       class="w-full mb-4 px-4 py-2 border rounded-lg">

<div id="employee-table">
  {% include "employees/partials/table.html" %}
</div>

{% endblock %}
```

### Partiel table (`templates/employees/partials/table.html`)

```html
<table class="w-full text-sm">
  <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
    <tr>
      <th class="px-4 py-3 text-left">Nom</th>
      <th class="px-4 py-3 text-left">Email</th>
      <th class="px-4 py-3 text-left">Département</th>
      <th class="px-4 py-3 text-left">Statut</th>
      <th class="px-4 py-3 text-left">Actions</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-gray-100">
    {% for emp in employees %}
    <tr id="employee-{{ emp.pk }}" class="hover:bg-gray-50">
      <td class="px-4 py-3 font-medium">{{ emp.prenom }} {{ emp.nom }}</td>
      <td class="px-4 py-3 text-gray-500">{{ emp.email }}</td>
      <td class="px-4 py-3">{{ emp.departement }}</td>
      <td class="px-4 py-3">
        <span class="px-2 py-1 rounded-full text-xs
          {% if emp.statut == 'actif' %}bg-green-100 text-green-700{% else %}bg-red-100 text-red-700{% endif %}">
          {{ emp.get_statut_display }}
        </span>
      </td>
      <td class="px-4 py-3 flex gap-2">
        <a href="{% url 'employees:detail' emp.pk %}"
           hx-get="{% url 'employees:detail' emp.pk %}"
           hx-target="#main-content"
           class="text-blue-500 hover:underline">Voir</a>

        <button hx-delete="{% url 'employees:delete' emp.pk %}"
                hx-target="#employee-{{ emp.pk }}"
                hx-swap="outerHTML"
                hx-confirm="Supprimer cet employé ?"
                class="text-red-500 hover:underline">Supprimer</button>
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="5" class="text-center py-8 text-gray-400">Aucun employé trouvé.</td></tr>
    {% endfor %}
  </tbody>
</table>
```

---

## 9. Approbation de congé avec HTMX (`leaves/views.py`)

```python
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import LeaveRequest

def approve_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        leave.statut = "approuve"
        leave.save()
        # Retourner uniquement le badge mis à jour
        return render(request, "leaves/partials/status_badge.html", {"leave": leave})

def reject_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        leave.statut = "refuse"
        leave.save()
        return render(request, "leaves/partials/status_badge.html", {"leave": leave})
```

### Partiel badge statut (`templates/leaves/partials/status_badge.html`)

```html
<div id="leave-status-{{ leave.pk }}" class="flex items-center gap-2">
  <span class="px-2 py-1 rounded-full text-xs
    {% if leave.statut == 'approuve' %}bg-green-100 text-green-700
    {% elif leave.statut == 'refuse' %}bg-red-100 text-red-700
    {% else %}bg-yellow-100 text-yellow-700{% endif %}">
    {{ leave.get_statut_display }}
  </span>

  {% if leave.statut == 'en_attente' %}
  <button hx-post="{% url 'leaves:approve' leave.pk %}"
          hx-target="#leave-status-{{ leave.pk }}"
          hx-swap="outerHTML"
          class="text-green-600 text-xs hover:underline">Approuver</button>
  <button hx-post="{% url 'leaves:reject' leave.pk %}"
          hx-target="#leave-status-{{ leave.pk }}"
          hx-swap="outerHTML"
          class="text-red-600 text-xs hover:underline">Refuser</button>
  {% endif %}
</div>
```

---

## 10. Dashboard (`dashboard/views.py`)

```python
from django.shortcuts import render
from employees.models import Employee
from leaves.models import LeaveRequest
from recruitment.models import JobPosting, Candidate

def dashboard(request):
    context = {
        "total_employes": Employee.objects.filter(statut="actif").count(),
        "conges_en_attente": LeaveRequest.objects.filter(statut="en_attente").count(),
        "offres_ouvertes": JobPosting.objects.filter(statut="ouvert").count(),
        "derniers_employes": Employee.objects.order_by("-date_embauche")[:5],
        "derniers_conges": LeaveRequest.objects.select_related("employe").order_by("-date_demande")[:5],
    }
    return render(request, "dashboard/index.html", context)
```

---

## 11. Protection CSRF pour HTMX

Dans `base.html`, ajouter ce script pour que HTMX envoie automatiquement le token CSRF :

```html
<script>
  document.body.addEventListener("htmx:configRequest", (event) => {
    event.detail.headers["X-CSRFToken"] = "{{ csrf_token }}";
  });
</script>
```

Ou utiliser le middleware `django-htmx` qui le gère automatiquement.

---

## 12. URLs par application

### `employees/urls.py`

```python
from django.urls import path
from . import views

app_name = "employees"

urlpatterns = [
    path("", views.employee_list, name="list"),
    path("nouveau/", views.employee_create, name="create"),
    path("<int:pk>/", views.employee_detail, name="detail"),
    path("<int:pk>/modifier/", views.employee_update, name="update"),
    path("<int:pk>/supprimer/", views.employee_delete, name="delete"),
]
```

---

## 13. Migrations et données initiales

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Optionnel : charger des données de démo
python manage.py loaddata demo_data.json
```

---

## 14. Lancer le projet

```bash
python manage.py runserver
```

Accéder à `http://127.0.0.1:8000/`

---

## 15. Correspondance React → Django/HTMX

| Composant React | Équivalent Django/HTMX |
|----------------|------------------------|
| `useState` pour filtres | `hx-get` + query params |
| `useState` pour onglets | `hx-get` + `hx-target` |
| `fetch` / API calls | Vues Django retournant des partiels HTML |
| Composants réutilisables | `{% include %}` + partials |
| React Router | `hx-push-url="true"` + vues Django |
| Formulaires contrôlés | Django Forms + `crispy-forms` |
| Mise à jour locale du DOM | `hx-swap` + `hx-target` |

---

## Structure finale des dossiers

```
apdpvp-rh/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── sidebar.html
│   │   └── header.html
│   ├── dashboard/
│   ├── employees/
│   │   └── partials/
│   ├── leaves/
│   │   └── partials/
│   ├── recruitment/
│   ├── training/
│   └── documents/
├── static/
│   └── css/
├── employees/
├── leaves/
├── recruitment/
├── training/
├── documents/
├── dashboard/
├── manage.py
└── requirements.txt
```

### `requirements.txt`

```
django>=5.0
django-htmx>=1.17
django-crispy-forms>=2.1
crispy-tailwind>=1.0
pillow>=10.0
psycopg2-binary>=2.9
```