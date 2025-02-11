FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей для tesseract и SSL
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    liblcms2-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libtiff-dev \
    libwebp-dev \
    libssl-dev \
    openssl | tee /app/install_deps.log

# Копирование виртуального окружения
COPY myenv /myenv

# Создаем директорию, если она не существует, и копируем исполнимый файл Python
RUN mkdir -p /myenv/Scripts && cp /usr/local/bin/python /myenv/Scripts/python

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="/myenv/Scripts:$PATH"
ENV PATH="/myenv/bin:$PATH"

# Устанавливаем pip в виртуальное окружение
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    /myenv/Scripts/python get-pip.py | tee /app/get_pip.log && \
    rm get-pip.py

# Проверяем, что используется Python из виртуального окружения
RUN echo "Проверка доступных исполнимых файлов:" && \
    ls -l /usr/local/bin/ | tee -a /app/docker_build.log && \
    echo "Проверка директории виртуального окружения:" && \
    ls -l /myenv/Scripts/ | tee -a /app/docker_build.log && \
    echo "Проверка используемого Python:" && \
    which python | tee -a /app/docker_build.log && python --version | tee -a /app/docker_build.log && \
    echo "Список установленных пакетов:" && \
    python -m pip list | tee -a /app/docker_build.log

# Копируем остальные файлы проекта
COPY . .

# Очистка кеша перед запуском
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -delete | tee -a /app/docker_build.log

# Определяем директорию для установки пакетов и сохраняем ее в переменную
RUN SITE_PATH=$(python -c "import site; import sys; print(site.getsitepackages()[0])") && \
    echo "Site Packages Path: $SITE_PATH" | tee -a /app/docker_build.log && \
    cp -r /myenv/Lib/site-packages/* $SITE_PATH/ | tee -a /app/docker_build.log

# Логирование завершения сборки
RUN echo "Сборка завершена." | tee -a /app/docker_build.log

# Запуск приложения с выводом всех логов в stdout
CMD /myenv/Scripts/python main.py | tee /dev/stdout
