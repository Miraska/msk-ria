FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

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
    /myenv/Scripts/python get-pip.py && \
    rm get-pip.py

# Проверяем, что используется Python из виртуального окружения
RUN echo "Проверка доступных исполнимых файлов:" && \
    ls -l /usr/local/bin/ && \
    echo "Проверка директории виртуального окружения:" && \
    ls -l /myenv/Scripts/ && \
    echo "Проверка используемого Python:" && \
    which python && python --version && \
    echo "Список установленных пакетов:" && \
    python -m pip list

# Копируем остальные файлы проекта
COPY . .

# Определяем директорию для установки пакетов
RUN python -c "import site; print(site.getsitepackages())" > /tmp/python_site.txt

# Добавляем вывод в файл, чтобы проверить путь
RUN cat /tmp/python_site.txt

# Перемещаем ваши библиотеки в нужную директорию
RUN cp -r /myenv/Lib/site-packages/* $(cat /tmp/python_site.txt | tr -d '\n')/site-packages/

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["/myenv/Scripts/python", "main.py"]
