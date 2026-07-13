#!/usr/bin/env python3
import argparse
import logging

from mil.config import load_config, get
from mil.phase4_cropper import process_alelo


def main() -> None:
    load_config()

    parser = argparse.ArgumentParser(
        description="MIL Phase4 - Cropping de regioes para patching"
    )
    parser.add_argument(
        "--alelo",
        choices=get("alelos_validos") + ["all"],
        default="all",
        help="Pasta de alelos a processar (default: all)",
    )
    parser.add_argument(
        "--dataset",
        default=get("paths.dataset_root"),
        help="Raiz do dataset original",
    )
    parser.add_argument(
        "--processed",
        default=get("paths.dados_processados_root"),
        help="Raiz dos dados processados (fase3)",
    )
    parser.add_argument(
        "--output",
        default=get("paths.dados_para_patching_root"),
        help="Raiz de saida (dados_para_patching)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Log verbose (DEBUG)",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    alelos = get("alelos_validos") if args.alelo == "all" else [args.alelo]

    for alelo in alelos:
        logger = logging.getLogger(__name__)
        logger.info("=" * 50)
        logger.info("Processando alelo: %s", alelo)
        logger.info("=" * 50)

        stats = process_alelo(
            dados_processados_root=args.processed,
            output_root=args.output,
            alelo=alelo,
        )

        logger.info(
            "\nRelatorio %s:\n"
            "  Cortados (SD): %d\n"
            "  Copiados (ND): %d\n"
            "  Total poligonos: %d\n"
            "  Erros: %d",
            alelo,
            stats["sd_ok"],
            stats["nd_ok"],
            stats["polygons_total"],
            stats["errors"],
        )


if __name__ == "__main__":
    main()
