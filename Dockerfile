FROM python:3.12
# Устанавливаем рабочую директорию для проекта в контейнере
WORKDIR /backend
# Скачиваем/обновляем необходимые библиотеки для проекта
RUN git clone git@github.com:FairWindCo/creatio_integration.git
RUN pip3 install --upgrade pip -r requirements.txt
# |ВАЖНЫЙ МОМЕНТ| копируем содержимое папки, где находится Dockerfile,
# в рабочую директорию контейнера
# Устанавливаем порт, который будет использоваться для сервера
EXPOSE 5000
CMD [ "python3", "-m" , "sync_service", "run", "--host=0.0.0.0"]