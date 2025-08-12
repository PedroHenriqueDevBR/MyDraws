from core.models import Profile, CreditTransaction


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
