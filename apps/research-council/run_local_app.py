"""Local Tk launcher for deterministic Research Council demo runs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

from research_council import (
    LLMAugmentationMode,
    ResearchCouncilInput,
    list_profiles,
    run_research_council,
    write_result_json,
)


APP_TITLE = "Research Council Local Launcher"
DEFAULT_OUTPUT_ROOT = Path.home() / "ResearchCouncilRuns"
DEFAULT_PROFILE_ID = "ai_saas"
AUGMENTATION_MODE_VALUES = tuple(mode.value for mode in LLMAugmentationMode)
SANDBOX_MESSAGE = "deterministic sandbox, no external LLM calls"
IDEA_ONLY_HELP = (
    "You can start with only an idea. Empty fields will use safe default prompts."
)
DEFAULT_GOAL = (
    "Evaluate whether this idea can become a viable MVP and identify the next "
    "validation step."
)
DEFAULT_CONTEXT = (
    "The user is exploring this as a product or workflow opportunity. The report "
    "should identify assumptions, evidence gaps, risks, and minimum viable experiments."
)
DEFAULT_CONSTRAINTS = (
    "Human review required",
    "No external services",
    "Treat outputs as validation planning, not final proof",
)


@dataclass(frozen=True)
class LocalRunArtifacts:
    run_dir: Path
    input_json: Path
    report_md: Path
    result_json: Path


def split_lines(value: str) -> tuple[str, ...]:
    """Return non-empty stripped lines from a multiline text box."""

    return tuple(line.strip() for line in value.splitlines() if line.strip())


def default_output_root() -> Path:
    return DEFAULT_OUTPUT_ROOT


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def normalize_output_root(output_root: Path) -> Path:
    resolved_output_root = output_root.expanduser().resolve(strict=False)
    resolved_repo_root = repo_root().resolve(strict=False)
    if is_relative_to(resolved_output_root, resolved_repo_root):
        raise ValueError(
            "Output directory must be outside the repository. "
            f"Choose a folder outside {resolved_repo_root}."
        )
    return resolved_output_root


def profile_ids() -> tuple[str, ...]:
    ids = tuple(profile.id for profile in list_profiles())
    if DEFAULT_PROFILE_ID in ids:
        return ids
    return (DEFAULT_PROFILE_ID, *ids)


def build_input_payload(
    *,
    idea: str,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
    provided_evidence: tuple[str, ...],
) -> dict[str, object]:
    return {
        "idea": idea,
        "goal": goal,
        "context": context,
        "constraints": list(constraints),
        "provided_evidence": list(provided_evidence),
    }


def with_safe_defaults(
    *,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
) -> tuple[str, str, tuple[str, ...]]:
    normalized_constraints = tuple(
        str(item).strip() for item in constraints if str(item).strip()
    )
    return (
        goal.strip() or DEFAULT_GOAL,
        context.strip() or DEFAULT_CONTEXT,
        normalized_constraints or DEFAULT_CONSTRAINTS,
    )


def allocate_run_dir(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f"research-council-{timestamp}"
    for index in range(1000):
        name = base_name if index == 0 else f"{base_name}-{index:03d}"
        candidate = output_root / name
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"could not allocate run directory under {output_root}")


def run_local_research(
    *,
    idea: str,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
    provided_evidence: tuple[str, ...],
    profile: str,
    llm_augmentation_mode: str,
    output_root: Path,
) -> LocalRunArtifacts:
    idea = idea.strip()
    goal = goal.strip()
    context = context.strip()
    profile = profile.strip() or DEFAULT_PROFILE_ID
    llm_augmentation_mode = llm_augmentation_mode.strip() or LLMAugmentationMode.OFF.value
    goal, context, constraints = with_safe_defaults(
        goal=goal,
        context=context,
        constraints=constraints,
    )

    if not idea:
        raise ValueError("Idea is required.")
    if llm_augmentation_mode not in AUGMENTATION_MODE_VALUES:
        raise ValueError(f"Unknown LLM augmentation mode: {llm_augmentation_mode}")

    output_root = normalize_output_root(output_root)
    run_dir = allocate_run_dir(output_root)
    input_json = run_dir / "input.json"
    report_md = run_dir / "report.md"
    result_json = run_dir / "result.json"

    payload = build_input_payload(
        idea=idea,
        goal=goal,
        context=context,
        constraints=constraints,
        provided_evidence=provided_evidence,
    )
    input_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_research_council(
        ResearchCouncilInput(
            raw_idea=idea,
            goal=goal,
            context=context,
            constraints=constraints,
            provided_evidence=provided_evidence,
        ),
        profile=profile,
        llm_advisor_config=llm_augmentation_mode,
    )
    report_md.write_text(result.markdown_report.markdown, encoding="utf-8")
    write_result_json(result, result_json)
    return LocalRunArtifacts(
        run_dir=run_dir,
        input_json=input_json,
        report_md=report_md,
        result_json=result_json,
    )


def open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(path)], check=False)


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class LocalLauncher:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.last_artifacts: LocalRunArtifacts | None = None

            root.title(APP_TITLE)
            root.minsize(840, 720)

            self.profile_var = tk.StringVar(value=DEFAULT_PROFILE_ID)
            self.mode_var = tk.StringVar(value=LLMAugmentationMode.OFF.value)
            self.output_dir_var = tk.StringVar(value=str(default_output_root()))
            self.report_path_var = tk.StringVar(value="")
            self.result_path_var = tk.StringVar(value="")

            self._build_layout(root)

        def _build_layout(self, root: tk.Tk) -> None:
            frame = ttk.Frame(root, padding=16)
            frame.grid(row=0, column=0, sticky="nsew")
            root.columnconfigure(0, weight=1)
            root.rowconfigure(0, weight=1)

            frame.columnconfigure(1, weight=1)
            frame.rowconfigure(4, weight=1)
            frame.rowconfigure(5, weight=1)
            frame.rowconfigure(6, weight=1)
            frame.rowconfigure(7, weight=1)
            frame.rowconfigure(12, weight=1)

            title = ttk.Label(frame, text=APP_TITLE, font=("", 15, "bold"))
            title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
            subtitle = ttk.Label(frame, text=SANDBOX_MESSAGE)
            subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))
            idea_only_help = ttk.Label(frame, text=IDEA_ONLY_HELP)
            idea_only_help.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))

            ttk.Label(frame, text="Idea").grid(row=3, column=0, sticky="nw")
            self.idea_text = self._text_box(frame, row=3, height=4)

            ttk.Label(frame, text="Goal").grid(row=4, column=0, sticky="nw")
            self.goal_text = self._text_box(frame, row=4, height=3)

            ttk.Label(frame, text="Context").grid(row=5, column=0, sticky="nw")
            self.context_text = self._text_box(frame, row=5, height=4)

            ttk.Label(frame, text="Constraints").grid(row=6, column=0, sticky="nw")
            self.constraints_text = self._text_box(frame, row=6, height=4)

            ttk.Label(frame, text="Provided evidence").grid(row=7, column=0, sticky="nw")
            self.evidence_text = self._text_box(frame, row=7, height=4)

            ttk.Label(frame, text="Profile").grid(row=8, column=0, sticky="w", pady=(10, 0))
            profile_box = ttk.Combobox(
                frame,
                textvariable=self.profile_var,
                values=profile_ids(),
                state="readonly",
            )
            profile_box.grid(row=8, column=1, sticky="ew", pady=(10, 0))

            ttk.Label(frame, text="LLM augmentation mode").grid(
                row=9,
                column=0,
                sticky="w",
                pady=(8, 0),
            )
            mode_box = ttk.Combobox(
                frame,
                textvariable=self.mode_var,
                values=AUGMENTATION_MODE_VALUES,
                state="readonly",
            )
            mode_box.grid(row=9, column=1, sticky="ew", pady=(8, 0))
            ttk.Label(frame, text=SANDBOX_MESSAGE).grid(
                row=9,
                column=2,
                sticky="w",
                padx=(8, 0),
                pady=(8, 0),
            )

            ttk.Label(frame, text="Output directory").grid(
                row=10,
                column=0,
                sticky="w",
                pady=(8, 0),
            )
            output_entry = ttk.Entry(frame, textvariable=self.output_dir_var)
            output_entry.grid(row=10, column=1, sticky="ew", pady=(8, 0))
            ttk.Button(frame, text="Choose...", command=self.choose_output_dir).grid(
                row=10,
                column=2,
                sticky="ew",
                padx=(8, 0),
                pady=(8, 0),
            )

            buttons = ttk.Frame(frame)
            buttons.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(12, 8))
            buttons.columnconfigure(4, weight=1)
            self.run_button = ttk.Button(buttons, text="Run", command=self.run)
            self.run_button.grid(row=0, column=0, sticky="w")
            self.open_folder_button = ttk.Button(
                buttons,
                text="Open output folder",
                command=self.open_output_folder,
                state="disabled",
            )
            self.open_folder_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
            self.open_report_button = ttk.Button(
                buttons,
                text="Open report",
                command=self.open_report,
                state="disabled",
            )
            self.open_report_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

            ttk.Label(frame, text="Status / output log").grid(row=12, column=0, sticky="nw")
            log_frame = ttk.Frame(frame)
            log_frame.grid(row=12, column=1, columnspan=2, sticky="nsew")
            log_frame.columnconfigure(0, weight=1)
            log_frame.rowconfigure(0, weight=1)
            self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled")
            self.log_text.grid(row=0, column=0, sticky="nsew")
            log_scroll = ttk.Scrollbar(
                log_frame,
                orient="vertical",
                command=self.log_text.yview,
            )
            log_scroll.grid(row=0, column=1, sticky="ns")
            self.log_text.configure(yscrollcommand=log_scroll.set)

            ttk.Label(frame, text="report.md").grid(row=13, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(
                frame,
                textvariable=self.report_path_var,
                state="readonly",
            ).grid(row=13, column=1, columnspan=2, sticky="ew", pady=(8, 0))
            ttk.Label(frame, text="result.json").grid(row=14, column=0, sticky="w", pady=(4, 0))
            ttk.Entry(
                frame,
                textvariable=self.result_path_var,
                state="readonly",
            ).grid(row=14, column=1, columnspan=2, sticky="ew", pady=(4, 0))

        def _text_box(self, parent: ttk.Frame, *, row: int, height: int) -> tk.Text:
            box = tk.Text(parent, height=height, wrap="word")
            box.grid(row=row, column=1, columnspan=2, sticky="nsew", pady=(0, 8))
            return box

        def choose_output_dir(self) -> None:
            selected = filedialog.askdirectory(
                initialdir=self.output_dir_var.get() or str(Path.home())
            )
            if selected:
                self.output_dir_var.set(selected)

        def run(self) -> None:
            self.run_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.open_report_button.configure(state="disabled")
            self.report_path_var.set("")
            self.result_path_var.set("")
            self.append_log("Running deterministic Research Council pass...")
            self.root.update_idletasks()
            try:
                artifacts = run_local_research(
                    idea=self.idea_text.get("1.0", "end"),
                    goal=self.goal_text.get("1.0", "end"),
                    context=self.context_text.get("1.0", "end"),
                    constraints=split_lines(self.constraints_text.get("1.0", "end")),
                    provided_evidence=split_lines(self.evidence_text.get("1.0", "end")),
                    profile=self.profile_var.get(),
                    llm_augmentation_mode=self.mode_var.get(),
                    output_root=Path(self.output_dir_var.get()),
                )
            except Exception as exc:
                self.append_log(f"Run failed: {exc}")
                messagebox.showerror(APP_TITLE, str(exc))
            else:
                self.last_artifacts = artifacts
                self.report_path_var.set(str(artifacts.report_md))
                self.result_path_var.set(str(artifacts.result_json))
                self.open_folder_button.configure(state="normal")
                self.open_report_button.configure(state="normal")
                self.append_log(f"Created input.json: {artifacts.input_json}")
                self.append_log(f"Created report.md: {artifacts.report_md}")
                self.append_log(f"Created result.json: {artifacts.result_json}")
            finally:
                self.run_button.configure(state="normal")

        def append_log(self, message: str) -> None:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        def open_output_folder(self) -> None:
            if self.last_artifacts is not None:
                self._open(self.last_artifacts.run_dir)

        def open_report(self) -> None:
            if self.last_artifacts is not None:
                self._open(self.last_artifacts.report_md)

        def _open(self, path: Path) -> None:
            try:
                open_path(path)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, str(exc))

    root = tk.Tk()
    LocalLauncher(root)
    root.mainloop()


def run_self_test(output_dir: Path) -> LocalRunArtifacts:
    artifacts = run_local_research(
        idea="CareNote assistant for family caregivers",
        goal="",
        context="",
        constraints=(),
        provided_evidence=(),
        profile=DEFAULT_PROFILE_ID,
        llm_augmentation_mode=LLMAugmentationMode.OFF.value,
        output_root=output_dir,
    )
    for path in (artifacts.input_json, artifacts.report_md, artifacts.result_json):
        if not path.exists():
            raise RuntimeError(f"self-test did not create {path}")
    if not artifacts.report_md.read_text(encoding="utf-8").startswith(
        "# Research Council Report"
    ):
        raise RuntimeError("self-test report.md did not contain a report")

    input_payload = json.loads(artifacts.input_json.read_text(encoding="utf-8"))
    if input_payload["goal"] != DEFAULT_GOAL:
        raise RuntimeError("self-test input.json did not include the default goal")
    if input_payload["context"] != DEFAULT_CONTEXT:
        raise RuntimeError("self-test input.json did not include the default context")
    if input_payload["constraints"] != list(DEFAULT_CONSTRAINTS):
        raise RuntimeError("self-test input.json did not include default constraints")
    if input_payload["provided_evidence"] != []:
        raise RuntimeError("self-test input.json should allow empty provided evidence")

    report_text = artifacts.report_md.read_text(encoding="utf-8")
    if "Missing evidence entries" not in report_text:
        raise RuntimeError("self-test report.md did not show missing evidence")

    result_payload = json.loads(artifacts.result_json.read_text(encoding="utf-8"))
    if result_payload["profile"]["profile_id"] != DEFAULT_PROFILE_ID:
        raise RuntimeError("self-test result.json did not preserve the selected profile")
    return artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open the local Research Council Tk launcher, or run a headless "
            "self-test that writes input.json, report.md, and result.json."
        )
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a headless launcher smoke test instead of opening the GUI.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_root(),
        help="Output root for GUI runs or --self-test runs.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        artifacts = run_self_test(args.output_dir)
        print("Research Council local launcher self-test passed")
        print(f"Run folder: {artifacts.run_dir}")
        print(f"Report: {artifacts.report_md}")
        print(f"Result JSON: {artifacts.result_json}")
        return 0

    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
