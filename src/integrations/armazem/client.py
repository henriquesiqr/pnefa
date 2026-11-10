import os

import requests
from dotenv import load_dotenv

from src.data_io import read_text_file


# =========================
# PARÂMETROS AJUSTÁVEIS
# =========================
REQUEST_TIMEOUT_SECONDS = 120


load_dotenv()


class ArmazemClient:
    def __init__(self):
        self.host = os.getenv("ARMAZEM_HOST")
        self.api_key = os.getenv("ARMAZEM_API_KEY")

        if not self.host:
            raise ValueError("ARMAZEM_HOST não definido no .env")

        if not self.api_key:
            raise ValueError("ARMAZEM_API_KEY não definido no .env")

    def execute_query(self, query: str) -> dict:
        try:
            response = requests.get(
                self.host,
                params={
                    "api_key": self.api_key,
                    "query": query,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        except requests.exceptions.ReadTimeout as exc:
            raise TimeoutError(
                f"A consulta ao Armazém excedeu "
                f"{REQUEST_TIMEOUT_SECONDS}s."
            ) from exc

        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            raise ValueError(
                f"Erro GraphQL retornado pela API: {data['errors']}"
            )

        return data

    def execute_query_file(self, query_path: str) -> dict:
        query = read_text_file(query_path)

        return self.execute_query(query)