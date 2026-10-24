import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

MAX_HISTORY = 12
MAX_CHARS = 2000
RATE_LIMIT = 30
RATE_WINDOW = 600


def _system_prompt(request):
    tenant = getattr(request, 'tenant', None) or getattr(request.user, 'fablab', None)
    lab = tenant.name if tenant else "le FabLab"
    name = request.user.get_full_name() or request.user.username
    return (
        f"Tu es l'assistant de LabOS, la plateforme de gestion de {lab}. "
        f"Tu aides {name} (rôle : {request.user.get_role_display()}) à utiliser la plateforme : "
        "équipements et machines, réservations, planning, habilitations et badges, ateliers et formations, "
        "bibliothèque, stocks et consommables, projets, maintenance et messagerie. "
        "Tu peux aussi répondre aux questions générales de fabrication numérique (impression 3D, découpe laser, CNC, électronique). "
        "Réponds en français en vouvoyant l'utilisateur, de façon claire et concise, en texte simple sans Markdown. "
        "Tu n'as pas accès aux données du FabLab : si on te demande une information précise (disponibilité, réservation, stock), "
        "indique la rubrique de LabOS où la trouver."
    )


def _clean_history(raw):
    history = []
    for msg in raw[-MAX_HISTORY:] if isinstance(raw, list) else []:
        if not isinstance(msg, dict):
            continue
        role = msg.get('role')
        content = str(msg.get('content', '')).strip()[:MAX_CHARS]
        if role in ('user', 'assistant') and content:
            history.append({'role': role, 'content': content})
    return history


def _rate_limited(user_id):
    key = f'assistant-rate-{user_id}'
    if cache.add(key, 1, RATE_WINDOW):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, RATE_WINDOW)
        return False
    return count > RATE_LIMIT


@require_POST
def assistant_chat_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': "Connectez-vous pour utiliser l'assistant."}, status=401)
    if not (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY):
        return JsonResponse({'error': "L'assistant n'est pas encore configuré sur cet espace."}, status=503)

    try:
        payload = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'error': 'Requête invalide.'}, status=400)

    history = _clean_history(payload.get('messages'))
    if not history or history[-1]['role'] != 'user':
        return JsonResponse({'error': 'Écrivez un message.'}, status=400)

    if _rate_limited(request.user.pk):
        return JsonResponse({'error': 'Trop de messages en peu de temps. Réessayez dans quelques minutes.'}, status=429)

    body = json.dumps({
        'model': settings.AZURE_OPENAI_DEPLOYMENT,
        'messages': [{'role': 'system', 'content': _system_prompt(request)}] + history,
        'max_completion_tokens': 2000,
        'reasoning_effort': 'low',
    }).encode('utf-8')
    api_request = urllib.request.Request(
        settings.AZURE_OPENAI_ENDPOINT.rstrip('/') + '/openai/v1/chat/completions',
        data=body,
        headers={'api-key': settings.AZURE_OPENAI_API_KEY, 'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(api_request, timeout=60) as response:
            data = json.load(response)
        reply = (data['choices'][0]['message'].get('content') or '').strip()
    except urllib.error.HTTPError as exc:
        logger.error("Assistant Azure OpenAI : HTTP %s %s", exc.code, exc.read()[:500])
        reply = ''
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError):
        logger.exception("Assistant Azure OpenAI indisponible")
        reply = ''

    if not reply:
        return JsonResponse({'error': "L'assistant est momentanément indisponible. Réessayez dans un instant."}, status=502)
    return JsonResponse({'reply': reply})
