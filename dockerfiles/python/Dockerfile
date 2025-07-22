FROM python:3.13

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOME=/code

RUN mkdir $HOME
WORKDIR $HOME
RUN apt update && apt upgrade -y
RUN apt install -y libgl1
RUN pip install -U pip setuptools

COPY requirements.txt $HOME
RUN pip install -r requirements.txt
ADD . $HOME

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
EXPOSE 8000
