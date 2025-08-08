import json
from pathlib import Path
import math
from decouple import config

from django.core.files import File
from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.conf import settings

from core.services.design_by_openai import DesignByOpenAI
from core.services.mercado_pago import get_mercado_pago_service

from core.forms import ImageUploadForm
from core.models import CreditTransaction, Profile, UploadedImage, Book
from core.services import local_converter

import stripe


def landing(request: HttpRequest):
    return render(request, "core/landing.html")


def custom_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    return redirect("login")


@login_required
def home(request: HttpRequest):
    books = Book.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "core/home.html", {"books": books})


@login_required
def book_detail(request: HttpRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver este livro.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver este livro.",
        )
        return redirect("home")

    uploaded_images = book.uploaded_images.all().order_by("-created_at")
    return render(
        request,
        "core/book_detail.html",
        {"book": book, "uploaded_images": uploaded_images},
    )


@login_required
def book_create(request: HttpRequest):
    if request.method == "POST":
        title = request.POST.get("title", "Untitled Book")
        description = request.POST.get("description", "")
        book = Book.objects.create(
            title=title,
            description=description,
            author=request.user,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Livro '{book.title}' criado com sucesso.",
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "Você pode começar a adicionar páginas a este livro.",
        )
        return redirect("book_detail", book_id=book.id)
    else:
        return redirect("home")


@login_required
def upload_image(request: HttpRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver este livro.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver este livro.",
        )
        return redirect("home")

    if request.method == "POST":
        image_file = request.FILES["image"]
        uploaded_image = UploadedImage.objects.create(
            title=request.POST.get("title", "Untitled"),
            image=image_file,
            profile=request.user,
            book=book,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Página mágica carregada com sucesso, hora da diversão! 🎉",
        )
        return redirect("show_uploaded_image", image_id=uploaded_image.id)
    else:
        form = ImageUploadForm()
    return render(request, "core/upload.html", {"form": form})


@login_required
def show_uploaded_image(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    return render(request, "core/show_image.html", {"uploaded_image": uploaded_image})


@login_required
def remove_uploaded_image(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    based_on = uploaded_image.based_on
    if based_on:
        book_id = based_on.book.id  # type: ignore
    else:
        book_id = uploaded_image.book.id  # type: ignore
    uploaded_image.delete()

    if based_on is not None:
        redirect_url = reverse("show_uploaded_image", kwargs={"image_id": based_on.id})
        return redirect(redirect_url)

    redirect_url = reverse("book_detail", kwargs={"book_id": book_id})
    return redirect(redirect_url)


@login_required
def simple_convert(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui créditos suficientes para executar essa ação, compre alguns créditos.",
        )
        return redirect("show_uploaded_image", image_id=image_id)

    detail_level = int(request.POST.get("detail_level", 21))
    converted_image_path = local_converter.converter(
        filename=uploaded_image.image.name,
        image_path=uploaded_image.image.path,
        detail_level=detail_level,
    )

    converted_image_file = File(open(converted_image_path, "rb"))

    UploadedImage.objects.create(
        title=f"Converted {uploaded_image.title}",
        image=converted_image_file,
        profile=request.user,
        based_on=uploaded_image,
    )

    Path(converted_image_path).unlink()

    messages.add_message(
        request,
        messages.SUCCESS,
        f"Arte convertida com sucesso! 🎨✨ Você pode ver a nova imagem abaixo.",
    )

    use_credit_amount(user, 1)  # type: ignore

    return redirect("show_uploaded_image", image_id=uploaded_image.id)


@login_required
def generate_by_ai(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui permissão para ver esta imagem.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "Você não possui créditos suficientes para executar essa ação, compre alguns créditos.",
        )
        return redirect("show_uploaded_image", image_id=image_id)

    designer = DesignByOpenAI(image_path=uploaded_image.image.path)
    converted_image_path, _ = designer.generate()
    converted_image_file = File(open(converted_image_path, "rb"))

    UploadedImage.objects.create(
        title=f"IA {uploaded_image.title}",
        image=converted_image_file,
        profile=request.user,
        based_on=uploaded_image,
    )

    Path(converted_image_path).unlink()

    messages.add_message(
        request,
        messages.SUCCESS,
        f"Arte convertida com sucesso! 🎨✨ Você pode ver a nova imagem abaixo.",
    )

    use_credit_amount(user, 3, "AI_GENERATION")  # type: ignore

    return redirect("show_uploaded_image", image_id=uploaded_image.id)


def use_credit_amount(profile: Profile, amount: int, origin: str = "LOCAL"):
    profile.credit_amount -= amount
    if profile.credit_amount < 0:
        profile.credit_amount = 0
    profile.save()

    CreditTransaction.objects.create(
        profile=profile,
        amount=-amount,
        transaction_type=f"CREDIT_USE_{origin}",
    )
    return True


@csrf_exempt
def webhook(request: HttpRequest):
    print("Webhook received POST:", request.body)
    print("Webhook received GET:", request.GET)

    if request.method == "POST":
        return HttpResponse(status=200)
    else:
        print("Webhook received GET:", request.GET)
        return HttpResponse(status=200)


# ==========================================
# MERCADO PAGO VIEWS
# ==========================================


@login_required
@require_http_methods(["POST"])
def create_payment_preference(request: HttpRequest):
    profile = request.user
    try:
        data = json.loads(request.body)
        credit_amount = data.get("credit_amount")

        if not credit_amount or credit_amount < 5:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Quantidade de créditos deve ser maior ou igual a 5 (cinco)",
                },
                status=400,
            )

        unit_price = config("UNIT_PRICE", default="0.75", cast=float)
        description = f"Compra de {credit_amount} créditos por { profile } - MyDraws"

        if credit_amount >= 120:
            unit_price = unit_price * 0.9
            unit_price = math.floor(unit_price * 100) / 100

        if credit_amount >= 300:
            unit_price = unit_price * 0.8
            unit_price = math.floor(unit_price * 100) / 100

        mp_service = get_mercado_pago_service()
        preference = mp_service.create_payment_preference(
            profile=request.user,
            credit_amount=credit_amount,
            unit_price=unit_price,
            description=description,
        )

        if preference:
            return JsonResponse(
                {
                    "success": True,
                    "preference_id": preference["id"],
                    "init_point": preference["init_point"],
                    "sandbox_init_point": preference.get("sandbox_init_point"),
                    "total_amount": float(unit_price * credit_amount),
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Erro interno ao criar preferência de pagamento",
                },
                status=500,
            )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Erro inesperado: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def mercado_pago_webhook(request: HttpRequest):
    try:

        print(f"Webhook Mercado Pago - Body: {request.body}")
        print(f"Webhook Mercado Pago - Headers: {dict(request.headers)}")

        data = json.loads(request.body)

        action = data.get("topic")
        api_version = data.get("api_version")
        payment_id = data.get("resource")

        print(
            f"Webhook - Action: {action}, API Version: {api_version}, Payment ID: {payment_id}"
        )

        if action == "payment" and payment_id:
            mp_service = get_mercado_pago_service()
            success, message = mp_service.process_payment_notification(str(payment_id))

            print(
                f"Webhook - Processamento: {'Sucesso' if success else 'Falha'} - {message}"
            )

            return JsonResponse(
                {"success": success, "message": message, "payment_id": payment_id}
            )
        else:

            print(f"Webhook - Notificação ignorada: {action}")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Notificação recebida, mas não processada",
                    "action": action,
                }
            )

    except json.JSONDecodeError:
        print("Webhook - Erro: JSON inválido")
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)
    except Exception as e:
        print(f"Webhook - Erro inesperado: {str(e)}")
        return JsonResponse(
            {"success": False, "error": f"Erro interno: {str(e)}"}, status=500
        )


@login_required
def payment_success(request: HttpRequest):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")
    external_reference = request.GET.get("external_reference")

    context = {
        "payment_id": payment_id,
        "status": status,
        "external_reference": external_reference,
        "user_credits": request.user.credit_amount,
    }

    if status == "approved":
        mp_service = get_mercado_pago_service()
        success, message = mp_service.process_payment_notification(str(payment_id))

        print(
            f"Webhook - Processamento: {'Sucesso' if success else 'Falha'} - {message}"
        )

        messages.success(
            request, "Pagamento aprovado! Seus créditos foram adicionados à sua conta."
        )
    elif status == "pending":
        messages.info(request, "Pagamento pendente. Aguarde a confirmação.")
    else:
        messages.warning(request, "Status do pagamento: " + (status or "desconhecido"))

    return render(request, "core/payment_success.html", context)


@login_required
def payment_failure(request: HttpRequest):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")

    context = {"payment_id": payment_id, "status": status}

    messages.error(
        request,
        "Pagamento não foi concluído. Tente novamente ou entre em contato conosco.",
    )

    return render(request, "core/payment_failure.html", context)


@login_required
def payment_pending(request: HttpRequest):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")

    context = {"payment_id": payment_id, "status": status}

    messages.info(
        request, "Pagamento em processamento. Você receberá uma confirmação em breve."
    )

    return render(request, "core/payment_pending.html", context)


@login_required
def check_payment_status(request: HttpRequest, payment_id: str):
    """
    API para consultar status de um pagamento específico
    """
    try:
        mp_service = get_mercado_pago_service()
        payment_data = mp_service.get_payment_status(payment_id)

        if payment_data:
            return JsonResponse(
                {
                    "success": True,
                    "payment": {
                        "id": payment_data.get("id"),
                        "status": payment_data.get("status"),
                        "status_detail": payment_data.get("status_detail"),
                        "transaction_amount": payment_data.get("transaction_amount"),
                        "payment_method_id": payment_data.get("payment_method_id"),
                        "date_created": payment_data.get("date_created"),
                        "date_approved": payment_data.get("date_approved"),
                        "external_reference": payment_data.get("external_reference"),
                    },
                }
            )
        else:
            return JsonResponse(
                {"success": False, "error": "Pagamento não encontrado"}, status=404
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Erro ao consultar pagamento: {str(e)}"},
            status=500,
        )


@login_required
def get_available_payment_methods(request: HttpRequest):
    """
    API para consultar métodos de pagamento disponíveis
    """
    try:
        mp_service = get_mercado_pago_service()
        methods = mp_service.get_available_payment_methods()

        if methods:
            return JsonResponse({"success": True, "payment_methods": methods})
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Não foi possível consultar métodos de pagamento",
                },
                status=500,
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Erro ao consultar métodos: {str(e)}"},
            status=500,
        )


@login_required
def buy_credits(request: HttpRequest):
    unit_price = config("UNIT_PRICE", default="0.75", cast=float)
    unit_price_str = config("UNIT_PRICE")
    medium_price = unit_price * 0.9
    premium_price = unit_price * 0.8
    return render(
        request,
        "core/buy_credits.html",
        {
            "unit_price": unit_price,
            "medium_price": medium_price,
            "premium_price": premium_price,
            "unit_price_str": unit_price_str,
        },
    )


# ==========================================
# STRIPE VIEWS
# ==========================================


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def stripe_create_checkout_session(request: HttpRequest):
    profile = request.user
    data = json.loads(request.body)
    selected_pack = data.get("pack_id")

    packages = settings.CREDIT_PACKAGES

    if selected_pack not in [pkg["id"] for pkg in packages]:
        return JsonResponse(
            {"success": False, "error": "invalid package selected"},
            status=400,
        )

    for pack in packages:
        if pack["id"] == selected_pack:
            selected_pack = pack
            break

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(selected_pack["amount"]),  # Preço em centavos
                    "product_data": {
                        "name": f"{selected_pack['label']}",
                    },
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("stripe_webhook")),
        cancel_url=request.build_absolute_uri(reverse("buy_stripe_credits")),
        currency="usd",
        customer_email=profile.email if profile.email else None,  # type: ignore
        metadata={
            "user_id": str(profile.id),  # type: ignore
            "pack_id": str(selected_pack["id"]),
        },
    )

    return JsonResponse(
        {
            "success": True,
            "sessionId": session.id,
        },
    )


@csrf_exempt
# @require_http_methods(["GET", "POST"])
def stripe_webhook(request: HttpRequest):
    payload = request.body

    if payload == b"":
        return redirect("buy_stripe_credits")

    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret,
        )
    except ValueError as e:
        print(f"Error parsing webhook payload: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except stripe.error.SignatureVerificationError as e:  # type: ignore
        print(f"Error verifying webhook signature: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        pack_id = session.get("metadata", {}).get("pack_id")

        if user_id and pack_id:
            profile = Profile.objects.get(id=user_id)
            pack = next(
                (pkg for pkg in settings.CREDIT_PACKAGES if pkg["id"] == pack_id),
                None,
            )

            if pack:
                profile.credit_amount += pack["credits"]
                profile.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Credit purchase successful!",
                )

    return JsonResponse(
        {"status": "success"},
        status=200,
    )


@login_required
def buy_stripe_credits(request: HttpRequest):
    packages = settings.CREDIT_PACKAGES
    publishable_key = settings.STRIPE_PUBLISHABLE_KEY

    packages = list(
        map(
            lambda pkg: {
                **pkg,
                "amount": int(pkg["amount"]) / 100,
            },
            packages,
        )
    )

    return render(
        request,
        "core/buy_stripe_credits.html",
        {
            "packages": packages,
            "publishable_key": publishable_key,
        },
    )
