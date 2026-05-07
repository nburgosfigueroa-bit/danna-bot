FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    "python-telegram-bot==20.7" \
    "supabase==2.4.0" \
    "google-generativeai==0.7.2" \
    "python-dotenv==1.0.0"
COPY . .
CMD ["python", "bot.py"]
