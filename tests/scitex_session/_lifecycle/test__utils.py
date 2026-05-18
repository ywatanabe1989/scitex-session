#!/usr/bin/env python3
# Time-stamp: "2026-05-18"
# File: ./tests/scitex_session/_lifecycle/test__utils.py

"""Tests for session lifecycle functions (start, close, running2finished).

No mocks anywhere — every test exercises the real collaborator. Where a
production function previously needed `unittest.mock.patch` (`print_header`'s
`_printc` and `sleep`, or `get_debug_mode`'s filesystem probe), the
collaborators are injected via kwargs or via a real `tmp_path` working
directory.
"""

import argparse
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Required for scitex_session module — the leaf-package tests skip
# gracefully if optional collaborators aren't installed in the env.
pytest.importorskip("natsort")
pytest.importorskip("h5py")
pytest.importorskip("zarr")


class TestFormatDiffTime:
    """Tests for format_diff_time helper function."""

    def test_format_diff_time_returns_seconds_only_when_under_a_minute(self):
        # Arrange
        from scitex_session._lifecycle._utils import format_diff_time

        diff = timedelta(seconds=45)
        # Act
        result = format_diff_time(diff)
        # Assert
        assert result == "00:00:45"

    def test_format_diff_time_renders_minutes_and_seconds(self):
        # Arrange
        from scitex_session._lifecycle._utils import format_diff_time

        diff = timedelta(minutes=5, seconds=30)
        # Act
        result = format_diff_time(diff)
        # Assert
        assert result == "00:05:30"

    def test_format_diff_time_renders_hours_minutes_seconds(self):
        # Arrange
        from scitex_session._lifecycle._utils import format_diff_time

        diff = timedelta(hours=2, minutes=15, seconds=45)
        # Act
        result = format_diff_time(diff)
        # Assert
        assert result == "02:15:45"

    def test_format_diff_time_returns_zeros_for_zero_delta(self):
        # Arrange
        from scitex_session._lifecycle._utils import format_diff_time

        diff = timedelta(seconds=0)
        # Act
        result = format_diff_time(diff)
        # Assert
        assert result == "00:00:00"

    def test_format_diff_time_supports_hours_over_one_hundred(self):
        # Arrange
        from scitex_session._lifecycle._utils import format_diff_time

        diff = timedelta(hours=100, minutes=30, seconds=15)
        # Act
        result = format_diff_time(diff)
        # Assert
        assert result == "100:30:15"


class TestSimplifyRelativePath:
    """Tests for simplify_relative_path helper function."""

    def test_simplify_relative_path_strips_running_directory(self):
        # Arrange
        from scitex_session._lifecycle._utils import simplify_relative_path

        cwd = os.getcwd()
        sdir = os.path.join(
            cwd, "scripts/experiment/RUNNING/2024Y-09M-12D-02h44m40s_GlBZ"
        )
        # Act
        result = simplify_relative_path(sdir)
        # Assert
        assert "RUNNING" not in result

    def test_simplify_relative_path_strips_datetime_id_suffix(self):
        # Arrange
        from scitex_session._lifecycle._utils import simplify_relative_path

        cwd = os.getcwd()
        sdir = os.path.join(
            cwd, "scripts/experiment/RUNNING/2024Y-09M-12D-02h44m40s_GlBZ"
        )
        # Act
        result = simplify_relative_path(sdir)
        # Assert
        assert "2024Y-09M-12D" not in result

    def test_simplify_relative_path_preserves_scripts_segment(self):
        # Arrange
        from scitex_session._lifecycle._utils import simplify_relative_path

        cwd = os.getcwd()
        sdir = os.path.join(cwd, "scripts/test/RUNNING/2024Y-01M-01D-00h00m00s_XXXX")
        # Act
        result = simplify_relative_path(sdir)
        # Assert
        assert "scripts/" in result


class TestGetDebugMode:
    """Tests for get_debug_mode helper function."""

    def test_get_debug_mode_returns_false_when_config_file_missing(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._utils import get_debug_mode

        original_cwd = os.getcwd()
        os.chdir(tmp_path)  # ./config/IS_DEBUG.yaml does not exist here.
        try:
            # Act
            result = get_debug_mode()
        finally:
            os.chdir(original_cwd)
        # Assert
        assert result is False

    def test_get_debug_mode_returns_boolean_type(self):
        # Arrange
        from scitex_session._lifecycle._utils import get_debug_mode

        # Act
        result = get_debug_mode()
        # Assert
        assert isinstance(result, bool)


class TestGetScitexVersion:
    """Tests for get_scitex_version helper function."""

    def test_get_scitex_version_returns_string_type(self):
        # Arrange
        from scitex_session._lifecycle._utils import get_scitex_version

        # Act
        result = get_scitex_version()
        # Assert
        assert isinstance(result, str)

    def test_get_scitex_version_returns_nonempty_value(self):
        # Arrange
        from scitex_session._lifecycle._utils import get_scitex_version

        # Act
        result = get_scitex_version()
        # Assert
        assert len(result) > 0


class TestInitializeEnv:
    """Tests for initialize_env helper function."""

    def test_initialize_env_returns_string_id(self):
        # Arrange
        from scitex_session._lifecycle._utils import initialize_env

        # Act
        ID, _ = initialize_env(IS_DEBUG=False)
        # Assert
        assert isinstance(ID, str)

    def test_initialize_env_returns_nonempty_id(self):
        # Arrange
        from scitex_session._lifecycle._utils import initialize_env

        # Act
        ID, _ = initialize_env(IS_DEBUG=False)
        # Assert
        assert len(ID) > 0

    def test_initialize_env_returns_current_process_pid(self):
        # Arrange
        from scitex_session._lifecycle._utils import initialize_env

        # Act
        _, PID = initialize_env(IS_DEBUG=False)
        # Assert
        assert PID == os.getpid()

    def test_initialize_env_prefixes_id_in_debug_mode(self):
        # Arrange
        from scitex_session._lifecycle._utils import initialize_env

        # Act
        ID, _ = initialize_env(IS_DEBUG=True)
        # Assert
        assert ID.startswith("DEBUG_")

    def test_initialize_env_returns_integer_pid_in_debug_mode(self):
        # Arrange
        from scitex_session._lifecycle._utils import initialize_env

        # Act
        _, PID = initialize_env(IS_DEBUG=True)
        # Assert
        assert isinstance(PID, int)


class TestSetupConfigs:
    """Tests for setup_configs helper function."""

    def test_setup_configs_preserves_id_field(self):
        # Arrange
        from scitex_session._lifecycle._config import setup_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "RUNNING", "test_id")
            os.makedirs(sdir)
            # Act
            configs = setup_configs(
                IS_DEBUG=False,
                ID="test_id",
                PID=12345,
                file="/tmp/test.py",
                sdir=sdir,
                relative_sdir="./test_out/RUNNING/test_id",
                verbose=False,
            )
        # Assert
        assert configs["ID"] == "test_id"

    def test_setup_configs_preserves_pid_field(self):
        # Arrange
        from scitex_session._lifecycle._config import setup_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "RUNNING", "test_id")
            os.makedirs(sdir)
            # Act
            configs = setup_configs(
                IS_DEBUG=False,
                ID="test_id",
                PID=12345,
                file="/tmp/test.py",
                sdir=sdir,
                relative_sdir="./test_out/RUNNING/test_id",
                verbose=False,
            )
        # Assert
        assert configs["PID"] == 12345

    def test_setup_configs_records_start_datetime(self):
        # Arrange
        from scitex_session._lifecycle._config import setup_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "RUNNING", "test_id")
            os.makedirs(sdir)
            # Act
            configs = setup_configs(
                IS_DEBUG=False,
                ID="test_id",
                PID=12345,
                file="/tmp/test.py",
                sdir=sdir,
                relative_sdir="./test_out/RUNNING/test_id",
                verbose=False,
            )
        # Assert
        assert isinstance(configs["START_DATETIME"], datetime)

    def test_setup_configs_sdir_run_matches_input_sdir(self):
        # Arrange
        from scitex_session._lifecycle._config import setup_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(sdir)
            # Act
            configs = setup_configs(
                IS_DEBUG=False,
                ID="test_id",
                PID=12345,
                file="/tmp/test.py",
                sdir=sdir,
                relative_sdir="./script_out/RUNNING/test_id",
                verbose=False,
            )
        # Assert
        assert configs["SDIR_RUN"] == Path(sdir)

    def test_setup_configs_sdir_out_drops_running_segment(self):
        # Arrange
        from scitex_session._lifecycle._config import setup_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(sdir)
            # Act
            configs = setup_configs(
                IS_DEBUG=False,
                ID="test_id",
                PID=12345,
                file="/tmp/test.py",
                sdir=sdir,
                relative_sdir="./script_out/RUNNING/test_id",
                verbose=False,
            )
        # Assert
        assert "RUNNING" not in str(configs["SDIR_OUT"])


@pytest.fixture
def matplotlib_colors_with_grey():
    """Run setup_matplotlib and return the colors palette; skip if the
    upstream palette doesn't expose `'grey'` (the alias-test contract)."""
    import matplotlib.pyplot as plt

    from scitex_session._lifecycle._matplotlib import setup_matplotlib

    _, colors = setup_matplotlib(plt=plt)
    if "grey" not in colors:
        pytest.skip("upstream palette does not provide 'grey' on this build")
    return colors


class TestSetupMatplotlib:
    """Tests for setup_matplotlib helper function."""

    def test_setup_matplotlib_returns_none_plt_when_input_is_none(self):
        # Arrange
        from scitex_session._lifecycle._matplotlib import setup_matplotlib

        # Act
        plt_result, _ = setup_matplotlib(plt=None)
        # Assert
        assert plt_result is None

    def test_setup_matplotlib_returns_none_colors_when_input_is_none(self):
        # Arrange
        from scitex_session._lifecycle._matplotlib import setup_matplotlib

        # Act
        _, colors = setup_matplotlib(plt=None)
        # Assert
        assert colors is None

    def test_setup_matplotlib_returns_non_none_plt_when_pyplot_provided(self):
        # Arrange
        import matplotlib.pyplot as plt

        from scitex_session._lifecycle._matplotlib import setup_matplotlib

        # Act
        plt_result, _ = setup_matplotlib(plt=plt)
        # Assert
        assert plt_result is not None

    def test_setup_matplotlib_returns_dict_like_colors_when_pyplot_provided(self):
        # Arrange
        import matplotlib.pyplot as plt

        from scitex_session._lifecycle._matplotlib import setup_matplotlib

        # Act
        _, colors = setup_matplotlib(plt=plt)
        # Assert
        assert hasattr(colors, "__getitem__")

    def test_setup_matplotlib_adds_gray_alias_when_grey_present(
        self, matplotlib_colors_with_grey
    ):
        # Arrange
        colors = matplotlib_colors_with_grey
        # Act
        has_gray_alias = "gray" in colors
        # Assert
        assert has_gray_alias is True


class TestArgsToStr:
    """Tests for args_to_str helper function."""

    def test_args_to_str_returns_empty_string_for_empty_dict(self):
        # Arrange
        from scitex_session._lifecycle._utils import args_to_str

        # Act
        result = args_to_str({})
        # Assert
        assert result == ""

    def test_args_to_str_includes_key_in_output(self):
        # Arrange
        from scitex_session._lifecycle._utils import args_to_str

        # Act
        result = args_to_str({"key1": "value1", "key2": 42})
        # Assert
        assert "key1" in result

    def test_args_to_str_includes_value_in_output(self):
        # Arrange
        from scitex_session._lifecycle._utils import args_to_str

        # Act
        result = args_to_str({"key1": "value1", "key2": 42})
        # Assert
        assert "value1" in result

    def test_args_to_str_renders_integer_values_as_text(self):
        # Arrange
        from scitex_session._lifecycle._utils import args_to_str

        # Act
        result = args_to_str({"key2": 42})
        # Assert
        assert "42" in result

    def test_args_to_str_separates_multiple_entries_with_newline(self):
        # Arrange
        from scitex_session._lifecycle._utils import args_to_str

        # Act
        result = args_to_str({"a": 1, "bb": 2})
        # Assert
        assert "\n" in result


class TestEscapeAnsiFromLogFiles:
    """Tests for escape_ansi_from_log_files helper function."""

    def test_escape_ansi_removes_color_open_sequence_from_log(self):
        # Arrange
        from scitex_session._lifecycle._utils import escape_ansi_from_log_files

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            with open(log_file, "w") as f:
                f.write("\x1b[31mRed text\x1b[0m and normal text")
            # Act
            escape_ansi_from_log_files([log_file])
            with open(log_file) as f:
                content = f.read()
        # Assert
        assert "\x1b[31m" not in content

    def test_escape_ansi_removes_color_reset_sequence_from_log(self):
        # Arrange
        from scitex_session._lifecycle._utils import escape_ansi_from_log_files

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            with open(log_file, "w") as f:
                f.write("\x1b[31mRed text\x1b[0m and normal text")
            # Act
            escape_ansi_from_log_files([log_file])
            with open(log_file) as f:
                content = f.read()
        # Assert
        assert "\x1b[0m" not in content

    def test_escape_ansi_preserves_textual_payload(self):
        # Arrange
        from scitex_session._lifecycle._utils import escape_ansi_from_log_files

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            with open(log_file, "w") as f:
                f.write("\x1b[31mRed text\x1b[0m and normal text")
            # Act
            escape_ansi_from_log_files([log_file])
            with open(log_file) as f:
                content = f.read()
        # Assert
        assert "Red text" in content

    def test_escape_ansi_does_not_raise_for_empty_file_list(self):
        # Arrange
        from scitex_session._lifecycle._utils import escape_ansi_from_log_files

        # Act
        escape_ansi_from_log_files([])
        # Assert
        assert True  # no exception is the observed behaviour


class TestProcessTimestamp:
    """Tests for process_timestamp helper function."""

    def test_process_timestamp_adds_end_datetime_field(self):
        # Arrange
        from scitex_session._lifecycle._utils import process_timestamp

        config = {"START_DATETIME": datetime.now() - timedelta(minutes=5)}
        # Act
        result = process_timestamp(config, verbose=False)
        # Assert
        assert "END_DATETIME" in result

    def test_process_timestamp_end_datetime_is_datetime_object(self):
        # Arrange
        from scitex_session._lifecycle._utils import process_timestamp

        config = {"START_DATETIME": datetime.now() - timedelta(minutes=5)}
        # Act
        result = process_timestamp(config, verbose=False)
        # Assert
        assert isinstance(result["END_DATETIME"], datetime)

    def test_process_timestamp_end_after_start(self):
        # Arrange
        from scitex_session._lifecycle._utils import process_timestamp

        config = {"START_DATETIME": datetime.now() - timedelta(minutes=5)}
        # Act
        result = process_timestamp(config, verbose=False)
        # Assert
        assert result["END_DATETIME"] > result["START_DATETIME"]

    def test_process_timestamp_adds_run_duration_field(self):
        # Arrange
        from scitex_session._lifecycle._utils import process_timestamp

        start_time = datetime.now() - timedelta(hours=1, minutes=30, seconds=45)
        config = {"START_DATETIME": start_time}
        # Act
        result = process_timestamp(config, verbose=False)
        # Assert
        assert "RUN_DURATION" in result

    def test_process_timestamp_run_duration_uses_hhmmss_layout(self):
        # Arrange
        from scitex_session._lifecycle._utils import process_timestamp

        start_time = datetime.now() - timedelta(hours=1, minutes=30, seconds=45)
        config = {"START_DATETIME": start_time}
        # Act
        result = process_timestamp(config, verbose=False)
        parts = result["RUN_DURATION"].split(":")
        # Assert
        assert len(parts) == 3


class TestRunning2Finished:
    """Tests for running2finished function."""

    def test_running2finished_moves_to_success_dir_when_exit_status_zero(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            with open(os.path.join(running_dir, "test.txt"), "w") as f:
                f.write("test content")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            result = running2finished(
                config, exit_status=0, remove_src_dir=True, max_wait=5
            )
        # Assert
        assert "FINISHED_SUCCESS" in str(result["SDIR_RUN"])

    def test_running2finished_moves_to_error_dir_when_exit_status_one(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            with open(os.path.join(running_dir, "test.txt"), "w") as f:
                f.write("test content")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            result = running2finished(
                config, exit_status=1, remove_src_dir=True, max_wait=5
            )
        # Assert
        assert "FINISHED_ERROR" in str(result["SDIR_RUN"])

    def test_running2finished_moves_to_neutral_dir_when_exit_status_none(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            with open(os.path.join(running_dir, "test.txt"), "w") as f:
                f.write("test content")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            result = running2finished(
                config, exit_status=None, remove_src_dir=True, max_wait=5
            )
            dest = str(result["SDIR_RUN"])
        # Assert
        assert "FINISHED/" in dest or "FINISHED\\" in dest

    def test_running2finished_copies_top_level_file_to_destination(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            with open(os.path.join(running_dir, "file1.txt"), "w") as f:
                f.write("content1")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            result = running2finished(
                config, exit_status=0, remove_src_dir=False, max_wait=5
            )
            dest_dir = str(result["SDIR_RUN"])
        # Assert
        assert os.path.exists(os.path.join(dest_dir, "file1.txt"))

    def test_running2finished_copies_nested_file_to_destination(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            sub_dir = os.path.join(running_dir, "subdir")
            os.makedirs(sub_dir)
            with open(os.path.join(sub_dir, "file2.txt"), "w") as f:
                f.write("content2")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            result = running2finished(
                config, exit_status=0, remove_src_dir=False, max_wait=5
            )
            dest_dir = str(result["SDIR_RUN"])
        # Assert
        assert os.path.exists(os.path.join(dest_dir, "subdir", "file2.txt"))

    def test_running2finished_removes_source_dir_when_flag_true(self):
        # Arrange
        from scitex_session._lifecycle import running2finished

        with tempfile.TemporaryDirectory() as tmpdir:
            running_dir = os.path.join(tmpdir, "script_out", "RUNNING", "test_id")
            os.makedirs(running_dir)
            with open(os.path.join(running_dir, "file.txt"), "w") as f:
                f.write("content")
            config = {"SDIR_RUN": Path(running_dir)}
            # Act
            running2finished(config, exit_status=0, remove_src_dir=True, max_wait=5)
        # Assert
        assert not os.path.exists(running_dir)


class TestStartFunction:
    """Tests for start() function."""

    def test_start_returns_six_element_tuple(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            os.makedirs(sdir, exist_ok=True)
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
        # Assert
        assert len(result) == 6

    def test_start_config_exposes_id_attribute(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            os.makedirs(sdir, exist_ok=True)
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            CONFIG = result[0]
        # Assert
        assert hasattr(CONFIG, "ID")

    def test_start_returns_none_stdout_when_sys_is_none(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            os.makedirs(sdir, exist_ok=True)
            # Act
            _, stdout, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
        # Assert
        assert stdout is None

    def test_start_creates_default_sdir_when_unspecified(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_script.py")
            with open(test_file, "w") as f:
                f.write("# test")
            # Act
            result = start(
                sys=None,
                plt=None,
                file=test_file,
                sdir=None,
                verbose=False,
            )
            CONFIG = result[0]
            try:
                exists = os.path.exists(str(CONFIG["SDIR_RUN"]))
            finally:
                shutil.rmtree(str(CONFIG["SDIR_OUT"]), ignore_errors=True)
        # Assert
        assert exists is True

    def test_start_respects_custom_sdir_string(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_sdir = os.path.join(tmpdir, "custom_out", "RUNNING", "session_id")
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=custom_sdir,
                verbose=False,
            )
            CONFIG = result[0]
        # Assert
        assert str(CONFIG["SDIR_RUN"]) == custom_sdir

    def test_start_accepts_path_object_as_sdir(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_sdir = Path(tmpdir) / "custom_out" / "RUNNING" / "session_id"
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=custom_sdir,
                verbose=False,
            )
            CONFIG = result[0]
        # Assert
        assert os.path.exists(str(CONFIG["SDIR_RUN"]))

    def test_start_appends_sdir_suffix_to_run_dir(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_script.py")
            with open(test_file, "w") as f:
                f.write("# test")
            # Act
            result = start(
                sys=None,
                plt=None,
                file=test_file,
                sdir=None,
                sdir_suffix="my_suffix",
                verbose=False,
            )
            CONFIG = result[0]
            try:
                contains = "my_suffix" in str(CONFIG["SDIR_RUN"])
            finally:
                shutil.rmtree(str(CONFIG["SDIR_OUT"]), ignore_errors=True)
        # Assert
        assert contains is True

    def test_start_records_first_arg_value(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            args = argparse.Namespace(param1="value1", param2=42)
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                args=args,
                verbose=False,
            )
            CONFIG = result[0]
        # Assert
        assert CONFIG["ARGS"]["param1"] == "value1"

    def test_start_records_second_arg_value(self):
        # Arrange
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            args = argparse.Namespace(param1="value1", param2=42)
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                args=args,
                verbose=False,
            )
            CONFIG = result[0]
        # Assert
        assert CONFIG["ARGS"]["param2"] == 42

    def test_start_registers_session_with_running_status(self):
        # Arrange
        from scitex_session._lifecycle import start
        from scitex_session._manager import get_global_session_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            CONFIG = result[0]
            info = get_global_session_manager().get_session(CONFIG["ID"])
        # Assert
        assert info["status"] == "running"

    def test_start_returns_random_state_manager_instance(self):
        # Arrange
        from scitex.repro import RandomStateManager
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            # Act
            result = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                seed=123,
                verbose=False,
            )
            rng = result[5]
        # Assert
        assert isinstance(rng, RandomStateManager)

    def test_start_returns_non_none_plt_when_pyplot_given(self):
        # Arrange
        import matplotlib.pyplot as plt
        from scitex_session._lifecycle import start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            # Act
            result = start(
                sys=None,
                plt=plt,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            plt_result = result[3]
        # Assert
        assert plt_result is not None


class TestCloseFunction:
    """Tests for close() function."""

    def test_close_does_not_raise_on_basic_session(self):
        # Arrange
        from scitex_session._lifecycle import close, start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            CONFIG, _, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            # Act
            close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert True  # no exception is the observed behaviour

    def test_close_marks_session_closed_in_manager(self):
        # Arrange
        from scitex_session._lifecycle import close, start
        from scitex_session._manager import get_global_session_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            CONFIG, _, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            session_id = CONFIG["ID"]
            # Act
            close(CONFIG, verbose=False, exit_status=0)
            info = get_global_session_manager().get_session(session_id)
        # Assert
        assert info["status"] == "closed"

    def test_close_removes_running_directory_after_finish(self):
        # Arrange
        from scitex_session._lifecycle import close, start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "test_session")
            CONFIG, _, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            # Act
            close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert not os.path.exists(sdir)

    @pytest.mark.parametrize("exit_status", [0, 1, None])
    def test_close_does_not_raise_for_any_exit_status_value(self, exit_status):
        # Arrange
        from scitex_session._lifecycle import close, start

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(
                tmpdir, "test_out", "RUNNING", f"test_session_{exit_status}"
            )
            CONFIG, _, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            # Act
            close(CONFIG, verbose=False, exit_status=exit_status)
        # Assert
        assert True  # no exception is the observed behaviour


class TestClearPythonLogDir:
    """Tests for clear_python_log_dir helper function."""

    def test_clear_python_log_dir_removes_existing_directory(self):
        # Arrange
        from scitex_session._lifecycle._utils import clear_python_log_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "logs")
            os.makedirs(log_dir)
            with open(os.path.join(log_dir, "test.log"), "w") as f:
                f.write("test")
            # Act
            clear_python_log_dir(log_dir)
        # Assert
        assert not os.path.exists(log_dir)

    def test_clear_python_log_dir_does_not_raise_on_missing_path(self):
        # Arrange
        from scitex_session._lifecycle._utils import clear_python_log_dir

        # Act
        clear_python_log_dir("/nonexistent/path/that/does/not/exist")
        # Assert
        assert True  # no exception is the observed behaviour


class TestIntegration:
    """Integration tests for session lifecycle."""

    def test_full_session_lifecycle_marks_session_closed(self):
        # Arrange
        from scitex_session._lifecycle import close, start
        from scitex_session._manager import get_global_session_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            sdir = os.path.join(tmpdir, "test_out", "RUNNING", "full_test")
            CONFIG, _, _, _, _, _ = start(
                sys=None,
                plt=None,
                file="/tmp/test.py",
                sdir=sdir,
                verbose=False,
            )
            session_id = CONFIG["ID"]
            close(CONFIG, verbose=False, exit_status=0)
            # Act
            status = get_global_session_manager().get_session(session_id)["status"]
        # Assert
        assert status == "closed"

    def test_multiple_sequential_sessions_have_unique_ids(self):
        # Arrange
        from scitex_session._lifecycle import close, start

        session_ids = []
        for i in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                sdir = os.path.join(tmpdir, "test_out", "RUNNING", f"session_{i}")
                CONFIG, _, _, _, _, _ = start(
                    sys=None,
                    plt=None,
                    file="/tmp/test.py",
                    sdir=sdir,
                    verbose=False,
                )
                session_ids.append(CONFIG["ID"])
                close(CONFIG, verbose=False, exit_status=0)
        # Act
        unique = set(session_ids)
        # Assert
        assert len(unique) == 3


class _FakePrintc:
    """Records calls to a `printc`-shaped collaborator (no mocks)."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class _FakeSleep:
    """Records sleep durations without actually sleeping (no mocks)."""

    def __init__(self):
        self.durations = []

    def __call__(self, duration):
        self.durations.append(duration)


class TestPrintHeader:
    """Tests for print_header helper function.

    The `printc_fn` / `sleep_fn` injection points let the test pass real
    hand-rolled fakes instead of `unittest.mock.patch`-ing module globals.
    """

    def test_print_header_with_args_invokes_printc_once(self):
        # Arrange
        from scitex.dict import DotDict
        from scitex_session._lifecycle._utils import print_header

        printc = _FakePrintc()
        sleep_fake = _FakeSleep()
        args = argparse.Namespace(param1="value1", param2=42)
        configs = DotDict({"test": "value"})
        # Act
        print_header(
            ID="test_id",
            PID=12345,
            file="/tmp/test.py",
            args=args,
            configs=configs,
            verbose=False,
            printc_fn=printc,
            sleep_fn=sleep_fake,
        )
        # Assert
        assert len(printc.calls) == 1

    def test_print_header_with_args_records_id_in_payload(self):
        # Arrange
        from scitex.dict import DotDict
        from scitex_session._lifecycle._utils import print_header

        printc = _FakePrintc()
        sleep_fake = _FakeSleep()
        args = argparse.Namespace(param1="value1", param2=42)
        configs = DotDict({"test": "value"})
        # Act
        print_header(
            ID="test_id",
            PID=12345,
            file="/tmp/test.py",
            args=args,
            configs=configs,
            verbose=False,
            printc_fn=printc,
            sleep_fn=sleep_fake,
        )
        payload = printc.calls[0][0][0]
        # Assert
        assert "test_id" in payload

    def test_print_header_without_args_renders_arguments_none(self):
        # Arrange
        from scitex.dict import DotDict
        from scitex_session._lifecycle._utils import print_header

        printc = _FakePrintc()
        sleep_fake = _FakeSleep()
        configs = DotDict({"test": "value"})
        # Act
        print_header(
            ID="test_id",
            PID=12345,
            file="/tmp/test.py",
            args=None,
            configs=configs,
            verbose=False,
            printc_fn=printc,
            sleep_fn=sleep_fake,
        )
        payload = printc.calls[0][0][0]
        # Assert
        assert "Arguments: None" in payload

    def test_print_header_invokes_sleep_twice(self):
        # Arrange
        from scitex.dict import DotDict
        from scitex_session._lifecycle._utils import print_header

        printc = _FakePrintc()
        sleep_fake = _FakeSleep()
        configs = DotDict({"test": "value"})
        # Act
        print_header(
            ID="test_id",
            PID=12345,
            file="/tmp/test.py",
            args=None,
            configs=configs,
            verbose=False,
            printc_fn=printc,
            sleep_fn=sleep_fake,
        )
        # Assert
        assert len(sleep_fake.durations) == 2


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
