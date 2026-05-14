FROM python:3.13-slim

WORKDIR /srv/app

COPY progrec_service/requirements.txt /tmp/progrec_service_requirements.txt
RUN pip install --no-cache-dir -r /tmp/progrec_service_requirements.txt

COPY . /srv/app

CMD ["/bin/sh", "-lc", "python deployment/scripts/migrate.py && python -m uvicorn progrec_service.app:create_app --factory --host 0.0.0.0 --port 8000"]
