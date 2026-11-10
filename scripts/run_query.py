from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


from src.integrations.armazem.client import ArmazemClient
from src.data_io import QUERIES_RESULTS_DIR, save_json


def main():
    if len(sys.argv) < 2:
        raise ValueError(
            "Uso: python run_query.py <arquivo.graphql>"
        )

    query_name = sys.argv[1]

    query_path = Path(f"queries/{query_name}")

    output_path = QUERIES_RESULTS_DIR / f"{query_path.stem}.json"

    client = ArmazemClient()

    data = client.execute_query_file(query_path)

    save_json(data, output_path)

    print(f"Resultado salvo em: {output_path}")


if __name__ == "__main__":
    main()