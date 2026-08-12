"""Command-line interface for local execution and human approval resume."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import Settings
from .models import AuditStartRequest, ResumeRequest
from .service import ContractGuardService


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contractguard", description="Secure multi-agent contract audit")
    parser.add_argument("--root", type=Path, default=None, help="Project root for data/evidence paths")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a new audit")
    start.add_argument("--request", required=True)
    start.add_argument("--contract", type=Path)
    start.add_argument("--contract-text")
    start.add_argument("--thread-id")
    start.add_argument("--simulate-primary-failure", action="store_true")
    start.add_argument("--simulate-output-validation-failure", action="store_true")
    start.add_argument("--simulate-quality-retry", action="store_true")

    resume = subparsers.add_parser("resume", help="Resume a paused human-approval node")
    resume.add_argument("thread_id")
    resume.add_argument("decision", choices=["approve", "reject"])
    resume.add_argument("--comment", default="")
    resume.add_argument("--approver", default="human-reviewer")

    status_parser = subparsers.add_parser("status", help="Read a durable checkpoint")
    status_parser.add_argument("thread_id")

    history_parser = subparsers.add_parser("history", help="Read checkpoint history")
    history_parser.add_argument("thread_id")

    subparsers.add_parser("graph", help="Print graph nodes, edges, and loops")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env(args.root)
    with ContractGuardService(settings) as service:
        if args.command == "start":
            flags = {
                "simulate_primary_failure": args.simulate_primary_failure,
                "simulate_output_validation_failure": args.simulate_output_validation_failure,
                "simulate_quality_retry": args.simulate_quality_retry,
            }
            result = service.start(
                AuditStartRequest(
                    thread_id=args.thread_id,
                    request_text=args.request,
                    contract_path=str(args.contract.resolve()) if args.contract else None,
                    contract_text=args.contract_text,
                    flags=flags,
                )
            )
        elif args.command == "resume":
            result = service.resume(
                args.thread_id,
                ResumeRequest(decision=args.decision, comment=args.comment, approver=args.approver),
            )
        elif args.command == "status":
            result = service.get(args.thread_id)
        elif args.command == "history":
            result = service.history(args.thread_id)
        else:
            result = service.graph_spec()
    _print_json(result)
    return 0
