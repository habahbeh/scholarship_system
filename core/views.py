from django.shortcuts import render
from django.views.generic import TemplateView

# Add this new view for instructions
class InstructionsView(TemplateView):
    """View for displaying instructions and guidelines page"""
    template_name = 'instructions.html'