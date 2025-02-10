FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Копируем исполнимый файл Python из официального образа в директорию /myenv/bin/
RUN cp /usr/local/bin/python /myenv/bin/python

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"  # Для Linux

# Проверяем, что используется Python из виртуального окружения
RUN echo "Проверка используемого Python:" && \
    which python && python --version && \
    echo "Список установленных пакетов:" && \
    python -m pip list

# Копируем остальные файлы проекта
COPY . .

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["/myenv/bin/python", "main.py"]  # Для Linux
