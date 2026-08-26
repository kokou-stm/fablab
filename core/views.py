from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count

from fablabs.models import FabLab
from equipment.models import Equipment, EquipmentCategory, MaintenanceTicket
from reservations.models import Reservation, Certification, UserCertification
from workshops.models import Workshop
from inventory.models import InventoryItem
from projects.models import Project

def landing_view(request):
    """Vue de la page d'accueil (Landing Page) institutionnelle et vitrine FabOS."""
    equipments = Equipment.objects.all()[:6]
    workshops = Workshop.objects.all()[:3]
    recent_projects = Project.objects.filter(is_public=True)[:3]
    all_tenants = FabLab.objects.all()

    total_machines = Equipment.objects.count()
    active_machines = Equipment.objects.filter(status='AVAILABLE').count()
    total_reservations = Reservation.objects.count()
    total_workshops = Workshop.objects.count()
    total_projects = Project.objects.count()
    total_tenants = FabLab.objects.count()

    context = {
        'equipments': equipments,
        'workshops': workshops,
        'recent_projects': recent_projects,
        'all_tenants': all_tenants,
        'total_machines': total_machines,
        'active_machines': active_machines,
        'total_reservations': total_reservations,
        'total_workshops': total_workshops,
        'total_projects': total_projects,
        'total_tenants': total_tenants,
    }

    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'landing/partials/landing_content.html', context)
    return render(request, 'landing/index.html', context)


def dashboard_view(request):
    """Vue principale du Tableau de bord (compatible HTMX)."""
    equipments = Equipment.objects.all()
    reservations = Reservation.objects.all()[:5]
    workshops = Workshop.objects.all()[:4]
    inventory_alerts = InventoryItem.objects.filter(quantity__lte=5)
    recent_projects = Project.objects.all()[:3]
    tickets = MaintenanceTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS'])

    # KPI Analytics
    total_machines = equipments.count()
    active_machines = equipments.filter(status='AVAILABLE').count()
    maintenance_count = equipments.filter(status='MAINTENANCE').count()
    in_use_count = equipments.filter(status='RESERVED').count()
    total_reservations = Reservation.objects.count()

    context = {
        'equipments': equipments,
        'reservations': reservations,
        'workshops': workshops,
        'inventory_alerts': inventory_alerts,
        'recent_projects': recent_projects,
        'tickets': tickets,
        'total_machines': total_machines,
        'active_machines': active_machines,
        'maintenance_count': maintenance_count,
        'in_use_count': in_use_count,
        'total_reservations': total_reservations,
    }

    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'dashboard/partials/dashboard_content.html', context)
    return render(request, 'dashboard/index.html', context)


def switch_tenant_view(request, slug):
    """Permet de basculer instantanément d'un FabLab à un autre (Multi-tenancy)."""
    fablab = get_object_or_404(FabLab, slug=slug)
    request.session['tenant_slug'] = fablab.slug
    if request.user.is_authenticated:
        request.user.fablab = fablab
        request.user.save()
    messages.success(request, f"Vous êtes maintenant sur le tenant : {fablab.name}")
    redirect_url = request.META.get('HTTP_REFERER', '/')
    return redirect(redirect_url)


def equipment_list_view(request):
    category_slug = request.GET.get('category')
    status_filter = request.GET.get('status')

    equipments = Equipment.objects.all()
    categories = EquipmentCategory.objects.all()

    if category_slug:
        equipments = equipments.filter(category__slug=category_slug)
    if status_filter:
        equipments = equipments.filter(status=status_filter)

    context = {
        'equipments': equipments,
        'categories': categories,
        'current_category': category_slug,
        'current_status': status_filter,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'equipment/partials/equipment_grid.html', context)
    return render(request, 'equipment/list.html', context)


def equipment_detail_view(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)
    tickets = equipment.maintenance_tickets.all()
    recent_reservations = equipment.reservations.all()[:5]

    context = {
        'equipment': equipment,
        'tickets': tickets,
        'recent_reservations': recent_reservations,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'equipment/partials/detail_content.html', context)
    return render(request, 'equipment/detail.html', context)


def reservation_list_view(request):
    reservations = Reservation.objects.all()
    equipments = Equipment.objects.filter(status='AVAILABLE')

    if request.method == 'POST':
        equipment_id = request.POST.get('equipment_id')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        project_desc = request.POST.get('project_description', '')

        if request.user.is_authenticated:
            user_username = request.user.username
            user_name = request.user.get_full_name() or request.user.username
        else:
            user_username = "maker_guest"
            user_name = request.POST.get('user_name', 'Maker Invité')

        if equipment_id and start_time and end_time:
            eq = Equipment.objects.get(id=equipment_id)
            Reservation.objects.create(
                equipment=eq,
                user_username=user_username,
                user_full_name=user_name,
                start_time=start_time,
                end_time=end_time,
                project_description=project_desc,
                status='APPROVED',
                total_cost=eq.hourly_rate * 2
            )
            messages.success(request, f"Réservation créée avec succès sur {eq.name} !")
            return redirect('reservation_list')

    context = {
        'reservations': reservations,
        'equipments': equipments,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'reservations/partials/reservation_table.html', context)
    return render(request, 'reservations/list.html', context)


def reservation_cancel_view(request, pk):
    """Annulation d'une réservation."""
    reservation = get_object_or_404(Reservation, id=pk)
    if request.method == 'POST':
        reservation.status = 'CANCELLED'
        reservation.save()
        messages.success(request, f"La réservation #{reservation.id} a été annulée avec succès.")
    return redirect('reservation_list')


def reservation_calendar_view(request):
    """Vue du planning/calendrier centralisé multi-machines."""
    equipments = Equipment.objects.all()
    return render(request, 'reservations/calendar.html', {'equipments': equipments})


def reservation_calendar_api(request):
    """API renvoyant les réservations au format JSON pour le composant calendrier."""
    reservations = Reservation.objects.exclude(status='CANCELLED')
    events = []
    for r in reservations:
        color = '#10B981' if r.status == 'APPROVED' else ('#3B82F6' if r.status == 'ACTIVE' else '#F59E0B')
        events.append({
            'id': r.id,
            'title': f"{r.equipment.name} - {r.user_full_name}",
            'start': r.start_time.isoformat(),
            'end': r.end_time.isoformat(),
            'status': r.get_status_display(),
            'color': color,
        })
    return JsonResponse(events, safe=False)


def usage_history_view(request):
    """Rapport et suivi d'historique d'utilisation réelle des machines."""
    reservations = Reservation.objects.all().order_by('-start_time')
    total_cost_sum = reservations.aggregate(total=Sum('total_cost'))['total'] or 0
    total_hours = 0
    for r in reservations:
        if r.start_time and r.end_time:
            delta = r.end_time - r.start_time
            total_hours += round(delta.total_seconds() / 3600, 1)

    context = {
        'reservations': reservations,
        'total_cost_sum': total_cost_sum,
        'total_hours': total_hours,
        'total_sessions': reservations.count(),
    }
    return render(request, 'reservations/usage_history.html', context)


def certification_list_view(request):
    certifications = Certification.objects.all()
    user_certs = UserCertification.objects.all()

    context = {
        'certifications': certifications,
        'user_certs': user_certs,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'certifications/partials/cert_content.html', context)
    return render(request, 'certifications/list.html', context)


def workshop_list_view(request):
    workshops = Workshop.objects.all()

    if request.method == 'POST':
        workshop_id = request.POST.get('workshop_id')
        participant_name = request.POST.get('participant_name')
        participant_email = request.POST.get('participant_email')

        if workshop_id and participant_name:
            ws = get_object_or_404(Workshop, id=workshop_id)
            ws.registrations.create(
                user_full_name=participant_name,
                user_email=participant_email,
                payment_status='FREE' if ws.price == 0 else 'PAID'
            )
            messages.success(request, f"Inscription réussie à l'atelier '{ws.title}' !")
            return redirect('workshop_list')

    context = {'workshops': workshops}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'workshops/partials/workshop_cards.html', context)
    return render(request, 'workshops/list.html', context)


def inventory_list_view(request):
    items = InventoryItem.objects.all()

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        add_qty = request.POST.get('add_quantity')
        if item_id and add_qty:
            item = InventoryItem.objects.get(id=item_id)
            item.quantity += Decimal(str(add_qty))
            item.save()
            messages.success(request, f"Stock mis à jour pour {item.name} (+{add_qty} {item.get_unit_display()})")
            return redirect('inventory_list')

    context = {'items': items}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'inventory/partials/inventory_table.html', context)
    return render(request, 'inventory/list.html', context)


def project_list_view(request):
    projects = Project.objects.filter(is_public=True)
    context = {'projects': projects}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'projects/partials/project_grid.html', context)
    return render(request, 'projects/list.html', context)


def project_create_view(request):
    """Formulaire de publication d'un nouveau projet Maker."""
    if not request.user.is_authenticated:
        messages.warning(request, "Veuillez vous connecter pour publier un projet.")
        return redirect('login')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'Impression 3D')
        description = request.POST.get('description', '').strip()
        license_type = request.POST.get('license', 'CC-BY-SA')
        is_public = request.POST.get('is_public') == 'on'

        clean_slug = slugify(title)
        if Project.objects.filter(slug=clean_slug).exists():
            clean_slug = f"{clean_slug}-{Project.objects.count() + 1}"

        project = Project.objects.create(
            title=title,
            slug=clean_slug,
            author=request.user,
            author_name=request.user.get_full_name() or request.user.username,
            category=category,
            description=description,
            license=license_type,
            is_public=is_public,
        )

        if 'cover_image' in request.FILES:
            project.cover_image = request.FILES['cover_image']
            project.save()

        messages.success(request, f"Votre projet '{project.title}' a été publié avec succès !")
        return redirect('project_list')

    return render(request, 'projects/create.html')


def maintenance_list_view(request):
    tickets = MaintenanceTicket.objects.all()
    equipments = Equipment.objects.all()

    if request.method == 'POST':
        eq_id = request.POST.get('equipment_id')
        issue_title = request.POST.get('issue_title')
        description = request.POST.get('description')
        priority = request.POST.get('priority', 'MEDIUM')

        if eq_id and issue_title:
            eq = Equipment.objects.get(id=eq_id)
            MaintenanceTicket.objects.create(
                equipment=eq,
                reported_by_username="Maker",
                issue_title=issue_title,
                description=description,
                priority=priority,
                status='OPEN'
            )
            eq.status = 'MAINTENANCE'
            eq.save()
            messages.success(request, f"Signalement créé pour {eq.name}. Statut passé en maintenance.")
            return redirect('maintenance_list')

    context = {
        'tickets': tickets,
        'equipments': equipments,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'maintenance/partials/tickets_table.html', context)
    return render(request, 'maintenance/list.html', context)


from django.utils.text import slugify
from django.contrib.auth import login, logout, authenticate
from accounts.models import User
from config.tenant_router import migrate_tenant, set_current_tenant

def register_tenant_view(request):
    """Permet à n'importe quelle école ou FabLab de créer son compte et d'isoler son interface."""
    if request.method == 'POST':
        lab_name = request.POST.get('lab_name')
        raw_slug = request.POST.get('slug') or lab_name
        clean_slug = slugify(raw_slug)
        contact_email = request.POST.get('contact_email')
        city = request.POST.get('city', 'Paris')
        plan = request.POST.get('plan', 'UNIVERSITY')
        admin_username = request.POST.get('admin_username')
        admin_name = request.POST.get('admin_name')
        password = request.POST.get('password')

        # Validation unicité slug
        if FabLab.objects.filter(slug=clean_slug).exists():
            messages.error(request, f"L'identifiant/slug '{clean_slug}' est déjà utilisé. Veuillez en choisir un autre.")
            return render(request, 'accounts/register_tenant.html', {'lab_name': lab_name, 'contact_email': contact_email})

        # 1. Création du Tenant Master
        fablab = FabLab.objects.create(
            name=lab_name,
            slug=clean_slug,
            contact_email=contact_email,
            city=city,
            plan=plan,
            is_active=True
        )

        # 2. Création de l'utilisateur Admin/FabManager lié
        user = User.objects.create_user(
            username=admin_username,
            email=contact_email,
            password=password,
            first_name=admin_name,
            role='FABMANAGER',
            fablab=fablab
        )

        # 3. Provisionnement du Schéma Postgres isolé pour la nouvelle école
        migrate_tenant(clean_slug)
        set_current_tenant(clean_slug)

        # 4. Populer les catégories par défaut dans le nouveau schéma
        EquipmentCategory.objects.get_or_create(slug="impression-3d", defaults={"name": "Impression 3D", "icon": "printer"})
        EquipmentCategory.objects.get_or_create(slug="decoupe-laser", defaults={"name": "Découpe Laser", "icon": "zap"})
        EquipmentCategory.objects.get_or_create(slug="usinage-cnc", defaults={"name": "Usinage CNC", "icon": "settings"})
        EquipmentCategory.objects.get_or_create(slug="electronique", defaults={"name": "Électronique & IoT", "icon": "cpu"})

        # 5. Connexion & Redirection vers la nouvelle interface
        request.session['tenant_slug'] = clean_slug
        login(request, user)

        messages.success(request, f"Félicitations ! Votre espace FabLab '{fablab.name}' a été créé avec succès et votre schéma dédié a été initialisé !")
        return redirect('dashboard')

    return render(request, 'accounts/register_tenant.html')

