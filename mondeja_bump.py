import argparse
import os
import re
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

DEFAULT_SEMVER_REGEX = r"\d+\.\d+\.\d+"
DEFAULT_PYPROJECT_TOML_SEMVER_REGEX = r"(version = [\"'])(\d+\.\d+\.\d+)([\"'])"
SEMVER_PART_ALIASES = {
    "major": "major",
    "minor": "minor",
    "patch": "patch",
    "micro": "patch",
    "M": "major",
    "m": "minor",
    "p": "patch",
    "1": "major",
    "2": "minor",
    "3": "patch",
}


def error(msg, exitcode=1, exit=True):
    sys.stderr.write(f"[mondeja's-bump] {msg}\n")
    if exit:
        sys.exit(exitcode)


def is_semver_version_or_error(version):
    if not re.match(DEFAULT_SEMVER_REGEX, version):
        error(f"The version '{version}' does not follow semantic versioning!")


def read_config():
    if not os.path.isfile("pyproject.toml"):
        error(
            "Reading of configuration from"
            " another file than pyproject.toml is not supported\n"
        )

    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomllib.load(f)

    if "bump" in pyproject_toml.get("tool", {}):
        if "source" not in pyproject_toml["tool"]["bump"]:
            source = {
                "file": "pyproject.toml",
                "regex": DEFAULT_SEMVER_REGEX,
            }
        else:
            source = pyproject_toml["tool"]["bump"]["source"]
            if isinstance(source, str):
                source = {
                    "file": source,
                    "regex": DEFAULT_SEMVER_REGEX,
                }
            elif not isinstance(source, dict):
                error(
                    f"Invalid type {type(source).__name__} for"
                    " `tool.bump.source` config field"
                )
            else:
                source = {
                    "file": source.get("file", "pyproject.toml"),
                    "regex": DEFAULT_SEMVER_REGEX,
                }
        if "targets" not in pyproject_toml["tool"]["bump"]:
            targets = [
                {
                    "file": "pyproject.toml",
                    "regex": DEFAULT_SEMVER_REGEX,
                }
            ]
        else:
            _targets = pyproject_toml["tool"]["bump"]["targets"]

            if not isinstance(_targets, list):
                error(
                    f"Invalid type {type(_targets).__name__} for"
                    " `tool.bump.targets` config field"
                )

            targets, _errored = [], False
            for i, target in enumerate(_targets):
                _target = None
                if isinstance(target, str):
                    _target = {
                        "file": target,
                        "regex": DEFAULT_SEMVER_REGEX,
                    }
                elif not isinstance(target, dict):
                    error(
                        f"Invalid type {type(_targets).__name__} for"
                        f" `tool.bump.targets[{i}]` config field",
                        exit=False,
                    )
                    _errored = True
                    continue
                else:
                    if "file" not in target:
                        error(
                            "tool.bump.targets[{i}] must contain a `file` field",
                            exit=False,
                        )
                        _errored = True
                        continue
                    _target = {
                        "regex": target.get(
                            "regex",
                            DEFAULT_PYPROJECT_TOML_SEMVER_REGEX
                            if target["file"] == "pyproject.toml"
                            else DEFAULT_SEMVER_REGEX,
                        ),
                        "file": target["file"],
                    }
                targets.append(_target)
            if _errored:
                sys.exit(1)
        return source, targets
    elif "poetry" not in pyproject_toml.get(
        "tool", {}
    ) or "version" not in pyproject_toml["tool"].get("poetry"):
        error(
            "[tool.bump] version not defined in pyproject.toml"
            " and no `tool.poetry.version` found"
        )

    return (
        {
            "file": "pyproject.toml",
            "regex": DEFAULT_SEMVER_REGEX,
        },
        [{"file": "pyproject.toml", "regex": DEFAULT_PYPROJECT_TOML_SEMVER_REGEX}],
    )


def read_source_version(source):
    with open(source["file"]) as f:
        match = re.search(source["regex"], f.read())
    if match is None:
        regex, file = source["regex"], source["file"]
        error(f"Version not found using regex '{regex}'" f" to search in file {file}")

    version = match.group(0) if not match.groups() else match.group(1)
    is_semver_version_or_error(version)
    return version


def bump_version(version, semver_part):
    major, minor, patch = [int(v) for v in version.split(".")]
    if semver_part == "major":
        major += 1
        minor = 0
        patch = 0
    elif semver_part == "minor":
        minor += 1
        patch = 0
    elif semver_part == "patch":
        patch += 1
    return f"{major}.{minor}.{patch}"


def write_new_version_in_targets(version, targets):
    for target in targets:
        with open(target["file"]) as f:
            previous_content = f.read()
        with open(target["file"], "w") as f:
            try:
                regex = target.get("regex", DEFAULT_SEMVER_REGEX)

                match = re.search(regex, previous_content)
                if 0 <= len(match.groups()) <= 1:
                    # no groups: entire match
                    new_content = re.sub(regex, version, previous_content)
                elif len(match.groups()) == 3:
                    # groups before and after
                    new_content = re.sub(
                        regex, rf"\g<1>{version}\g<3>", previous_content
                    )
                elif len(match.groups()) == 2:
                    if re.match(DEFAULT_SEMVER_REGEX, match.group(1)):
                        # group after
                        new_content = re.sub(
                            regex, rf"{version}\g<2>", previous_content
                        )
                    elif re.match(DEFAULT_SEMVER_REGEX, match.group(2)):
                        # group before
                        new_content = re.sub(
                            regex, rf"\g<1>{version}", previous_content
                        )
                    else:
                        error(
                            f"Version not found using regex '{regex}'"
                            f" to search in file {target['file']}"
                        )
                else:
                    error(
                        f"Too much groups found using regex '{regex}'"
                        f" to search in file {target['file']}"
                    )
            except Exception:
                f.write(previous_content)
                raise
            else:
                f.write(new_content)


def run():
    parser = argparse.ArgumentParser(description="Just bump semantic version.")
    parser.add_argument(
        "semver_part",
        type=str,
        choices=["major", "minor", "patch", "M", "m", "p", "1", "2", "3"],
        help="Bump type",
    )
    args = parser.parse_args()

    source, targets = read_config()
    source_version = read_source_version(source)
    target_version = bump_version(
        source_version,
        SEMVER_PART_ALIASES[args.semver_part],
    )

    write_new_version_in_targets(target_version, targets)
    return 0


def main():
    raise SystemExit(run())


if __name__ == "__main__":
    main()
