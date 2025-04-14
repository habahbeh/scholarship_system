from django.http import JsonResponse
from .models import Department

def get_departments(request):
    """جلب الأقسام بناءً على الكلية المحددة"""
    faculty_id = request.GET.get('faculty_id')
    departments = Department.objects.filter(faculty_id=faculty_id).values('id', 'name')
    return JsonResponse(list(departments), safe=False)