def user_role(request):
    """إضافة دور المستخدم إلى سياق القالب"""
    role = 'anonymous'
    if request.user.is_authenticated:
        role = request.user.profile.role

    return {
        'user_role': role
    }