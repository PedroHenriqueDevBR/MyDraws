import json

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Profile
from core.types import CustomRequest


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
