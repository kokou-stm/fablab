from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, Q

from fablabs.models import FabLab
from equipment.models import Equipment, EquipmentCategory, MaintenanceTicket
from reservations.models import Reservation, Certification, UserCertification
from workshops.models import Workshop
from inventory.models import InventoryItem
from projects.models import Project
from accounts.decorators import role_required, fabmanager_required, approved_member_required
from core.emails import send_tenant_registered_email, send_member_signup_notification, send_member_approved_email
from core.models import Channel, MessageTag, Message, ChannelReadStatus

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

    response = render(request, 'landing/index.html', context)
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        response['HX-Redirect'] = '/'
    return response


@approved_member_required
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
    """Permet de basculer instantanément d'un FabLab à un autre (Multi-tenancy pour SuperAdmin et Visiteurs)."""
    if request.user.is_authenticated and not (request.user.is_superuser or getattr(request.user, 'role', '') == 'ADMIN'):
        messages.error(request, "Vous n'avez pas la permission de changer d'espace FabLab.")
        redirect_url = request.META.get('HTTP_REFERER', '/')
        return redirect(redirect_url)

    fablab = get_object_or_404(FabLab, slug=slug)
    request.session['tenant_slug'] = fablab.slug
    if request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'role', '') == 'ADMIN'):
        request.user.fablab = fablab
        request.user.save()
    messages.success(request, f"Vous êtes maintenant sur le tenant : {fablab.name}")
    redirect_url = request.META.get('HTTP_REFERER', '/')
    return redirect(redirect_url)


def equipment_list_view(request):
    category_slug = request.GET.get('category')
    status_filter = request.GET.get('status')
    search_query = (request.GET.get('q') or request.GET.get('search') or '').strip()

    # Initialisation des catégories par défaut incluant "Autre"
    EquipmentCategory.objects.get_or_create(slug="impression-3d", defaults={"name": "Impression 3D", "icon": "printer"})
    EquipmentCategory.objects.get_or_create(slug="decoupe-laser", defaults={"name": "Découpe Laser", "icon": "zap"})
    EquipmentCategory.objects.get_or_create(slug="usinage-cnc", defaults={"name": "Usinage CNC", "icon": "settings"})
    EquipmentCategory.objects.get_or_create(slug="electronique", defaults={"name": "Électronique & IoT", "icon": "cpu"})
    EquipmentCategory.objects.get_or_create(slug="autre", defaults={"name": "Autre", "icon": "box"})

    equipments = Equipment.objects.all()
    categories = EquipmentCategory.objects.all()

    if category_slug:
        equipments = equipments.filter(category__slug=category_slug)
    if status_filter:
        equipments = equipments.filter(status=status_filter)
    if search_query:
        equipments = equipments.filter(
            Q(name__icontains=search_query) |
            Q(model_number__icontains=search_query) |
            Q(location_zone__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    context = {
        'equipments': equipments,
        'categories': categories,
        'current_category': category_slug,
        'current_status': status_filter,
        'search_query': search_query,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'equipment/partials/equipment_grid.html', context)
    return render(request, 'equipment/list.html', context)


@role_required('ADMIN', 'FABMANAGER')
def equipment_create_view(request):
    """Permet au FabManager/Admin d'ajouter une nouvelle machine au parc d'équipements."""
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category_id')
        location_zone = request.POST.get('location_zone', 'Atelier Principal')
        power_watts = request.POST.get('power_watts', 0)
        description = request.POST.get('description', '')
        requires_cert = request.POST.get('requires_certification') == 'on'
        image_file = request.FILES.get('image')
        doc_file = request.FILES.get('doc_file')
        doc_url = request.POST.get('doc_url', '').strip()

        category = get_object_or_404(EquipmentCategory, id=category_id)
        slug = slugify(name)

        count = 1
        base_slug = slug
        while Equipment.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        equipment = Equipment.objects.create(
            name=name,
            slug=slug,
            category=category,
            location_zone=location_zone,
            hourly_rate=0.00,
            power_watts=power_watts or 0,
            description=description,
            requires_certification=requires_cert,
            image=image_file,
            doc_file=doc_file,
            doc_url=doc_url if doc_url else None,
            status='AVAILABLE'
        )
        messages.success(request, f"La machine '{equipment.name}' a été ajoutée avec succès au parc d'équipements !")
        return redirect('equipment_list')
    return redirect('equipment_list')


def equipment_detail_view(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)

    if request.method == 'POST' and request.POST.get('action') == 'update_equipment':
        if not request.user.is_authenticated or not request.user.is_fabmanager_user:
            messages.error(request, "Seul le FabManager est autorisé à modifier les machines.")
            return redirect('equipment_detail', slug=slug)

        equipment.name = request.POST.get('name', equipment.name).strip()
        category_id = request.POST.get('category_id')
        if category_id:
            equipment.category = get_object_or_404(EquipmentCategory, id=category_id)

        equipment.status = request.POST.get('status', equipment.status)
        equipment.location_zone = request.POST.get('location_zone', equipment.location_zone)
        equipment.power_watts = request.POST.get('power_watts', equipment.power_watts)
        
        try:
            equipment.hourly_rate = float(request.POST.get('hourly_rate', equipment.hourly_rate))
        except (ValueError, TypeError):
            pass

        equipment.requires_certification = request.POST.get('requires_certification') == 'on'
        equipment.description = request.POST.get('description', equipment.description)
        equipment.safety_instructions = request.POST.get('safety_instructions', equipment.safety_instructions)
        equipment.doc_url = request.POST.get('doc_url', '').strip() or None

        if request.FILES.get('image'):
            equipment.image = request.FILES.get('image')
        if request.FILES.get('doc_file'):
            equipment.doc_file = request.FILES.get('doc_file')

        equipment.save()
        messages.success(request, f"La fiche de la machine '{equipment.name}' a été mise à jour avec succès !")
        return redirect('equipment_detail', slug=equipment.slug)

    tickets = equipment.maintenance_tickets.all()
    recent_reservations = equipment.reservations.all()[:5]
    categories = EquipmentCategory.objects.all()

    context = {
        'equipment': equipment,
        'tickets': tickets,
        'recent_reservations': recent_reservations,
        'categories': categories,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'equipment/partials/detail_content.html', context)
    return render(request, 'equipment/detail.html', context)


def reservation_list_view(request):
    reservations = Reservation.objects.all()
    equipments = Equipment.objects.filter(status='AVAILABLE')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour effectuer une réservation.")
            return redirect('login')

        action = request.POST.get('action')

        # Action d'Approbation / Refus par le FabManager / Admin
        if action in ['approve_reservation', 'reject_reservation']:
            if not request.user.is_superuser and not request.user.is_fabmanager_user:
                messages.error(request, "Seul le FabManager est autorisé à valider ou refuser les réservations.")
                return redirect('reservation_list')

            res_id = request.POST.get('reservation_id')
            res_obj = get_object_or_404(Reservation, id=res_id)
            if action == 'approve_reservation':
                res_obj.status = 'APPROVED'
                res_obj.save()
                messages.success(request, f"✓ La réservation #{res_obj.id} pour {res_obj.user_full_name} a été confirmée !")
            elif action == 'reject_reservation':
                res_obj.status = 'CANCELLED'
                res_obj.save()
                messages.info(request, f"✕ La réservation #{res_obj.id} a été refusée.")
            return redirect('reservation_list')

        # Nouvelles demandes de réservation
        if not request.user.is_superuser and not request.user.is_fabmanager_user and not getattr(request.user, 'is_approved', False):
            messages.error(request, "Votre compte est actuellement en attente de validation par le responsable du FabLab. Vous ne pouvez pas encore effectuer de réservations.")
            return redirect('reservation_list')

        equipment_id = request.POST.get('equipment_id')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        project_desc = request.POST.get('project_description', '')

        if equipment_id and start_time and end_time:
            eq = get_object_or_404(Equipment, id=equipment_id)

            # Vérification de l'habilitation obligatoire sur la machine
            if eq.requires_certification and not (request.user.is_superuser or request.user.is_fabmanager_user):
                has_cert = UserCertification.objects.filter(
                    user=request.user,
                    certification__category=eq.category,
                    is_active=True
                ).exists() or getattr(request.user, 'is_certified', False)

                if not has_cert:
                    messages.error(request, f"La machine '{eq.name}' nécessite une habilitation/formation active pour la catégorie '{eq.category.name}'. Veuillez contacter un Formateur.")
                    return redirect('reservation_list')

            Reservation.objects.create(
                equipment=eq,
                user=request.user,
                user_username=request.user.username,
                user_full_name=request.user.get_full_name() or request.user.username,
                start_time=start_time,
                end_time=end_time,
                project_description=project_desc,
                status='PENDING',
                total_cost=eq.hourly_rate * 2
            )
            messages.success(request, f"⏳ Votre demande de réservation sur {eq.name} a été enregistrée avec succès ! Elle est en attente de validation par le FabManager.")
            return redirect('reservation_list')

    context = {
        'reservations': reservations,
        'equipments': equipments,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'reservations/partials/reservation_table.html', context)
    return render(request, 'reservations/list.html', context)


def reservation_cancel_view(request, pk):
    """Annulation d'une réservation (par son auteur, un FabManager ou un Admin uniquement)."""
    reservation = get_object_or_404(Reservation, id=pk)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour effectuer cette action.")
            return redirect('login')

        is_owner = reservation.user_id == request.user.id
        if not (is_owner or request.user.is_superuser or request.user.is_fabmanager_user):
            messages.error(request, "Vous ne pouvez annuler que vos propres réservations.")
            return redirect('reservation_list')

        reservation.status = 'CANCELLED'
        reservation.save()
        messages.success(request, f"La réservation #{reservation.id} a été annulée avec succès.")
    return redirect('reservation_list')


@approved_member_required
def reservation_calendar_view(request):
    """Vue du planning/calendrier centralisé multi-machines."""
    equipments = Equipment.objects.all()
    context = {'equipments': equipments}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'reservations/partials/calendar_content.html', context)
    return render(request, 'reservations/calendar.html', context)


@approved_member_required
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


@approved_member_required
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
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'reservations/partials/history_content.html', context)
    return render(request, 'reservations/usage_history.html', context)


@approved_member_required
def certification_list_view(request):
    certifications = Certification.objects.all()
    user_certs = UserCertification.objects.all()

    if request.method == 'POST':
        if not (request.user.is_superuser or request.user.is_fabmanager_user or request.user.role == 'INSTRUCTOR'):
            messages.error(request, "Seuls les Formateurs et FabManagers peuvent accorder une habilitation.")
            return redirect('certification_list')

        member_id = request.POST.get('member_id')
        cert_id = request.POST.get('certification_id')
        if member_id and cert_id:
            target_user = get_object_or_404(User, id=member_id)
            cert = get_object_or_404(Certification, id=cert_id)
            UserCertification.objects.get_or_create(
                user=target_user,
                certification=cert,
                defaults={
                    'user_username': target_user.username,
                    'user_full_name': target_user.get_full_name() or target_user.username,
                    'is_active': True
                }
            )
            target_user.is_certified = True
            target_user.save()
            messages.success(request, f"Habilitation '{cert.name}' accordée avec succès à {target_user.get_full_name() or target_user.username} !")
            return redirect('certification_list')

    members = User.objects.filter(fablab=request.tenant) if getattr(request, 'tenant', None) else User.objects.all()
    context = {
        'certifications': certifications,
        'user_certs': user_certs,
        'members': members,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'certifications/partials/cert_content.html', context)
    return render(request, 'certifications/list.html', context)


def workshop_list_view(request):
    workshops = Workshop.objects.all()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour vous inscrire à un atelier.")
            return redirect('login')

        if not request.user.is_superuser and not request.user.is_fabmanager_user and not getattr(request.user, 'is_approved', False):
            messages.error(request, "Votre compte est actuellement en attente de validation par le responsable du FabLab.")
            return redirect('workshop_list')

        workshop_id = request.POST.get('workshop_id')
        if workshop_id:
            ws = get_object_or_404(Workshop, id=workshop_id)

            if ws.available_seats <= 0:
                messages.error(request, f"L'atelier '{ws.title}' est complet (0 place disponible).")
                return redirect('workshop_list')

            if ws.registrations.filter(user=request.user).exists():
                messages.error(request, f"Vous êtes déjà inscrit à l'atelier '{ws.title}'.")
                return redirect('workshop_list')

            ws.registrations.create(
                user=request.user,
                user_full_name=request.user.get_full_name() or request.user.username,
                user_email=request.user.email,
                payment_status='FREE' if ws.price == 0 else 'PAID'
            )
            messages.success(request, f"Inscription réussie à l'atelier '{ws.title}' !")
            return redirect('workshop_list')

    context = {'workshops': workshops}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'workshops/partials/workshop_cards.html', context)
    return render(request, 'workshops/list.html', context)


@approved_member_required
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


@approved_member_required
def project_create_view(request):
    """Formulaire de publication d'un nouveau projet Maker."""
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

    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'projects/partials/create_content.html')
    return render(request, 'projects/create.html')


@approved_member_required
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
                reported_by=request.user,
                reported_by_username=request.user.get_full_name() or request.user.username,
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
        custom_domain = request.POST.get('domain', '').strip().lower() or None
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

        # Validation unicité du nom de domaine personnalisé
        if custom_domain and FabLab.objects.filter(domain__iexact=custom_domain).exists():
            messages.error(request, f"Le nom de domaine '{custom_domain}' est déjà utilisé par un autre espace.")
            return render(request, 'accounts/register_tenant.html', {'lab_name': lab_name, 'contact_email': contact_email})

        justification_doc = request.FILES.get('justification_document')

        # 1. Création du Tenant Master
        fablab = FabLab.objects.create(
            name=lab_name,
            slug=clean_slug,
            domain=custom_domain,
            contact_email=contact_email,
            city=city,
            plan=plan,
            is_active=True,
            is_approved=False,
            justification_document=justification_doc
        )

        # 2. Création de l'utilisateur Admin/FabManager lié (en attente de validation SuperAdmin)
        user = User.objects.create_user(
            username=admin_username,
            email=contact_email,
            password=password,
            first_name=admin_name,
            role='FABMANAGER',
            fablab=fablab,
            is_approved=False
        )

        # 3. Provisionnement du Schéma Postgres isolé pour la nouvelle école
        migrate_tenant(clean_slug)
        set_current_tenant(clean_slug)

        # 4. Populer les catégories par défaut dans le nouveau schéma
        EquipmentCategory.objects.get_or_create(slug="impression-3d", defaults={"name": "Impression 3D", "icon": "printer"})
        EquipmentCategory.objects.get_or_create(slug="decoupe-laser", defaults={"name": "Découpe Laser", "icon": "zap"})
        EquipmentCategory.objects.get_or_create(slug="usinage-cnc", defaults={"name": "Usinage CNC", "icon": "settings"})
        EquipmentCategory.objects.get_or_create(slug="electronique", defaults={"name": "Électronique & IoT", "icon": "cpu"})
        EquipmentCategory.objects.get_or_create(slug="autre", defaults={"name": "Autre", "icon": "box"})

        # 5. Notification Email de confirmation d'inscription d'espace
        send_tenant_registered_email(fablab, user)

        # 6. Connexion & Redirection avec notification d'examen par le SuperAdmin
        request.session['tenant_slug'] = clean_slug
        login(request, user)

        messages.info(
            request, 
            f"L'espace FabLab '{fablab.name}' a été créé avec succès ! Votre demande a été transmise au SuperAdmin pour validation."
        )
        return redirect('signup_pending')

    return render(request, 'accounts/register_tenant.html')


from django.http import JsonResponse

def notifications_api_view(request):
    """API de notifications en temps réel pour la cloche du topbar."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0, 'items': []})

    items = []

    # 1. Pour les FabManagers et SuperAdmins : Réservations en attente
    if request.user.is_superuser or request.user.is_fabmanager_user:
        pending_res = Reservation.objects.filter(status='PENDING')
        for r in pending_res[:5]:
            items.append({
                'id': f"res-{r.id}",
                'icon': '⏳',
                'title': 'Réservation à valider',
                'text': f"{r.user_full_name} a demandé la machine {r.equipment.name}",
                'url': '/reservations/',
                'time': r.created_at.strftime('%H:%M')
            })

        # 2. Pour les FabManagers : Membres en attente d'approbation
        pending_members = User.objects.filter(is_approved=False, is_superuser=False)
        for m in pending_members[:5]:
            items.append({
                'id': f"mem-{m.id}",
                'icon': '👤',
                'title': 'Nouvel inscrit en attente',
                'text': f"{m.get_full_name() or m.username} ({m.get_role_display()}) attend votre validation.",
                'url': '/members/',
                'time': m.date_joined.strftime('%H:%M')
            })

        # 3. Tickets de maintenance ouverts
        open_tickets = MaintenanceTicket.objects.filter(status='OPEN')
        for t in open_tickets[:3]:
            items.append({
                'id': f"maint-{t.id}",
                'icon': '🛠️',
                'title': 'Incident signalé',
                'text': f"{t.equipment.name} : {t.issue_title}",
                'url': '/maintenance/',
                'time': t.created_at.strftime('%H:%M')
            })
    else:
        # Pour les membres réguliers : Leurs réservations validées
        my_res = Reservation.objects.filter(user=request.user, status='APPROVED')[:5]
        for r in my_res:
            items.append({
                'id': f"myres-{r.id}",
                'icon': '✓',
                'title': 'Réservation Confirmée',
                'text': f"Votre créneau sur {r.equipment.name} est validé.",
                'url': '/reservations/',
                'time': r.created_at.strftime('%H:%M')
            })

    # Notifications pour les messages reçus et mentions @username
    unread_dms = Message.objects.filter(recipient=request.user, is_read=False)[:3]
    for msg in unread_dms:
        items.append({
            'id': f"dm-{msg.id}",
            'icon': '💬',
            'title': f"Message privé de {msg.sender_username}",
            'text': msg.content[:55] + ('...' if len(msg.content) > 55 else ''),
            'url': f"/messaging/?dm={msg.sender.id}",
            'time': msg.created_at.strftime('%H:%M')
        })

    mention_msgs = Message.objects.filter(content__icontains=f"@{request.user.username}").exclude(sender=request.user).order_by('-created_at')[:3]
    for msg in mention_msgs:
        items.append({
            'id': f"mention-{msg.id}",
            'icon': '💬',
            'title': f"Mention par @{msg.sender_username}",
            'text': msg.content[:55] + ('...' if len(msg.content) > 55 else ''),
            'url': f"/messaging/?channel={msg.channel.slug}" if msg.channel else f"/messaging/?dm={msg.sender.id}",
            'time': msg.created_at.strftime('%H:%M')
        })

    return JsonResponse({
        'count': len(items),
        'items': items
    })


from core.models import Channel, MessageTag, Message
from accounts.models import User

@approved_member_required
def messaging_view(request):
    """Messagerie Interne Collaborative Multi-tenant (Style ikiu/Slack)."""
    # 1. Initialiser les canaux par défaut pour le tenant s'ils n'existent pas encore
    Channel.objects.get_or_create(slug="general", defaults={"name": "Général & Discussion", "icon": "", "channel_type": "PUBLIC", "description": "Échanges libres et actualités du FabLab"})
    Channel.objects.get_or_create(slug="annonces", defaults={"name": "Annonces Officielles", "icon": "", "channel_type": "PUBLIC", "description": "Communications officielles de l'équipe"})
    Channel.objects.get_or_create(slug="entraide", defaults={"name": "Entraide & Projets", "icon": "", "channel_type": "HELP", "description": "Questions techniques, fichiers 3D, conseils découpe & électronique"})
    Channel.objects.get_or_create(slug="maintenance", defaults={"name": "Pannes & Signalements", "icon": "", "channel_type": "HELP", "description": "Informations sur l'état des machines et incidents"})
    Channel.objects.get_or_create(slug="fabmanagers", defaults={"name": "Espace FabManagers", "icon": "", "channel_type": "FABMANAGER", "description": "Canal restreint pour l'équipe d'administration"})

    # Initialiser les tags par défaut
    MessageTag.objects.get_or_create(slug="projet", defaults={"name": "Projet", "color": "#3b82f6"})
    MessageTag.objects.get_or_create(slug="panne", defaults={"name": "Panne / Maintenance", "color": "#ef4444"})
    MessageTag.objects.get_or_create(slug="question", defaults={"name": "Question", "color": "#f59e0b"})
    MessageTag.objects.get_or_create(slug="urgent", defaults={"name": "Urgent", "color": "#dc2626"})
    MessageTag.objects.get_or_create(slug="habilitation", defaults={"name": "Habilitation", "color": "#8b5cf6"})
    MessageTag.objects.get_or_create(slug="formation", defaults={"name": "Formation", "color": "#10b981"})

    tags = MessageTag.objects.all()

    # Déterminer le FabLab tenant actif pour filtrer strictly les membres
    current_lab = getattr(request, 'tenant', None) or request.user.fablab

    # Filtrer les canaux selon le rôle et les invitations privées (M2M multi-tenant check)
    ThroughModel = Channel.members.through
    user_channel_ids = set(ThroughModel.objects.filter(user_id=request.user.id).values_list('channel_id', flat=True))

    all_channels = Channel.objects.all()
    channels = []
    for ch in all_channels:
        if ch.channel_type == 'FABMANAGER':
            if request.user.is_superuser or request.user.is_fabmanager_user:
                channels.append(ch)
        elif ch.is_private or ch.channel_type == 'GROUP':
            # Visible uniquement si le membre est invité dans le groupe, créateur du groupe, ou FabManager/Admin
            if ch.creator == request.user or ch.id in user_channel_ids or request.user.is_fabmanager_user or request.user.is_superuser:
                channels.append(ch)
        else:
            channels.append(ch)

    # Sélection du canal ou du DM
    channel_slug = request.GET.get('channel', 'general')
    tag_slug = request.GET.get('tag')
    dm_user_id = request.GET.get('dm')

    if not channels:
        general_ch, _ = Channel.objects.get_or_create(slug="general", defaults={"name": "Général & Discussion", "description": "Échanges libres et actualités du FabLab"})
        channels = [general_ch]

    active_channel = next((c for c in channels if c.slug == channel_slug), None) or channels[0]
    active_dm_user = None

    if dm_user_id:
        if current_lab:
            active_dm_user = User.objects.filter(id=dm_user_id, fablab=current_lab, is_approved=True).first()
        else:
            active_dm_user = User.objects.filter(id=dm_user_id, is_approved=True).first()

    # Récupérer uniquement les membres du MÊME FabLab tenant pour la messagerie et les DMs
    if current_lab:
        members = User.objects.filter(is_approved=True, fablab=current_lab).exclude(id=request.user.id)
    else:
        members = User.objects.filter(is_approved=True).exclude(id=request.user.id)

    if not members.exists():
        members = User.objects.filter(is_approved=True).exclude(id=request.user.id)

    # 2. Traitement des formulaires POST (Création de canal, Invitation, Envoi de message)
    if request.method == 'POST':
        action = request.POST.get('action')

        # Action A: Création d'un nouveau canal de discussion par un Enseignant, Formateur ou FabManager
        if action == 'create_channel':
            is_allowed = request.user.is_superuser or request.user.is_fabmanager_user or getattr(request.user, 'is_instructor_user', False)
            if not is_allowed:
                messages.error(request, "Seuls les Enseignants, Formateurs et FabManagers peuvent créer de nouveaux canaux de discussion.")
                return redirect('/messaging/')

            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_private = request.POST.get('is_private') == '1'
            invited_member_ids = request.POST.getlist('members')

            if name:
                from django.utils.text import slugify
                import time
                base_slug = slugify(name) or f"group-{int(time.time())}"
                slug = base_slug
                count = 1
                while Channel.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{count}"
                    count += 1

                new_channel = Channel.objects.create(
                    name=name,
                    slug=slug,
                    description=description,
                    channel_type='GROUP' if is_private else 'PUBLIC',
                    is_private=is_private,
                    creator=request.user
                )
                new_channel.members.add(request.user)
                if invited_member_ids:
                    new_channel.members.add(*invited_member_ids)

                messages.success(request, f"Canal #{name} créé avec succès !")
                return redirect(f"/messaging/?channel={new_channel.slug}")

        # Action B: Inviter des membres supplémentaires dans le canal actif
        elif action == 'invite_members':
            invited_member_ids = request.POST.getlist('members')
            if active_channel and invited_member_ids:
                if active_channel.creator == request.user or request.user.is_fabmanager_user or request.user.is_superuser:
                    active_channel.members.add(*invited_member_ids)
                    messages.success(request, "Membres invités avec succès dans le groupe !")
                else:
                    messages.error(request, "Seul le créateur du groupe ou un FabManager peut inviter des membres.")
            return redirect(f"/messaging/?channel={active_channel.slug if active_channel else 'general'}")

        # Action C: Envoi normal de message dans le canal ou DM
        else:
            content = request.POST.get('content', '').strip()
            attachment = request.FILES.get('attachment')
            selected_tag_ids = request.POST.getlist('tags')

            # Restriction : Seuls les FabManagers et Admins peuvent poster dans #annonces
            if not active_dm_user and active_channel and active_channel.slug == 'annonces':
                if not (request.user.is_superuser or request.user.is_fabmanager_user):
                    messages.error(request, "Seuls les FabManagers et l'équipe d'administration peuvent publier dans le canal des annonces officielles.")
                    return redirect(f"/messaging/?channel={active_channel.slug}")

            if content or attachment:
                msg = Message.objects.create(
                    channel=active_channel if not active_dm_user else None,
                    recipient=active_dm_user if active_dm_user else None,
                    sender=request.user,
                    sender_username=request.user.get_full_name() or request.user.username,
                    sender_role=request.user.get_role_display(),
                    content=content,
                    attachment=attachment,
                    is_announcement=(active_channel and active_channel.slug == 'annonces')
                )
                if selected_tag_ids:
                    msg.tags.set(selected_tag_ids)

                if not request.headers.get('HX-Request'):
                    messages.success(request, "Message envoyé !")
                    if active_dm_user:
                        return redirect(f"/messaging/?dm={active_dm_user.id}")
                    return redirect(f"/messaging/?channel={active_channel.slug}")

    # 3. Récupération des messages & Marquage comme lu (is_read = True)
    if active_dm_user:
        # Marquer automatiquement comme lus les messages privés reçus de cet interlocuteur
        Message.objects.filter(sender=active_dm_user, recipient=request.user, is_read=False).update(is_read=True)

        message_list = Message.objects.filter(
            (Q(sender=request.user) & Q(recipient=active_dm_user)) |
            (Q(sender=active_dm_user) & Q(recipient=request.user))
        ).prefetch_related('tags')
    else:
        message_list = Message.objects.filter(channel=active_channel).prefetch_related('tags')
        # Mettre à jour le statut de lecture du canal actif pour l'utilisateur
        if active_channel:
            latest_msg = message_list.last()
            if latest_msg:
                ChannelReadStatus.objects.update_or_create(
                    user=request.user,
                    channel=active_channel,
                    defaults={'last_read_message': latest_msg}
                )

    if tag_slug:
        message_list = message_list.filter(tags__slug=tag_slug)

    # Récupérer uniquement les membres du MÊME FabLab tenant pour la messagerie et les DMs
    if current_lab:
        members_qs = User.objects.filter(is_approved=True, fablab=current_lab).exclude(id=request.user.id)
    else:
        members_qs = User.objects.filter(is_approved=True).exclude(id=request.user.id)

    if not members_qs.exists():
        members_qs = User.objects.filter(is_approved=True).exclude(id=request.user.id)

    # 4. Calcul des notifications / badges de messages non lus (Style Discord / WhatsApp)
    # A) Messages directs (DMs) non lus par expéditeur
    from django.db.models import Count
    unread_dm_qs = Message.objects.filter(recipient=request.user, is_read=False).values('sender_id').annotate(count=Count('id'))
    unread_dm_counts = {item['sender_id']: item['count'] for item in unread_dm_qs}

    members = list(members_qs)
    for m in members:
        m.unread_count = unread_dm_counts.get(m.id, 0)

    # B) Messages non lus par canal de discussion
    read_statuses = {rs.channel_id: rs.last_read_message_id for rs in ChannelReadStatus.objects.filter(user=request.user)}
    for ch in channels:
        if active_channel and ch.id == active_channel.id and not active_dm_user:
            ch.unread_count = 0
        else:
            last_read_id = read_statuses.get(ch.id)
            if last_read_id:
                ch.unread_count = Message.objects.filter(channel=ch, id__gt=last_read_id).exclude(sender=request.user).count()
            else:
                ch.unread_count = Message.objects.filter(channel=ch).exclude(sender=request.user).count()

    context = {
        'tenant': current_lab or getattr(request, 'tenant', None),
        'channels': channels,
        'active_channel': active_channel,
        'active_dm_user': active_dm_user,
        'message_list': message_list,
        'tags': tags,
        'selected_tag': tag_slug,
        'members': members,
    }

    # N'envoyer le partiel message_thread.html QUE pour le rafraîchissement automatique du fil de discussion (polling sans toucher à la zone de saisie)
    # N'envoyer le partiel chat_box.html QUE lorsque la cible HTMX est le container complet du tchat (#chat-container)
    # Pour les navigations HTMX normales (#content), envoyer le partiel messaging_content.html (sans re-étendre base.html)
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        if request.GET.get('thread_only') == '1' or request.headers.get('HX-Target') == 'message-thread':
            return render(request, 'messaging/partials/message_thread.html', context)
        if request.headers.get('HX-Target') == 'chat-container':
            return render(request, 'messaging/partials/chat_box.html', context)
        return render(request, 'messaging/partials/messaging_content.html', context)
    return render(request, 'messaging/index.html', context)
