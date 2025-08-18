import json
import math
from pathlib import Path

import stripe
from celery.result import AsyncResult
from decouple import config
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.forms import ImageUploadForm
from core.models import Book, Profile, UploadedImage
from core.services import local_converter
from core.services.mercado_pago import get_mercado_pago_service
from core.tasks import generate_ai_image_task
from core.types import CustomRequest
from core.utils import use_credit_amount


# Endpoint para polling do status da task Celery
def check_ai_task_status(request: CustomRequest, image_id: int):
    task_id = request.session.get(f"ai_task_{image_id}")
    if not task_id:
        return JsonResponse({"status": "not_found"})

    result = AsyncResult(task_id)

    print(result.state)  # Debugging line to check task state

    if result.state == "SUCCESS":
        request.session.pop(f"ai_task_{image_id}", None)
        return JsonResponse({"status": "done", "image_path": result.result})
    elif result.state == "FAILURE":
        request.session.pop(f"ai_task_{image_id}", None)
        return JsonResponse({"status": "error"})
    else:
        return JsonResponse({"status": "pending"})


def landing(request: CustomRequest):
    return render(request, "core/landing.html")


def custom_logout(request: CustomRequest):
    logout(request)
    request.session.flush()
    return redirect("login")


@login_required
def home(request: CustomRequest):
    books = Book.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "core/home.html", {"books": books})


@login_required
def book_detail(request: CustomRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    uploaded_images = book.uploaded_images.all().order_by("-id")  # type: ignore
    return render(
        request,
        "core/book_detail.html",
        {"book": book, "uploaded_images": uploaded_images},
    )


@login_required
def book_create(request: CustomRequest):
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
            f"Book '{book.title}' created successfully.",
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "You can start adding pages to this book.",
        )
        return redirect("book_detail", book_id=book.id)  # type: ignore
    else:
        return redirect("home")


@login_required
def upload_image(request: CustomRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
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
            "Magic page uploaded successfully, time for fun! 🎉",
        )
        return redirect("show_uploaded_image", image_id=uploaded_image.id)  # type: ignore
    else:
        form = ImageUploadForm()
    return render(request, "core/upload.html", {"form": form})


@login_required
def show_uploaded_image(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    has_imagem_task = request.session.get(f"ai_task_{image_id}") is not None

    return render(
        request,
        "core/show_image.html",
        {
            "uploaded_image": uploaded_image,
            "has_imagem_task": has_imagem_task,
        },
    )


@login_required
def remove_uploaded_image(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
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
def simple_convert(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have enough credits to perform this action, please buy some credits.",
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
        "Art converted successfully! 🎨✨ You can see the new image below.",
    )

    use_credit_amount(user, 1)  # type: ignore

    return redirect(
        "show_uploaded_image",
        image_id=uploaded_image.id,  # type: ignore
    )


@login_required
def generate_by_ai(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image or uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have enough credits to perform this action, please buy some credits.",
        )
        return redirect("show_uploaded_image", image_id=image_id)

    # Celery task
    task = generate_ai_image_task.delay(uploaded_image.id)  # type: ignore
    request.session[f"ai_task_{image_id}"] = task.id

    messages.add_message(
        request,
        messages.INFO,
        "AI art generation has been started! You will be notified when it's ready.",
    )

    return redirect("show_uploaded_image", image_id=uploaded_image.id)  # type: ignore


@csrf_exempt
def webhook(request: CustomRequest):
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
def create_payment_preference(request: CustomRequest):
    profile = request.user
    try:
        data = json.loads(request.body)
        credit_amount = data.get("credit_amount")

        if not credit_amount or credit_amount < 5:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Credit amount must be greater than or equal to 5 (five)",
                },
                status=400,
            )

        unit_price = config("UNIT_PRICE", default="0.75", cast=float)
        description = f"Purchase of {credit_amount} credits by { profile } - MyDraws"

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
            unit_price=unit_price,  # type: ignore
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
                    "error": "Internal error creating payment preference",
                },
                status=500,
            )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Unexpected error: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def mercado_pago_webhook(request: CustomRequest):
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
                f"Webhook - Processing: {'Success' if success else 'Failure'} - {message}"
            )

            return JsonResponse(
                {"success": success, "message": message, "payment_id": payment_id}
            )
        else:

            print(f"Webhook - Notification ignored: {action}")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Notification received, but not processed",
                    "action": action,
                }
            )

    except json.JSONDecodeError:
        print("Webhook - Error: Invalid JSON")
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        print(f"Webhook - Unexpected error: {str(e)}")
        return JsonResponse(
            {"success": False, "error": f"Internal error: {str(e)}"}, status=500
        )


@login_required
def payment_success(request: CustomRequest):
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
            f"Webhook - Processing: {'Success' if success else 'Failure'} - {message}"
        )

        messages.success(
            request, "Payment approved! Your credits have been added to your account."
        )
    elif status == "pending":
        messages.info(request, "Payment pending. Please wait for confirmation.")
    else:
        messages.warning(request, "Payment status: " + (status or "unknown"))

    return render(request, "core/payment_success.html", context)


@login_required
def payment_failure(request: CustomRequest):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")

    context = {"payment_id": payment_id, "status": status}

    messages.error(
        request,
        "Payment was not completed. Please try again or contact us.",
    )

    return render(request, "core/payment_failure.html", context)


@login_required
def payment_pending(request: CustomRequest):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")

    context = {"payment_id": payment_id, "status": status}

    messages.info(
        request, "Payment is being processed. You will receive confirmation shortly."
    )

    return render(request, "core/payment_pending.html", context)


@login_required
def check_payment_status(request: CustomRequest, payment_id: str):
    """
    API to check status of a specific payment
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
                {"success": False, "error": "Payment not found"}, status=404
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error checking payment: {str(e)}"},
            status=500,
        )


@login_required
def get_available_payment_methods(request: CustomRequest):
    """
    API to check available payment methods
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
                    "error": "Could not check payment methods",
                },
                status=500,
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error checking methods: {str(e)}"},
            status=500,
        )


@login_required
def buy_credits(request: CustomRequest):
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
def stripe_create_checkout_session(request: CustomRequest):
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
                    "unit_amount": int(selected_pack["amount"]),  # Price in cents
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
def stripe_webhook(request: CustomRequest):
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
def buy_stripe_credits(request: CustomRequest):
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
