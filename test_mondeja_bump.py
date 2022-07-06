try:
    import tomllib
except ImportError:
    import tomli as tomllib

from mondeja_bump import DEFAULT_SEMVER_REGEX, run

import pytest

from contextlib_chdir import chdir


def test_invalid_semver_part(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["w"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "invalid choice: 'w' (choose from" in err


def test_read_config_unexsistent_pyproject_toml(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc, chdir(tmp_path):
        run(["1"])
    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Reading of configuration from another file"
        " than pyproject.toml is not supported\n"
    )


def test_read_config_unparseable_pyproject_toml(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_file.write_text("[invalid")

    with chdir(tmp_path), pytest.raises(tomllib.TOMLDecodeError):
        run(["1"])


def test_missing_tool_bump_nor_poetry_version_in_pyproject_toml(
    tmp_path,
    capsys,
):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_file.write_text('foo = "bar"\n')

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["1"])
    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] `tool.bump` section nor"
        " `tool.poetry.version` found in pyproject.toml\n"
    )


def test_default_source_is_pyproject_toml_semver_regex(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_file.write_text('[tool.poetry]\nversion = "1.2.3"\n')

    with chdir(tmp_path):
        run(["1"])

    assert pyproject_toml_file.read_text() == '[tool.poetry]\nversion = "2.0.0"\n'


def test_multiple_semver_regex_in_pyproject_toml(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = "[tool.poetry]\n" 'version = "1.2.3"\n' 'other = "3.2.1"\n'
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["2"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("1.2.3", "1.3.0")
    )


def test_tool_bump_missing_source(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nfoo = "1.2.3"\nversion="7.8.90"\n\n' "[tool.bump]\n\n"
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["2"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "7.9.0")
    )


def test_tool_bump_string_source_type(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' '[tool.bump]\nsource = "foo.txt"\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    foo_txt_file = tmp_path / "foo.txt"
    foo_txt_content = "foo\nbar\n'1.2.30'\n4.5.6\n"
    foo_txt_file.write_text(foo_txt_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "1.2.31")
    )
    assert foo_txt_file.read_text() == foo_txt_content


def test_tool_bump_invalid_source_type(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_file.write_text("[tool.bump]\nsource = 5\n")

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["1"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Invalid type int for `tool.bump.source`"
        " config field, expected string or object\n"
    )


def test_tool_object_source_type_default_file(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.4"\n\n'
        "[tool.bump]\n"
        'source = {"regex" = "version=\\"(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)"}\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["2"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.4", "7.9.0")
    )

    # regex doesn't matches in target
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.4"\n\n'
        "[tool.bump]\n"
        'source = {regex = "foo=(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)"}\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["2"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        r"[mondeja's-bump] Version not found using regex 'foo=(\d+\.\d+\.\d+)'"
        " to search in file pyproject.toml\n"
    )


def test_invalid_semver_version_in_pyproject_toml(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_file.write_text(
        '[tool.poetry]\nversion = "1.2"\n\n'
        '[tool.bump]\nsource = {regex = "\\\\d+\\\\.\\\\d+"}'
    )

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["1"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] The version '1.2' does not follow semantic versioning!\n"
    )


def test_default_targets(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' '[tool.bump]\nsource = "foo.txt"\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    foo_txt_file = tmp_path / "foo.txt"
    foo_txt_content = "foo\nbar\n'1.2.30'\n4.5.6\n"
    foo_txt_file.write_text(foo_txt_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "1.2.31")
    )
    assert foo_txt_file.read_text() == foo_txt_content


def test_invalid_targets_type(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' "[tool.bump]\ntargets = 1\n"
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["3"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Invalid type int for `tool.bump.targets`"
        " config field, expected list\n"
    )


def test_invalid_target_type(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' '[tool.bump]\ntargets = ["foo.txt", 1]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["3"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Invalid type int for `tool.bump.targets[1]`"
        " config field, expected string or object\n"
    )


def test_target_object_must_contain_file(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n'
        '[tool.bump]\ntargets = ["foo.txt", {regex = "foo"}]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["3"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] tool.bump.targets[1] must contain a `file` field\n"
    )


def test_string_target(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' '[tool.bump]\ntargets = ["foo.txt"]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    foo_txt_file = tmp_path / "foo.txt"
    foo_txt_content = "foo\nbar\n'1.2.30'\n4.5.6\n"
    foo_txt_file.write_text(foo_txt_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (pyproject_toml_content)
    assert foo_txt_file.read_text() == (
        foo_txt_content.replace("1.2.30", "7.8.91").replace("4.5.6", "7.8.91")
    )


def test_object_pyproject_default_regex_target(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n'
        '[tool.bump]\ntargets = [{file = "pyproject.toml"}]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "7.8.91")
    )


def test_object_target(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    regex = '(foo=\\")(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)'
    pyproject_toml_content = (
        '[tool.poetry]\nfoo="7.8.90"\n\n'
        "[tool.bump]\n"
        'source = {file = "pyproject.toml", regex="' + regex + '"}\n'
        "targets = ["
        '{file = "pyproject.toml",'
        ' regex = "' + regex + '"}'
        "]\n"
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "7.8.91")
    )


def test_version_not_found_in_target(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    foo_regex = '(foo=\\")(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)'
    bar_regex = foo_regex.replace("foo", "bar")
    pyproject_toml_content = (
        '[tool.poetry]\nfoo="7.8.90"\n\n'
        "[tool.bump]\n"
        'source = {file = "pyproject.toml", regex="' + foo_regex + '"}\n'
        "targets = ["
        '{file = "pyproject.toml",'
        ' regex = "' + bar_regex + '"}'
        "]\n"
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["3"])

    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Version not found using regex"
        " '(bar=\")(\\d+\\.\\d+\\.\\d+)' to search in file pyproject.toml\n"
    )


def test_unexistent_source_file(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n' '[tool.bump]\nsource = "foobarbaz.txt"\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(FileNotFoundError) as exc:
        run(["3"])

    assert exc.value.filename == "foobarbaz.txt"


def test_unexistent_target_file(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        '[tool.poetry]\nversion="7.8.90"\n\n'
        '[tool.bump]\ntargets = ["foobarbaz.txt"]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(FileNotFoundError) as exc:
        run(["3"])

    assert exc.value.filename == "foobarbaz.txt"


def test_target_regex_too_much_groups(tmp_path, capsys):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        "[tool.poetry]\nversion='7.8.90'\n\n"
        "[tool.bump]\ntargets = ["
        '{file = "pyproject.toml",'
        " regex = \"([^'])(')(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)(')\"}]\n"
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path), pytest.raises(SystemExit) as exc:
        run(["3"])
    assert exc.value.code == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "[mondeja's-bump] Too much groups found using regex"
        r" '([^'])(')(\d+\.\d+\.\d+)(')'"
        " to search in file pyproject.toml\n"
    )


def test_target_regex_two_groups_group_before(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        "[tool.poetry]\nversion='7.8.90'\n\n"
        "[tool.bump]\ntargets = ["
        '{file = "pyproject.toml",'
        ' regex = "(\')(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)"}]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "7.8.91")
    )


def test_target_regex_two_groups_group_after(tmp_path):
    pyproject_toml_file = tmp_path / "pyproject.toml"
    pyproject_toml_content = (
        "[tool.poetry]\nversion='7.8.90'\n\n"
        "[tool.bump]\ntargets = ["
        '{file = "pyproject.toml",'
        ' regex = "(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)(\')"}]\n'
    )
    pyproject_toml_file.write_text(pyproject_toml_content)

    with chdir(tmp_path):
        run(["3"])

    assert pyproject_toml_file.read_text() == (
        pyproject_toml_content.replace("7.8.90", "7.8.91")
    )
