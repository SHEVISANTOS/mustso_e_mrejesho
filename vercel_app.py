import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

# Set the default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'must_mrejesho.settings')

# Get the Django WSGI application
application = get_wsgi_application()

# Wrap it with WhiteNoise to serve static files
# Note: 'staticfiles' is the folder where collectstatic puts files
application = WhiteNoise(application, root=os.path.join(os.path.dirname(__file__), 'staticfiles'))

app = application