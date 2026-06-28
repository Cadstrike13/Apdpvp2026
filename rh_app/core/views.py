from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.shortcuts import render

from .roles import Roles
from .permissions import role_required, GESTION_ROLES
from .jwt_utils import encode_token
from .models import AuditLog

User = get_user_model()


# ============ Gestion des rôles (réservée admin / directeur) ============
def _roles_context():
    groups = {
        g.name: g
        for g in Group.objects.filter(name__in=Roles.ALL).prefetch_related("user_set", "permissions")
    }
    roles = []
    for code, label in Roles.CHOICES:
        g = groups.get(code)
        roles.append({
            "code": code,
            "label": label,
            "members": list(g.user_set.all()) if g else [],
            "perm_count": g.permissions.count() if g else 0,
        })
    return roles


@role_required(*GESTION_ROLES)
def role_list(request):
    context = {
        "roles": _roles_context(),
        "users": User.objects.order_by("username"),
        "role_choices": Roles.CHOICES,
    }
    template = "roles/partials/content.html" if request.htmx else "roles/list.html"
    return render(request, template, context)


@role_required(*GESTION_ROLES)
def role_assign(request):
    if request.method == "POST":
        user_id = request.POST.get("user")
        role = request.POST.get("role")
        if user_id and role in Roles.ALL:
            user = User.objects.filter(pk=user_id).first()
            group = Group.objects.filter(name=role).first()
            if user and group:
                user.groups.add(group)
    return render(request, "roles/partials/table.html", {"roles": _roles_context()})


@role_required(*GESTION_ROLES)
def role_remove(request, role, user_id):
    if request.method in ("POST", "DELETE"):
        user = User.objects.filter(pk=user_id).first()
        group = Group.objects.filter(name=role).first()
        if user and group:
            user.groups.remove(group)
    return render(request, "roles/partials/table.html", {"roles": _roles_context()})


# ============ Journal d'audit (réservé admin / directeur) ============
@role_required(*GESTION_ROLES)
def audit_log(request):
    logs = AuditLog.objects.select_related("user")
    action = request.GET.get("action", "")
    q = request.GET.get("q", "")
    if action:
        logs = logs.filter(action=action)
    if q:
        logs = logs.filter(object_repr__icontains=q) | logs.filter(username__icontains=q)
    logs = logs[:200]
    context = {"logs": logs, "actions": AuditLog.ACTION_CHOICES, "action_selected": action, "query": q}
    if request.htmx and (request.GET.get("action") is not None or request.GET.get("q") is not None):
        return render(request, "audit/partials/table.html", context)
    template = "audit/partials/content.html" if request.htmx else "audit/list.html"
    return render(request, context_template := template, context)


# ============ Émission d'un JWT pour l'utilisateur connecté (inter-services) ============
def token(request):
    return JsonResponse({
        "access_token": encode_token(request.user),
        "token_type": "Bearer",
    })
