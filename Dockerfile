FROM python:3.12-alpine
# Устанавливаем рабочую директорию для проекта в контейнере
# Скачиваем/обновляем необходимые библиотеки для проекта
ENV TZ=Europe/Kyiv
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apk add build-base openldap-dev python3-dev git curl gnupg ;  \
    curl -O https://download.microsoft.com/download/7/6/d/76de322a-d860-4894-9945-f0cc5d6a45f8/msodbcsql18_18.4.1.1-1_amd64.apk ;\
    curl -O https://download.microsoft.com/download/7/6/d/76de322a-d860-4894-9945-f0cc5d6a45f8/msodbcsql18_18.4.1.1-1_amd64.sig ;\
    curl https://packages.microsoft.com/keys/microsoft.asc  | gpg --import - ; \
    gpg --verify msodbcsql18_18.4.1.1-1_amd64.sig msodbcsql18_18.4.1.1-1_amd64.apk ; \
    apk add --allow-untrusted msodbcsql18_18.4.1.1-1_amd64.apk ; \
    apk add  unixodbc-dev

RUN mkdir /creatio_integration
WORKDIR /creatio_integration
COPY requirements.txt /creatio_integration/requirements.txt
RUN pip3 install --upgrade pip -r requirements.txt ; pip3 install gunicorn

RUN git clone https://github.com/FairWindCo/creatio_integration
# |ВАЖНЫЙ МОМЕНТ| копируем содержимое папки, где находится Dockerfile,
# в рабочую директорию контейнера
# Устанавливаем порт, который будет использоваться для сервера
EXPOSE 5000
# CMD [ "python3", "-m" , "flask", "--app", "sync_service" ,"run", "--host=0.0.0.0"]
CMD ["gunicorn", "sync_service:app", "-b", "0.0.0.0:5000", "-w", "2", "--timeout", "600"]