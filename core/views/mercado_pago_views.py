import json
import math

from decouple import config
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.services.mercado_pago import get_mercado_pago_service
from core.types import CustomRequest


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


@csrf_exempt
def webhook(request: CustomRequest):
    print("Webhook received POST:", request.body)
    print("Webhook received GET:", request.GET)

    if request.method == "POST":
        return HttpResponse(status=200)
    else:
        print("Webhook received GET:", request.GET)
        return HttpResponse(status=200)
