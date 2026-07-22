import os
from django.core.wsgi import get_wsgi_application

# This MUST match your inner folder name: must_mrejesho
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'must_mrejesho.settings')

# Vercel looks for 'app' or 'application'
app = get_wsgi_application()