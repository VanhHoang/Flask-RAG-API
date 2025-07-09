FROM vanhhoang102/py39_flask_ai

WORKDIR /app

COPY . .

CMD ["python", "backend.py"]