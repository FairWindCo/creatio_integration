FROM python:3.12-alpine
# Устанавливаем рабочую директорию для проекта в контейнере
# Скачиваем/обновляем необходимые библиотеки для проекта
ENV TZ=Europe/Kyiv
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apk add build-base openldap-dev python3-dev git unixodbc-dev

RUN git clone https://github.com/FairWindCo/creatio_integration
WORKDIR /creatio_integration
RUN pip3 install --upgrade pip -r requirements.txt
RUN pip3 install gunicorn
# |ВАЖНЫЙ МОМЕНТ| копируем содержимое папки, где находится Dockerfile,
# в рабочую директорию контейнера
# Устанавливаем порт, который будет использоваться для сервера
EXPOSE 5000
# CMD [ "python3", "-m" , "flask", "--app", "sync_service" ,"run", "--host=0.0.0.0"]
CMD ["gunicorn", "sync_service:app", "-b", "0.0.0.0:5000", "-w", "4"]