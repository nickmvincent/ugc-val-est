def tmp():
    from portal.models import Revision
    qs = Revision.objects.all().order_by('?')[:50]
    for rev in qs:
        print(qs.user)
        print(qs.registration)
