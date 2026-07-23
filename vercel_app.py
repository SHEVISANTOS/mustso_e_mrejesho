import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'must_mrejesho.settings')

application = get_wsgi_application()

# Explicitly point WhiteNoise to the staticfiles folder
application = WhiteNoise(
    application, 
    root=os.path.join(os.path.dirname(__file__), 'staticfiles')
)

app = application