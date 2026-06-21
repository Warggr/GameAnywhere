FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt update && apt install -y npm && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action ignore -r requirements.txt

COPY . .
RUN pip install --no-cache-dir --root-user-action ignore '.[examples]'

FROM python:3.12-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

EXPOSE 8000

ENV PORT=8000

CMD sh -c "python -m game_anywhere.run_server -p ${PORT}"
