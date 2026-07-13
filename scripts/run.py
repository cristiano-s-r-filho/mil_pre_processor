#!/usr/bin/env python3
import argparse
import logging
import os

from mil.config import load_config, get
from mil.pipeline import process_alelo
from mil.run_logger import create_run, finish_run, next_run_id, print_report


def main() -> None:
    load_config()

    parser = argparse.ArgumentParser(
        description="MIL Pipeline - triagem e classificacao de laminas renais"
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
        help="Raiz do dataset de entrada",
    )
    parser.add_argument(
        "--output",
        default=get("paths.dados_processados_root"),
        help="Raiz da saida processada",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log verbose (DEBUG)",
    )
    parser.add_argument(
        "--phase4",
        action="store_true",
        help="Executar fase 4 (cropping para dados_para_patching)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Mostrar relatorio de execucoes anteriores e sair",
    )

    args = parser.parse_args()

    if args.report:
        from mil.run_logger import list_runs

        runs = list_runs(args.output)
        if not runs:
            print("Nenhuma execucao anterior encontrada.")
        else:
            print(f"\nHistorico de execucoes ({len(runs)}):\n")
            for r in runs:
                print(
                    f"  {r['run_id']:30s}  "
                    f"{r['alelo']:8s}  "
                    f"{r['ok']:3d}/{r['total']:3d} OK  "
                    f"{r['errors']:3d} erros  "
                    f"{r['cortados']:3d} cortados"
                )
        return

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    alelos = get("alelos_validos") if args.alelo == "all" else [args.alelo]

    if args.phase4:
        from mil.phase4_cropper import run as run_phase4

        dados_proc = args.output
        dados_patch = os.path.join(os.path.dirname(args.output), get("paths.dados_para_patching_root"))
        run_phase4(
            dados_processados_root=dados_proc,
            output_root=dados_patch,
            alelos=alelos,
        )
        return

    for alelo in alelos:
        run_id = next_run_id(alelo)
        run = create_run(run_id, alelo, args.output)
        process_alelo(
            dataset_root=args.dataset,
            output_root=args.output,
            alelo=alelo,
            run=run,
        )
        log_path = finish_run(run, args.output)
        print_report(run)
        print(f"Log salvo em: {log_path}\n")


if __name__ == "__main__":
    main()
