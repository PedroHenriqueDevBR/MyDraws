from celery.result import AsyncResult
from django.contrib.auth import logout
from django.http.response import JsonResponse
from django.shortcuts import redirect, render

from core.types import CustomRequest


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
