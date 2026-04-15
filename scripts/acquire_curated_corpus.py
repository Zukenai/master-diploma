from app.config.settings import get_config
from app.ingest.curated_acquisition import acquire_curated_corpus


if __name__ == "__main__":
    result = acquire_curated_corpus(get_config())
    import json

    print(json.dumps(result, indent=2, ensure_ascii=False))
