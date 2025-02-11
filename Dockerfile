FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей для tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    liblcms2-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libtiff-dev \
    libwebp-dev \
    > /app/docker_build.log 2>&1

# Копирование виртуального окружения
COPY myenv /myenv

# Создаем директорию, если она не существует, и копируем исполнимый файл Python
RUN mkdir -p /myenv/Scripts && cp /usr/local/bin/python /myenv/Scripts/python \
    >> /app/docker_build.log 2>&1

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="/myenv/Scripts:$PATH"
ENV PATH="/myenv/bin:$PATH"

# Устанавливаем pip в виртуальное окружение
RUN curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    /myenv/Scripts/python get-pip.py >> /app/docker_build.log 2>&1 && \
    rm get-pip.py

# Проверяем, что используется Python из виртуального окружения
RUN echo "=== Проверка доступных исполнимых файлов ===" >> /app/docker_build.log && \
    ls -l /usr/local/bin/ >> /app/docker_build.log && \
    echo "=== Проверка директории виртуального окружения ===" >> /app/docker_build.log && \
    ls -l /myenv/Scripts/ >> /app/docker_build.log && \
    echo "=== Проверка используемого Python ===" >> /app/docker_build.log && \
    which python >> /app/docker_build.log && \
    python --version >> /app/docker_build.log && \
    echo "=== Список установленных пакетов ===" >> /app/docker_build.log && \
    python -m pip list >> /app/docker_build.log

# Копируем остальные файлы проекта
COPY . .

# Определяем директорию site-packages и копируем пакеты
RUN SITE_PATH=$(python -c "import site; import sys; print(site.getsitepackages()[0])") && \
    echo "Site Packages Path: $SITE_PATH" >> /app/docker_build.log && \
    cp -r /myenv/Lib/site-packages/* $SITE_PATH/ >> /app/docker_build.log

# Логирование завершения сборки
RUN echo "Сборка завершена." >> /app/docker_build.log

# Команда для запуска приложения с логированием
CMD ["/bin/sh", "-c", "/myenv/Scripts/python main.py 2>&1 | tee -a /app/app.log"]
