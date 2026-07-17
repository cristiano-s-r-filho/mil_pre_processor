#!/usr/bin/env python3
"""MIL Phase5 - Renomeacao de arquivos para patching."""

import argparse
import logging

from mil.config import load_config, get
from mil.phase5_renamer import process_alelo


def main() -> None:
    load_config()

    parser = argparse.ArgumentParser(
        description="MIL Phase5 - Renomeacao de arquivos para patching"
    )
    parser.add_argument(
        "--alelo",
        choices=get("alelos_validos") + ["all"],
        default="all",
        help="Pasta de alelos a processar (default: all)",
    )
    parser.add_argument(
        "--input",
        default=get("paths.dados_para_patching_root"),
        help="Raiz de entrada (dados_para_patching)",
    )
    parser.add_argument(
        "--output",
        default="dados_renamed",
        help="Raiz de saida (default: dados_renamed)",
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
        logger.info("Renomeando alelo: %s", alelo)
        logger.info("=" * 50)

        sd_count, nd_count, skipped = process_alelo(
            input_root=args.input,
            output_root=args.output,
            alelo=alelo,
        )

        logger.info(
            "\nRelatorio %s:\n"
            "  SD renomeados: %d\n"
            "  ND renomeados: %d\n"
            "  Pulados: %d\n"
            "  Total: %d",
            alelo,
            sd_count,
            nd_count,
            skipped,
            sd_count + nd_count,
        )


if __name__ == "__main__":
    main()
