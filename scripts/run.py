#!/usr/bin/env python3
"""MIL Pipeline - Script principal CLI com UI/UX moderna."""

import argparse
import logging
import os

from mil.config import load_config, get
from mil.pipeline import process_alelo
from mil.report import (
    console,
    print_error_msg,
    print_header,
    print_phase_indicator,
    print_step,
    print_success,
    print_warning_msg,
    report_margin,
    report_phase4,
    report_runtime_stats,
    report_summary,
    report_extensive,
)
from mil.run_logger import create_run, finish_run, next_run_id, print_report
from mil.runtime_log import RuntimeLogger


def main() -> None:
    load_config()

    parser = argparse.ArgumentParser(
        description="MIL Pipeline - triagem e classificacao de laminas renais",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  run-proc --alelo 0alelos\n"
            "  run-proc --alelo 0alelos --extensive\n"
            "  run-proc --phase4 --alelo 0alelos\n"
            "  run-proc --phase4 --alelo 0alelos --edge-margin 50 --edge-mode outside\n"
            "  run-proc --report\n"
            "  run-proc --report --extensive\n"
            "  run-proc --runtime-logs"
        ),
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
        "--verbose", "-v",
        action="store_true",
        help="Log verbose (DEBUG)",
    )
    parser.add_argument(
        "--phase4",
        action="store_true",
        help="Executar fase 4 (cropping para dados_para_patching)",
    )
    parser.add_argument(
        "--extensive", "-e",
        action="store_true",
        help="Relatorio extenso (detalhado por arquivo)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Mostrar relatorio de execucoes anteriores e sair",
    )
    parser.add_argument(
        "--runtime-logs",
        action="store_true",
        help="Mostrar logs de runtime e sair",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Desabilitar cores na saida",
    )

    # --- Flags de margem ---
    parser.add_argument(
        "--edge-margin",
        type=int,
        default=None,
        help="Margem de borda em pixels (sobrescreve config)",
    )
    parser.add_argument(
        "--edge-mode",
        choices=["exact", "outside", "inside"],
        default=None,
        help="Modo de borda (sobrescreve config)",
    )

    args = parser.parse_args()

    if args.no_color:
        from mil.report import console as _console
        _console.no_color = True

    # --- Modo relatório ---
    if args.report:
        from mil.run_logger import list_runs

        runs = list_runs(args.output)
        if not runs:
            print_error_msg("Nenhuma execucao anterior encontrada.")
        else:
            print_header()
            print_step(f"Historico de execucoes ({len(runs)} runs)")
            for r in runs:
                if args.extensive:
                    report_extensive(r)
                else:
                    report_summary(r)
        return

    # --- Modo runtime logs ---
    if args.runtime_logs:
        from mil.runtime_log import list_runtime_logs, load_runtime_logs

        run_ids = list_runtime_logs(args.output)
        if not run_ids:
            print_error_msg("Nenhum log de runtime encontrado.")
        else:
            print_header()
            print_step(f"Logs de runtime disponíveis ({len(run_ids)})")
            for run_id in run_ids:
                console.print(f"\n[bold]Run ID: {run_id}[/bold]")
                logs = load_runtime_logs(args.output, run_id)

                # Resumo
                summary = logs.get("summary", [])
                if summary:
                    last = summary[-1]
                    if last.get("event") == "run_complete":
                        print_step("Resumo")
                        console.print(f"  Total: {last.get('total_files', 0)}")
                        console.print(f"  Processados: {last.get('processed_files', 0)}")
                        console.print(f"  Warnings: [yellow]{last.get('warnings', 0)}[/yellow]")
                        console.print(f"  Erros: [red]{last.get('errors', 0)}[/red]")
                        console.print(f"  Duração: {last.get('duration_seconds', 0):.1f}s")

                # Warnings
                warnings = logs.get("warnings", [])
                if warnings:
                    print_step(f"Warnings ({len(warnings)})")
                    for w in warnings[:10]:  # Mostrar apenas 10
                        print_warning_msg(
                            f"{w.get('filename', '?')}: {w.get('message', '?')}"
                        )
                    if len(warnings) > 10:
                        console.print(f"  ... e mais {len(warnings) - 10} warnings")

                # Erros
                errors = logs.get("errors", [])
                if errors:
                    print_step(f"Erros ({len(errors)})")
                    for e in errors[:10]:  # Mostrar apenas 10
                        print_error_msg(
                            f"{e.get('filename', '?')}: {e.get('message', '?')}"
                        )
                    if len(errors) > 10:
                        console.print(f"  ... e mais {len(errors) - 10} erros")
        return

    # --- Configuração de logging ---
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    alelos = get("alelos_validos") if args.alelo == "all" else [args.alelo]

    # --- Modo fase 4 ---
    if args.phase4:
        from mil.phase4_cropper import process_alelo as phase4_process

        print_header()
        print_phase_indicator("Fase 4 - Cropping", "start")

        if args.edge_margin is not None or args.edge_mode is not None:
            report_margin(
                args.edge_margin or 0,
                args.edge_mode or "exact",
                "Fase 4",
            )

        dados_proc = args.output
        dados_patch = os.path.join(os.path.dirname(args.output), get("paths.dados_para_patching_root"))

        for alelo in alelos:
            print_step(f"Fase 4 - {alelo}")
            sd, nd = phase4_process(
                dados_processados_root=dados_proc,
                output_root=dados_patch,
                alelo=alelo,
                edge_margin=args.edge_margin,
                edge_mode=args.edge_mode,
            )
            report_phase4({"sd_ok": sd, "nd_ok": nd, "polygons_total": sd, "errors": 0}, alelo)

        print_phase_indicator("Fase 4 - Cropping", "end")
        return

    # --- Modo pipeline (fases 1-3) ---
    print_header()
    print_phase_indicator("Pipeline (fases 1-3)", "start")

    if args.edge_margin is not None or args.edge_mode is not None:
        report_margin(
            args.edge_margin or 0,
            args.edge_mode or "exact",
            "Pipeline",
        )

    for alelo in alelos:
        print_step(f"Processando {alelo}")
        run_id = next_run_id(alelo)
        run = create_run(run_id, alelo, args.output)

        process_alelo(
            dataset_root=args.dataset,
            output_root=args.output,
            alelo=alelo,
            run=run,
            edge_margin=args.edge_margin,
            edge_mode=args.edge_mode,
        )

        log_path = finish_run(run, args.output)
        report_summary(run)
        print_success(f"Log salvo em: {log_path}")

    print_phase_indicator("Pipeline (fases 1-3)", "end")


if __name__ == "__main__":
    main()
