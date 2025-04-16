from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('instructions/', views.InstructionsView.as_view(), name='instructions'),
    # Add other core URLs here as needed
]