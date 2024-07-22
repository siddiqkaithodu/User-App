FROM python:3.10-slim-bullseye
LABEL authors="abubakkar"
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH .
WORKDIR /code
COPY requirements.txt /code
RUN pip install -r requirements.txt
COPY . /code
CMD ["python", "-m", "uvicorn", "UserApp.run:app", "--host", "0.0.0.0"]