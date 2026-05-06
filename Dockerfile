FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "python-telegram-bot==20.7" \
    "httpx==0.25.2" \
    "gotrue==1.3.0" \
    "supabase==2.4.0" \
    "python-dotenv==1.0.0"
COPY . .
CMD ["python", "bot.py"]
