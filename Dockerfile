FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    "python-telegram-bot==20.7" \
    "python-dotenv==1.0.0" \
    "requests==2.31.0" \
    "groq==0.9.0" \
    "openpyxl==3.1.5"
COPY . .
CMD ["python", "bot.py"]
