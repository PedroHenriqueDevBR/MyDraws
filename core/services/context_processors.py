def user_credit_amount(request):
    if request.user.is_authenticated:
        credit_amount = request.user.credit_amount
    else:
        credit_amount = None
    return {"credit_amount": credit_amount}
