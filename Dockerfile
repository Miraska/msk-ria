FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Устанавливаем зависимости для Tesseract (например, на базе Ubuntu)
RUN apt-get update && \
    apt-get install -y tesseract-ocr && \
    apt-get clean

# Копирование виртуального окружения
COPY myenv /myenv

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="/myenv/bin:$PATH"

# Проверяем наличие Python в виртуальном окружении
RUN ls -l /myenv/bin/

# Устанавливаем pip в виртуальное окружение, используя правильный путь
RUN /myenv/bin/python -m ensurepip --upgrade

# Проверяем, что используется Python из виртуального окружения
RUN echo "Проверка доступных исполнимых файлов:" && \
    ls -l /usr/local/bin/ && \
    echo "Проверка директории виртуального окружения:" && \
    ls -l /myenv/bin/ && \
    echo "Проверка используемого Python:" && \
    which python && python --version && \
    echo "Список установленных пакетов:" && \
    /myenv/bin/python -m pip list

# Копируем остальные файлы проекта
COPY . .

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["/myenv/bin/python", "main.py"]
