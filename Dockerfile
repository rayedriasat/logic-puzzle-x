# Container for the LogicPuzzleX web app (API + UI on one port).
# Used by the Hugging Face Space (see deploy/huggingface/README.md); also runs anywhere Docker does:
#   docker build -t logicpuzzlex . && docker run -p 7860:7860 logicpuzzlex
FROM python:3.12-slim

# Hugging Face runs Docker Spaces as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user main.py .
COPY --chown=user support ./support
COPY --chown=user data ./data

EXPOSE 7860
CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "7860", "--no-browser"]
