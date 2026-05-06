#!/usr/bin/env python3
"""
Deterministic linter for SKILL.md files.

Enforces Anthropic's official skill best practices:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

Checks SKILL.md frontmatter and body, plus the bundled reference files in the
skill directory:
  - reference.toc            — files >100 lines need a '## Contents' section
  - reference.length         — reference files capped at 500 lines
  - reference.one-level-deep — only SKILL.md should link to other reference files
  - reference.links-exist    — markdown links inside reference files must resolve
  - reference.no-orphans     — every .md in the skill dir must be linked from SKILL.md
  - plugin.links-exist       — markdown links in plugin files (commands, agents, etc.)
                               outside any skill dir must also resolve

Every rule is pass/fail — no warnings. Use lint-skip in frontmatter to skip rules.

Usage:
    python3 scripts/lint-skills.py                         # lint all skills
    python3 scripts/lint-skills.py path/to/SKILL.md ...    # lint specific files
    python3 scripts/lint-skills.py --changed-only          # CI mode (diff vs base)
    python3 scripts/lint-skills.py --base origin/master    # diff base for --changed-only
    python3 scripts/lint-skills.py --json                  # machine-readable output
    python3 scripts/lint-skills.py --verbose               # show passing checks too

Exit codes:
    0 = all checks pass (or only skips on unchanged/exempted skills)
    1 = one or more checks FAIL on changed skills
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
NAME_MAX_LEN = 64
DESC_MAX_CHARS = 1024
DESC_MIN_WORDS = 10
BODY_MAX_LINES = 500
REFERENCE_MAX_LINES = 500
REFERENCE_TOC_MIN_LINES = 100
TOC_SEARCH_LINES = 30
RESERVED_WORDS = {"anthropic", "claude"}
XML_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
TOC_HEADER_RE = re.compile(
    r"^#{1,3}\s+(contents|table\s+of\s+contents|toc)\b", re.IGNORECASE | re.MULTILINE
)

# Directories to skip when walking the tree for SKILL.md files.
SKIP_DIRS = {
    ".git", ".github", ".hg", ".svn",
    "node_modules", "vendor", "tmp", "log", "dist", "build",
    "__pycache__", ".venv", "venv", ".tox", ".pytest_cache",
}


def discover_skills(root: Path) -> list[Path]:
    """Recursively find all SKILL.md files under root, skipping noisy directories."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if "SKILL.md" in filenames:
            found.append(Path(dirpath) / "SKILL.md")
    return sorted(found)


def parse_frontmatter(skill_md: Path) -> tuple[dict | None, str, str]:
    """Parse YAML frontmatter. Returns (frontmatter_dict, raw_frontmatter, body)."""
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        return None, "", content

    raw = match.group(1)
    body = match.group(2)
    fm = {}

    # name
    name_m = re.search(r"^name:\s*(.+)$", raw, re.MULTILINE)
    if name_m:
        fm["name"] = name_m.group(1).strip().strip("'\"")

    # description (multiline |, multiline >, or inline)
    desc_m = re.search(r"^description:\s*[|>]\s*\n((?:\s+.+\n?)*)", raw, re.MULTILINE)
    if desc_m:
        fm["description"] = desc_m.group(1).strip()
    else:
        desc_m = re.search(r"^description:\s*(.+)$", raw, re.MULTILINE)
        if desc_m:
            val = desc_m.group(1).strip()
            if val.startswith(('"', "'")):
                val = val[1:-1] if len(val) > 1 and val[-1] == val[0] else val[1:]
            fm["description"] = val

    # allowed-tools
    tools_m = re.search(r"^allowed-tools:\s*(.+)$", raw, re.MULTILINE)
    if tools_m:
        fm["allowed-tools"] = tools_m.group(1).strip()

    # lint-skip (list of {rule, reason} dicts)
    skip_list = []
    skip_block = re.search(
        r"^lint-skip:\s*\n((?:\s+-.+\n?(?:\s+\w.+\n?)*)*)", raw, re.MULTILINE
    )
    if skip_block:
        entries = re.findall(
            r"-\s*rule:\s*(.+?)(?:\n\s+reason:\s*['\"]?(.+?)['\"]?\s*$|\s*$)",
            skip_block.group(1),
            re.MULTILINE,
        )
        for rule_id, reason in entries:
            skip_list.append({"rule": rule_id.strip(), "reason": reason.strip()})
    fm["lint-skip"] = skip_list

    return fm, raw, body


def detect_diff_base() -> str | None:
    """Pick a sensible git ref to diff against for --changed-only."""
    candidates = ["origin/main", "origin/master", "main", "master"]
    for ref in candidates:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            capture_output=True, cwd=REPO_ROOT,
        )
        if result.returncode == 0:
            return ref
    return None


def get_changed_skill_dirs(base: str | None) -> set[str]:
    """Return repo-relative directories of skills changed vs the diff base."""
    if os.environ.get("GITHUB_ACTIONS"):
        subprocess.run(
            ["git", "fetch", "--deepen=1", "--no-tags"],
            capture_output=True, check=False, cwd=REPO_ROOT,
        )
        diff_args = ["HEAD^1", "HEAD"]
    else:
        if not base:
            return set()
        diff_args = [f"{base}...HEAD"]

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", *diff_args],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()

    # Build a set of skill directories (those containing a SKILL.md) currently in the tree.
    skill_dirs = {str(p.parent.relative_to(REPO_ROOT)) for p in discover_skills(REPO_ROOT)}

    changed: set[str] = set()
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # A skill is "changed" if any file under its directory changed.
        for sd in skill_dirs:
            if line == f"{sd}/SKILL.md" or line.startswith(f"{sd}/"):
                changed.add(sd)
                break
    return changed


KNOWN_RULES = {
    "frontmatter.exists", "frontmatter.name.exists", "frontmatter.name.format",
    "frontmatter.name.no-reserved", "frontmatter.name.matches-dir",
    "frontmatter.description.exists", "frontmatter.description.max-length",
    "frontmatter.description.min-words", "frontmatter.description.no-xml",
    "skill-length", "references-exist",
    "reference.toc", "reference.length", "reference.one-level-deep",
    "reference.links-exist", "reference.no-orphans",
    "plugin.links-exist",
}


def discover_plugin_md_files(repo_root: Path, skill_dirs: set[Path]) -> list[Path]:
    """Find every .md file in the repo that is NOT inside a skill directory."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        cur = Path(dirpath).resolve()
        # Skip if this directory is inside any skill dir
        if any(_is_inside_or_equal(cur, sd) for sd in skill_dirs):
            continue
        for fname in filenames:
            if fname.endswith(".md"):
                found.append(Path(dirpath) / fname)
    return sorted(found)


def _is_inside_or_equal(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def check_plugin_links(plugin_files: list[Path], repo_root: Path) -> list[dict]:
    """Verify that every relative link in plugin-level files resolves to an existing target."""
    broken: list[str] = []
    for f in plugin_files:
        rel = f.relative_to(repo_root).as_posix()
        text = f.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            href = match.group(2)
            if is_external_or_placeholder(href):
                continue
            href_path = href.split("#")[0]
            if not href_path:
                continue
            target = (f.parent / href_path).resolve()
            if not target.exists():
                broken.append(f"{rel} -> {href}")

    if broken:
        # Show every broken link — they are usually few and each one needs human action
        sample = "; ".join(broken)
        return [{
            "check": "plugin.links-exist", "status": "FAIL",
            "detail": f"Broken links in plugin files ({len(broken)}): {sample}",
        }]
    if plugin_files:
        return [{
            "check": "plugin.links-exist", "status": "PASS",
            "detail": f"{len(plugin_files)} file(s) checked",
        }]
    return [{
        "check": "plugin.links-exist", "status": "PASS",
        "detail": "no plugin-level files",
    }]


def discover_reference_files(skill_dir: Path) -> list[Path]:
    """Return all .md files under the skill dir except SKILL.md itself."""
    refs: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".md") and not (Path(dirpath) == skill_dir and fname == "SKILL.md"):
                refs.append(Path(dirpath) / fname)
    return sorted(refs)


def is_external_or_placeholder(href: str) -> bool:
    """Mirror of the link-skip logic from the references-exist check."""
    if href.startswith(("http://", "https://", "#", "mailto:", "tel:")):
        return True
    if href.startswith("mcp__") or "__" in href:
        return True
    if re.match(r"^[A-Z_]+$", href) or "{" in href or "<" in href:
        return True
    if href.lower() in ("url", "link", "...", "path", "file"):
        return True
    return False


def check_skill(skill_md: Path) -> list[dict]:
    """Run all lint rules on a single SKILL.md. Returns list of check results."""
    skill_dir = skill_md.parent
    dir_name = skill_dir.name
    results = []
    skip_map: dict[str, str] = {}  # rule -> reason

    def add(check_id: str, status: str, detail: str = ""):
        if status == "FAIL" and check_id in skip_map:
            results.append({
                "check": check_id, "status": "SKIP",
                "detail": f"[skipped: {skip_map[check_id]}]",
            })
            return
        results.append({"check": check_id, "status": status, "detail": detail})

    # ── 1. Frontmatter exists ──────────────────────────────────────
    fm, raw_fm, body = parse_frontmatter(skill_md)
    if fm is None:
        add("frontmatter.exists", "FAIL", "No YAML frontmatter (--- markers) found")
        return results
    add("frontmatter.exists", "PASS")

    # Validate and build lint-skip map
    for entry in fm.get("lint-skip", []):
        rule_id = entry.get("rule", "")
        reason = entry.get("reason", "")
        if not reason:
            add("invalid-lint-skip", "FAIL",
                f"lint-skip entry for '{rule_id}' missing required 'reason'")
        elif rule_id not in KNOWN_RULES:
            add("invalid-lint-skip", "FAIL",
                f"lint-skip references unknown rule '{rule_id}'")
        else:
            skip_map[rule_id] = reason

    # ── 2. Name ────────────────────────────────────────────────────
    name = fm.get("name")
    if not name:
        add("frontmatter.name.exists", "FAIL", "Missing 'name' field")
    else:
        add("frontmatter.name.exists", "PASS")

        if not NAME_RE.match(name):
            add("frontmatter.name.format", "FAIL",
                f"'{name}' must be lowercase letters, numbers, hyphens only")
        elif len(name) > NAME_MAX_LEN:
            add("frontmatter.name.format", "FAIL",
                f"'{name}' is {len(name)} chars (max {NAME_MAX_LEN})")
        else:
            add("frontmatter.name.format", "PASS", f"'{name}' ({len(name)} chars)")

        if any(w in name for w in RESERVED_WORDS):
            add("frontmatter.name.no-reserved", "FAIL",
                f"'{name}' contains reserved word (anthropic/claude)")
        else:
            add("frontmatter.name.no-reserved", "PASS")

        if name != dir_name:
            add("frontmatter.name.matches-dir", "FAIL",
                f"name='{name}' but directory is '{dir_name}'")
        else:
            add("frontmatter.name.matches-dir", "PASS")

    # ── 3. Description ─────────────────────────────────────────────
    desc = fm.get("description")
    if not desc:
        add("frontmatter.description.exists", "FAIL", "Missing or empty 'description'")
    else:
        add("frontmatter.description.exists", "PASS")

        char_count = len(desc)
        if char_count > DESC_MAX_CHARS:
            add("frontmatter.description.max-length", "FAIL",
                f"{char_count} chars (max {DESC_MAX_CHARS})")
        else:
            add("frontmatter.description.max-length", "PASS", f"{char_count} chars")

        word_count = len(desc.split())
        if word_count < DESC_MIN_WORDS:
            add("frontmatter.description.min-words", "FAIL",
                f"{word_count} words (min {DESC_MIN_WORDS})")
        else:
            add("frontmatter.description.min-words", "PASS", f"{word_count} words")

        if XML_TAG_RE.search(desc):
            add("frontmatter.description.no-xml", "FAIL", "Contains XML tags")
        else:
            add("frontmatter.description.no-xml", "PASS")

    # ── 4. Skill length ────────────────────────────────────────────
    total_lines = skill_md.read_text().count("\n") + 1
    refs_exist = (skill_dir / "references").is_dir() and any((skill_dir / "references").iterdir())

    if total_lines > BODY_MAX_LINES:
        if refs_exist:
            add("skill-length", "PASS",
                f"{total_lines} lines (has references/ for progressive disclosure)")
        else:
            add("skill-length", "FAIL",
                f"{total_lines} lines with no references/ — split into references/")
    else:
        add("skill-length", "PASS", f"{total_lines} lines")

    # ── 5. References exist ────────────────────────────────────────
    missing_refs = []
    for match in MD_LINK_RE.finditer(body):
        href = match.group(2)
        if is_external_or_placeholder(href):
            continue
        # Strip #fragment before resolving
        href_path = href.split("#")[0]
        if not href_path:
            continue
        ref_path = (skill_dir / href_path).resolve()
        if not ref_path.exists():
            missing_refs.append(href)

    if missing_refs:
        add("references-exist", "FAIL",
            f"Missing referenced files: {', '.join(missing_refs[:3])}")
    else:
        add("references-exist", "PASS")

    # ── 6. Reference files: TOC, length, one-level-deep, links-exist ──
    reference_files = discover_reference_files(skill_dir)
    skill_dir_resolved = skill_dir.resolve()

    missing_toc: list[str] = []
    too_long: list[str] = []
    nested: list[str] = []     # "from -> to" pairs
    broken: list[str] = []     # "from -> href" pairs for missing targets

    for ref in reference_files:
        rel = ref.relative_to(skill_dir).as_posix()
        ref_text = ref.read_text(encoding="utf-8")
        line_count = ref_text.count("\n") + 1

        # TOC required for files >100 lines, in the first ~30 lines
        if line_count > REFERENCE_TOC_MIN_LINES:
            head = "\n".join(ref_text.splitlines()[:TOC_SEARCH_LINES])
            if not TOC_HEADER_RE.search(head):
                missing_toc.append(f"{rel} ({line_count} lines)")

        # Length cap matches SKILL.md guidance
        if line_count > REFERENCE_MAX_LINES:
            too_long.append(f"{rel} ({line_count} lines)")

        for match in MD_LINK_RE.finditer(ref_text):
            href = match.group(2)
            if is_external_or_placeholder(href):
                continue
            href_path = href.split("#")[0]
            if not href_path:
                continue  # pure anchor — same file, fine
            target = (ref.parent / href_path).resolve()

            # links-exist: target file must exist on disk
            if not target.exists():
                broken.append(f"{rel} -> {href}")
                continue  # broken targets aren't useful for further checks

            # one-level-deep: links to other files inside the skill dir are nested
            try:
                target_rel = target.relative_to(skill_dir_resolved)
            except ValueError:
                continue  # link points outside the skill dir
            if target == ref.resolve():
                continue  # self-link with fragment
            nested.append(f"{rel} -> {target_rel.as_posix()}")

    if missing_toc:
        sample = ", ".join(missing_toc[:3])
        more = f" (+{len(missing_toc) - 3} more)" if len(missing_toc) > 3 else ""
        add("reference.toc", "FAIL",
            f"Reference files >{REFERENCE_TOC_MIN_LINES} lines need a '## Contents' "
            f"section in the first {TOC_SEARCH_LINES} lines: {sample}{more}")
    elif reference_files:
        add("reference.toc", "PASS",
            f"{len(reference_files)} reference file(s) checked")
    else:
        add("reference.toc", "PASS", "no reference files")

    if too_long:
        sample = ", ".join(too_long[:3])
        more = f" (+{len(too_long) - 3} more)" if len(too_long) > 3 else ""
        add("reference.length", "FAIL",
            f"Reference files exceed {REFERENCE_MAX_LINES} lines — split further: "
            f"{sample}{more}")
    elif reference_files:
        add("reference.length", "PASS")
    else:
        add("reference.length", "PASS", "no reference files")

    if nested:
        sample = "; ".join(nested[:3])
        more = f" (+{len(nested) - 3} more)" if len(nested) > 3 else ""
        add("reference.one-level-deep", "FAIL",
            f"Reference files link to other reference files (link only from SKILL.md): "
            f"{sample}{more}")
    elif reference_files:
        add("reference.one-level-deep", "PASS")
    else:
        add("reference.one-level-deep", "PASS", "no reference files")

    if broken:
        sample = "; ".join(broken[:3])
        more = f" (+{len(broken) - 3} more)" if len(broken) > 3 else ""
        add("reference.links-exist", "FAIL",
            f"Reference files contain broken links: {sample}{more}")
    elif reference_files:
        add("reference.links-exist", "PASS")
    else:
        add("reference.links-exist", "PASS", "no reference files")

    # ── 7. No orphans: every .md must be linked from SKILL.md ──────
    linked_targets: set[Path] = set()
    for match in MD_LINK_RE.finditer(body):
        href = match.group(2)
        if is_external_or_placeholder(href):
            continue
        href_path = href.split("#")[0]
        if not href_path:
            continue
        target = (skill_dir / href_path).resolve()
        if target.is_file():
            linked_targets.add(target)

    orphans: list[str] = []
    for ref in reference_files:
        if ref.resolve() not in linked_targets:
            orphans.append(ref.relative_to(skill_dir).as_posix())

    if orphans:
        sample = ", ".join(orphans[:5])
        more = f" (+{len(orphans) - 5} more)" if len(orphans) > 5 else ""
        add("reference.no-orphans", "FAIL",
            f"Reference files not linked from SKILL.md: {sample}{more}")
    elif reference_files:
        add("reference.no-orphans", "PASS")
    else:
        add("reference.no-orphans", "PASS", "no reference files")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Lint SKILL.md files against Anthropic best practices"
    )
    parser.add_argument("--changed-only", action="store_true",
                        help="Only FAIL on skills changed vs the diff base (CI mode)")
    parser.add_argument("--base", default=None,
                        help="Git ref to diff against for --changed-only "
                             "(default: auto-detect origin/main, origin/master, main, master)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Show all checks including passing ones")
    parser.add_argument("paths", nargs="*",
                        help="Specific SKILL.md paths to check (default: all under repo)")
    args = parser.parse_args()

    # Discover skills
    if args.paths:
        skills = [Path(p).resolve() for p in args.paths]
    else:
        skills = discover_skills(REPO_ROOT)

    if not skills:
        print("No SKILL.md files found.")
        sys.exit(0)

    # Determine changed skills
    changed: set[str] = set()
    if args.changed_only:
        base = args.base or detect_diff_base()
        if not base and not os.environ.get("GITHUB_ACTIONS"):
            print("Could not detect a diff base. Pass --base <ref> explicitly.")
            sys.exit(2)
        changed = get_changed_skill_dirs(base)
        if changed:
            print(f"Changed skills: {', '.join(sorted(s.split('/')[-1] for s in changed))}")
        else:
            print("No skill files changed.")
            sys.exit(0)

    print(f"Linting {len(skills)} skill(s)...\n")

    all_results = {}
    any_fail = False

    for skill_md in skills:
        skill_dir = skill_md.parent
        try:
            rel_dir = str(skill_dir.relative_to(REPO_ROOT))
        except ValueError:
            rel_dir = str(skill_dir)
        skill_name = skill_dir.name
        is_changed = not args.changed_only or rel_dir in changed

        results = check_skill(skill_md)

        # Downgrade FAILs to SKIP for unchanged skills
        if not is_changed:
            for r in results:
                if r["status"] == "FAIL":
                    r["status"] = "SKIP"
                    r["detail"] = f"[unchanged skill] {r['detail']}" if r["detail"] else "[unchanged skill]"

        has_fail = any(r["status"] == "FAIL" for r in results)
        has_skip = any(r["status"] == "SKIP" for r in results)
        if has_fail:
            any_fail = True

        all_results[rel_dir] = {
            "name": skill_name,
            "changed": is_changed,
            "results": results,
            "status": "FAIL" if has_fail else ("SKIP" if has_skip else "PASS"),
        }

    # Plugin-wide checks (commands, agents, top-level docs — anything outside skill dirs).
    # Always runs regardless of --changed-only: a broken link in a command file affects
    # every skill it points into.
    skill_dirs_resolved = {s.parent.resolve() for s in skills}
    plugin_files = discover_plugin_md_files(REPO_ROOT, skill_dirs_resolved)
    plugin_results = check_plugin_links(plugin_files, REPO_ROOT)
    plugin_has_fail = any(r["status"] == "FAIL" for r in plugin_results)
    if plugin_has_fail:
        any_fail = True
    all_results["<plugin-wide>"] = {
        "name": "<plugin-wide>",
        "changed": True,
        "results": plugin_results,
        "status": "FAIL" if plugin_has_fail else "PASS",
    }

    # Output
    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        for rel_dir, data in sorted(all_results.items()):
            non_pass = [r for r in data["results"] if r["status"] != "PASS"]
            if not non_pass and not args.verbose:
                continue

            changed_tag = "" if data["changed"] else " (unchanged)"
            icon = data["status"]
            print(f"{'=' * 60}")
            print(f"  {data['name']}{changed_tag} — {icon}")
            print(f"{'=' * 60}")

            for r in data["results"]:
                if r["status"] == "PASS" and not args.verbose:
                    continue
                status_icon = {
                    "PASS": "  pass", "FAIL": "**FAIL", "SKIP": "  skip",
                }
                line = f"  {status_icon.get(r['status'], '  ????')}  {r['check']}"
                if r["detail"]:
                    line += f"  — {r['detail']}"
                print(line)
            print()

    # Summary (count real skills only; plugin-wide is a separate scope)
    skill_results = {k: v for k, v in all_results.items() if k != "<plugin-wide>"}
    total = len(skill_results)
    fails = sum(1 for d in skill_results.values() if d["status"] == "FAIL")
    skips = sum(1 for d in skill_results.values() if d["status"] == "SKIP")
    passes = total - fails - skips

    if not args.json:
        print(f"Summary: {passes} pass, {skips} skip, {fails} fail (out of {total} skills)")
        plugin_entry = all_results.get("<plugin-wide>")
        if plugin_entry:
            icon = "FAIL" if plugin_entry["status"] == "FAIL" else "PASS"
            print(f"Plugin-wide: {icon}")
        if any_fail:
            print("\nFix the FAIL checks above before merging.")

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
