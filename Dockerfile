FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    "python-telegram-bot==20.7" \
    "httpx==0.25.2" \
    "gotrue==1.3.0" \
    "postgrest==0.10.8" \
    "realtime==1.0.2" \
    "storage3==0.5.4" \
    "supabase==2.4.0" \
    "python-dotenv==1.0.0" \
    "google-generativeai==0.7.2"
COPY . .
CMD ["python", "bot.py"]
