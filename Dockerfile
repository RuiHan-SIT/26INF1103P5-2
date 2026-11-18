FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# run the same tests as CI, then throw away the db the tests made so the image starts clean
RUN python -m pytest tests/ -q && rm -f part_2/db.sqlite3

WORKDIR /app/part_2
EXPOSE 8000

# set up the db, load the demo employees, then start the server
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py load_employees && python manage.py runserver 0.0.0.0:8000"]
