FROM python:3.12-slim

# Create a secure non-root user
RUN useradd --create-home appuser

WORKDIR /app

# Leverage layer cache by installing dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Explicitly export the module namespace path
ENV PYTHONPATH=/app
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]




