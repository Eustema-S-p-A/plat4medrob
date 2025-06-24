FROM python:3.9
    
# Imposta una directory di lavoro all'interno del container
WORKDIR /app/app

# Copia il file Pipfile e Pipfile.lock nella directory di lavoro
COPY Pipfile ./

# Installa pipenv e le dipendenze dal Pipfile
RUN pip install pipenv

RUN pipenv lock && pipenv install --system

# Copia il resto del codice sorgente dell'applicazione nella directory di lavoro
COPY . .

# Specifica la porta su cui il container sarà in ascolto
EXPOSE 17000


CMD ["uvicorn", "app.main:app", "--host", "localhost", "--port", "8000"]