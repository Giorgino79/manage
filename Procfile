web: gunicorn management.wsgi --log-file - --settings=management.settings_heroku
release: python manage.py migrate --noinput --settings=management.settings_heroku
