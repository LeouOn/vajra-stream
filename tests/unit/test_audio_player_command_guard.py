import inspect
import os
import pathlib

import pytest

from tests import conftest


@pytest.mark.parametrize(
    "cmd",
    [
        "aplay audio.wav",
        "  aplay audio.wav  ",
        "/usr/bin/aplay audio.wav",
        "/usr/local/bin/paplay test.wav",
        "afplay song.aiff",
        "ffplay -nodisp -autoexit sound.wav",
    ],
)
def test_is_audio_player_command_bare_and_absolute(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        '"/usr/bin/aplay" file.wav',
        "'aplay' file.wav",
        '"ffplay" -nodisp sound.wav',
        "'paplay' /tmp/test.wav",
        "   \"/opt/audio/bin/afplay\" 'test audio.aiff'   ",
    ],
)
def test_is_audio_player_command_quoted(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        "AUDIODEV=hw:0,0 aplay file.wav",
        "VAR1=1 VAR2=2 aplay file.wav",
        'VAR1=1 VAR2="foo bar" aplay file.wav',
        "X=1 Y=2 /usr/bin/afplay audio.aiff",
        "AUDIODEV=default 'ffplay' sound.wav",
        "ALSA_CARD=0 'paplay' song.wav",
    ],
)
def test_is_audio_player_command_env_assignments(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # A WHOLE word written in quotes is a command name to the shell, not an
        # assignment. shlex.split discards the quoting, so these arrive at the
        # assignment loop looking exactly like real assignments. Ground truth
        # under sh -c: exit 127, "AUDIODEV=x: command not found", and the
        # player never runs — so True here would be a false swallow.
        '"AUDIODEV=x" aplay f.wav',
        "'AUDIODEV=x' aplay f.wav",
        # Partially quoted: the token is still one shell word that is not an
        # assignment word, because the first character is a quote.
        '"AUDIODEV=x"y aplay f.wav',
        "'AUDIODEV=x'y aplay f.wav",
        # After a genuine leading assignment the loop must still stop here.
        'VAR1=1 "AUDIODEV=x" aplay f.wav',
        # Same rule after nohup, which does not parse assignments at all.
        'nohup "AUDIODEV=x" aplay f.wav',
        'env nohup "A=x" aplay f.wav',
        'AUDIODEV=x nohup "A=y" aplay f.wav',
    ],
)
def test_is_audio_player_command_quoted_whole_token_is_not_an_assignment(cmd: str) -> None:
    """A quoted whole word is an executable name, so no player ever runs."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # A quote or backslash ANYWHERE IN THE NAME PART makes the word a
        # command name, not an assignment — the first character being a quote
        # is only the obvious case. The shell requires the text before the
        # first '=' to be an entirely unquoted, unescaped identifier, so all of
        # these exit 127 and never launch a player. Ground truth under sh -c:
        # "AUDIODEV=x: command not found" (or AUDIODEV=xy for the partial ones).
        'AUDIO"DEV"=x aplay f.wav',
        "AUDIO'DEV'=x aplay f.wav",
        r"AUDIO\DEV=x aplay f.wav",
        r"\AUDIODEV=x aplay f.wav",
        'VAR1=1 AUDIO"DEV"=x aplay f.wav',
        'A"B"=x aplay f.wav',
        # Already covered above, repeated here so the whole name-part class
        # lives in one pin: quote at the front but not the whole word.
        '"AUDIO"DEV=x aplay f.wav',
        # Not a leading position, but nohup does not parse assignments either.
        r"nohup AUDIO\DEV=x aplay f.wav",
        'env nohup A"B"=x aplay f.wav',
    ],
)
def test_is_audio_player_command_quoted_or_escaped_name_is_not_an_assignment(cmd: str) -> None:
    """A quote or backslash in the NAME part makes the word a command name."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Controls: the VALUE may contain quotes and escapes freely, because
        # only the text before the first '=' decides assignment-vs-command.
        'AUDIODEV="x" aplay f.wav',
        "AUDIODEV='x y' aplay f.wav",
        r"AUDIODEV=\x aplay f.wav",
        "AUDIODEV=x aplay f.wav",
        'VAR1=1 AUDIODEV="hw:0,0" aplay file.wav',
        r"VAR1=1 AUDIODEV=\x nohup aplay f.wav",
        'A="foo bar" aplay f.wav',
    ],
)
def test_is_audio_player_command_plain_name_with_any_value_is_an_assignment(cmd: str) -> None:
    """Only the name part is restricted; the value may be quoted or escaped."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # Shape, not quoting: the shell also rejects a name that cannot be an
        # identifier, so the whole word is a command name and nothing launches.
        # Ground truth under sh -c: exit 127, "1A=x: command not found".
        "1A=x aplay f.wav",
        "=x aplay f.wav",
        "1A=1 apLAY f.wav",
        r"1A=x AUDIODEV=\"q\" aplay f.wav",
    ],
)
def test_is_audio_player_command_non_identifier_name_is_not_an_assignment(cmd: str) -> None:
    """A name that cannot be an identifier is a command name, not an assignment."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # An escaped double quote INSIDE a double-quoted value: shlex's
        # escapedquotes is '"', so \" is an escaped quote and the value
        # continues. A splitter that treats it as the closing delimiter drifts
        # out of alignment and then applies assignment flags to the wrong word.
        # Ground truth under sh -c: "C=q" is a quoted COMMAND word, so sh
        # exits 127 and nothing launches. All of these must be False.
        'A="x\\" B=z" "C=q" aplay f.wav',
        'A="x\\"\tB=z" "C=q" aplay f.wav',
        'A="x\\"   B=z" "C=q" aplay f.wav',
        'P=1 A="x\\" B=z" "C=q" aplay f.wav',
        'A="x\\" B=z" "C=q" nohup aplay f.wav',
        'A="x\\" B=z" AUDIO"DEV"=q aplay f.wav',
        # Same family: the shell expands an unset $AUDIODEV to empty (POSIX
        # behaviour; identical under bash and dash), leaving the word '=x',
        # an invalid assignment, so the shell exits 127. The helper agrees
        # because '$' is not part of an identifier.
        "$AUDIODEV=x aplay f.wav",
        # nohup does not parse assignments: it tries to execute 'A=x'.
        "nohup A=x aplay f.wav",
        # Same family, my own additions: an escaped quote followed by a real
        # quoted word in several positions.
        'A="x\\"y" "C=q" aplay f.wav',
        'A=\\"q" "C=q" aplay f.wav',
        'A="q\\"" "C=q" aplay f.wav',
        'V="a\\"b" W="c d" "C=q" aplay f.wav',
        # A backslash inside double quotes that is NOT before '"' or '\\' stays
        # literal (shlex escapedquotes), so the value keeps the backslash and
        # the following quoted word is still a command word.
        'A="x\\y z" "C=q" aplay f.wav',
        'A="x\\$y z" "C=q" aplay f.wav',
        'A="x\\\\" "C=q" aplay f.wav',
        # Single quotes: a backslash is literal and the next ' closes the word,
        # so the remainder becomes separate words and "C=q" is a command.
        "A='x\\' \"C=q\" aplay f.wav",
    ],
)
def test_is_audio_player_command_escaped_quote_inside_value_keeps_alignment(cmd: str) -> None:
    """An escaped quote inside a value must not desync the raw split from shlex."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Controls for the same family: a single assignment whose value contains
        # whitespace and an escaped quote is still one assignment, and the
        # player does launch.
        'A="x\\" B=z" aplay f.wav',
        'A="x\\" B=z" C=q aplay f.wav',
        'A="x\\"y" aplay f.wav',
        'A="x y" aplay f.wav',
        'A="x\\" B=z" env "C=q" aplay f.wav',
        'X="1 2" env A=x aplay f.wav',
        "A=\"1\" B='2' C=3 aplay f.wav",
        "A='x\"y' aplay f.wav",
        'A="x\'y" aplay f.wav',
        "A=x\\ y aplay f.wav",
        "A= aplay f.wav",
        "A== aplay f.wav",
        'A="" aplay f.wav',
        # $ is literal to both shlex and this splitter (shlex does no
        # expansion), and the name part keeps it, so a $-word is NOT a
        # plain identifier and the shell fails to resolve it.
        "A=$HOME aplay f.wav",
        'A="$HOME" aplay f.wav',
        "A='$HOME' aplay f.wav",
        # Inside double quotes shlex's escapedquotes is '"', so a backslash
        # before a SINGLE quote is NOT an escape: the backslash survives into
        # the token ('A=x\'y'). This is a real assignment and the player does
        # launch. Caught by the alignment invariant while the splitter still
        # treated \' as an escape inside double quotes.
        r'A="x\'y" aplay f.wav',
        r'A="\'" aplay f.wav',
        # Quoted PROGRAM word: the shell dequotes it, so a player launches.
        "A=x 'aplay' f.wav",
        'A=x "aplay" f.wav',
        "A=x 'ap'lay f.wav",
        # nohup / env interplay after a tricky value
        "A=x nohup aplay f.wav",
        'env "A=x" nohup aplay f.wav',
        "env A=x nohup aplay f.wav",
    ],
)
def test_is_audio_player_command_values_never_change_the_verdict(cmd: str) -> None:
    """Quotes, escapes, $ and backticks in a VALUE never change the verdict."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # bash extension names in the assignment position. Under BASH (which is
        # /bin/sh on the developer box but NOT on Ubuntu CI, where /bin/sh is
        # dash) these are accepted as assignments, so the player really does
        # launch while the helper returns False — the known gap this pin
        # records. Under dash/POSIX sh the name is not a valid identifier, the
        # word becomes an unresolvable command name, nothing launches, and
        # False is simply the correct verdict there. Recorded as known gaps and
        # pinned here the same way the other gaps are.
        "A+=x aplay f.wav",
        "A+=x nohup aplay f.wav",
        "B=y A+=x aplay f.wav",
        "A=(x y) aplay f.wav",
        # env applies no shell rule, so a bash-extension NAME is just a valid
        # NAME=VALUE for env and the player launches.
        "env A+=x aplay f.wav",
        "env A[0]=x aplay f.wav",
        # Shell EXPANSION that splits into more words desyncs the token list
        # from what the shell executes, so the command passes through. A
        # SYNTAX-level effect only; see the Scope paragraph in the docstring for
        # why this is not a defect.
        "A=`echo hi` aplay f.wav",
        "$(echo aplay) f.wav",
        "A=$(echo x y) aplay f.wav",
    ],
)
def test_is_audio_player_command_bash_extension_names_are_known_gaps(cmd: str) -> None:
    """bash-only names and splitting expansions are accepted known false negatives."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # NOT a gap: 'A[0]=x' in the SHELL assignment position never runs the
        # program under EITHER shell — bash: syntax error, rc 1, "A[0]: not a
        # valid identifier"; dash/POSIX sh: the word is a command name that
        # fails to resolve, rc 127 — so False is the CORRECT verdict here. It is
        # only
        # accepted by env, which applies no shell rule - see the gap test above
        # for 'env A[0]=x aplay f.wav'. Kept as a pin so the label cannot drift
        # back to calling this a 'player launches' gap.
        "A[0]=x aplay f.wav",
    ],
)
def test_is_audio_player_command_array_name_prefix_is_correct_passthrough(cmd: str) -> None:
    """'A[0]=x prog' is a shell syntax error, so False is correct, not a gap."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # These are RECOGNISED player commands whose EVALUATION fails at run
        # time. The helper returns True and swallows them on purpose: the
        # silence guard's job is to stop a player, and a command that cannot
        # run is stopped just as well. Modelling evaluation (expansion errors,
        # bash's readonly variables, PATH overrides) is explicitly out of
        # contract - the helper is a SYNTACTIC recognizer. They are pinned so
        # no future change quietly deletes the coverage, NOT because they are
        # defects. test_benign_swallow_class_fails_in_a_real_shell() checks the
        # evaluation failure against sh -c.
        # Round 7 pinned these three as INTENDED benign swallows under the old
        # contract. The operator has since adopted dev-check's contract — True
        # means the program really launches — so they are now passthrough pins
        # in test_is_audio_player_command_fail_capable_prefix_passes_through and
        # test_is_audio_player_command_readonly_and_path_names_pass_through.
        # Only the syntax-error case below remains a genuine benign swallow: a
        # recognised player token whose LINE cannot run, with no expansion and
        # no special name involved.
        "aplay &&",
    ],
)
def test_is_audio_player_command_benign_swallows_are_intended(cmd: str) -> None:
    """A recognised player command that fails at run time is swallowed on purpose."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # Operators GLUED to the player word, a leading '!' and a leading '('
        # are FALSE NEGATIVES: the player really does launch, and the helper
        # returns False. shlex keeps the operator inside a single token, so the
        # token is 'aplay;', 'aplay&&echo', 'aplay&' or 'aplay|cat' rather than a
        # bare player name, and '!' / '(' become their own leading tokens.
        # Splitting on shell operators is a full shell parser, which item 8
        # rules out, so these are recorded rather than fixed.
        "aplay; echo hi",
        "aplay;echo hi",
        "aplay&&echo hi",
        "aplay&",
        "aplay|cat",
        "! aplay f.wav",
        "(aplay f.wav)",
    ],
)
def test_is_audio_player_command_glued_operators_are_known_gaps(cmd: str) -> None:
    """Operators glued to the player word pass through and the player still runs."""
    assert conftest._is_audio_player_command(cmd) is False


def test_glued_operator_gaps_really_launch_the_player() -> None:
    """Ground truth: the glued-operator forms really do run the player.

    Uses an EXTERNAL bare-name stand-in on a scratch PATH, never a player, and
    never a player name in a shell string. The scratch PATH is prepended to the
    real PATH rather than replacing it, so auxiliary commands in the command
    line (e.g. the 'cat' in 'aplay|cat') still resolve - replacing PATH made
    this test report a bogus rc 127 on the first attempt. A positive control
    runs first so no check below can pass vacuously.
    """
    import os as _os
    import shutil
    import stat
    import subprocess
    import tempfile

    scratch = tempfile.mkdtemp(prefix="devb-glued-", dir="/tmp")
    try:
        stand_in = pathlib.Path(scratch) / "devbstandin"
        stand_in.write_text("#!/bin/sh\nprintf 'STOOD-IN\\n'\n")
        stand_in.chmod(stand_in.stat().st_mode | stat.S_IEXEC)
        shell_env = {"PATH": f"{scratch}:{_os.environ.get('PATH', '/usr/bin:/bin')}"}

        control = subprocess.run(
            ["/bin/sh", "-c", "devbstandin"], capture_output=True, text=True, timeout=10, env=shell_env
        )
        assert "STOOD-IN" in control.stdout, "stand-in not reachable; the checks below would be vacuous"

        for cmd in (
            "aplay; echo hi",
            "aplay;echo hi",
            "aplay&&echo hi",
            "aplay&",
            "aplay|cat",
            "! aplay f.wav",
            "(aplay f.wav)",
        ):
            analog = cmd.replace("aplay", "devbstandin")
            assert "aplay" not in analog
            result = subprocess.run(
                ["/bin/sh", "-c", analog], capture_output=True, text=True, timeout=10, env=shell_env
            )
            assert "STOOD-IN" in result.stdout, f"stand-in did not run for {analog!r}: {result.stderr!r}"
            assert conftest._is_audio_player_command(cmd) is False, f"{cmd!r} should be a pinned false negative"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_benign_swallow_class_fails_in_a_real_shell() -> None:
    """Ground truth: the pinned benign swallows really do fail evaluation.

    The stand-in is an EXTERNAL script on a scratch PATH, not the printf
    builtin, because a builtin ignores PATH and would hide the PATH case. No
    player name is ever passed to a shell.
    """
    import shutil
    import stat
    import subprocess
    import tempfile

    scratch = tempfile.mkdtemp(prefix="devb-benign-", dir="/tmp")
    try:
        stand_in = pathlib.Path(scratch) / "devbstandin"
        stand_in.write_text("#!/bin/sh\nprintf 'STOOD-IN'\n")
        stand_in.chmod(stand_in.stat().st_mode | stat.S_IEXEC)
        shell_env = {"PATH": scratch}

        # Positive control first: the stand-in must actually be reachable on the
        # scratch PATH, otherwise the three checks below would pass vacuously.
        control = subprocess.run(
            ["/bin/sh", "-c", "devbstandin"], capture_output=True, text=True, timeout=10, env=shell_env
        )
        assert "STOOD-IN" in control.stdout, "stand-in is not reachable; the checks below would be vacuous"

        # The stand-in is invoked by BARE NAME so a PATH override can break the
        # lookup, and it is an external script rather than a builtin so PATH
        # actually applies.
        #
        # Shell truth (CI-1): 'UID=1' stops the launch only under BASH, whose
        # readonly UID makes the assignment fail (rc 1). Under dash (Ubuntu
        # CI's /bin/sh) an ordinary prefix assignment runs the command — pinned
        # in test_readonly_name_prefix_launches_under_a_dash_like_shell below —
        # so that entry is verified under an EXPLICIT bash, never against
        # /bin/sh, whose identity is machine-dependent. The other two entries
        # are portable POSIX behaviour and stay on /bin/sh.
        portable_checks = [
            ("A=${VAJRA_QA_ABSENT_87219:?e}", "expansion error"),
            ("PATH=/nonexistent", "PATH lookup failure"),
        ]
        for prefix, label in portable_checks:
            analog = f"{prefix} devbstandin"
            result = subprocess.run(
                ["/bin/sh", "-c", analog], capture_output=True, text=True, timeout=10, env=shell_env
            )
            assert "STOOD-IN" not in result.stdout, f"{label}: stand-in unexpectedly ran for {analog!r}"

        # CI-1 ground truth is bash-MODE-specific: bash 5.3 in NORMAL mode
        # prints 'UID: readonly variable' but STILL runs the command (verified
        # on 5.3.20), while bash invoked AS sh (argv0='sh' — the mode
        # '/bin/sh is bash' machines actually run, and the mode os.system
        # triggers there) aborts with rc 1. The bash-side truth is therefore
        # pinned under argv0='sh' via executable=; the dash-side truth lives
        # in test_readonly_name_prefix_launches_under_a_dash_like_shell.
        bash_path = shutil.which("bash")
        if bash_path is None:
            pytest.skip("bash not available: cannot verify the bash-sh readonly-UID ground truth")
        readonly_result = subprocess.run(
            ["sh", "-c", "UID=1 devbstandin"],
            capture_output=True,
            text=True,
            timeout=10,
            env=shell_env,
            executable=bash_path,
        )
        assert (
            "STOOD-IN" not in readonly_result.stdout
        ), "readonly variable: stand-in unexpectedly ran for 'UID=1 devbstandin'"

        # A recognised player token with a trailing operator and nothing after
        # it: sh is a syntax error, the program never runs, and the helper
        # still swallows it. Same benign class as the three above.
        trailing = subprocess.run(
            ["/bin/sh", "-c", "devbstandin &&"], capture_output=True, text=True, timeout=10, env=shell_env
        )
        assert "STOOD-IN" not in trailing.stdout, "trailing-operator form unexpectedly ran the stand-in"
        assert trailing.returncode != 0, f"expected a syntax error, got rc {trailing.returncode}"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@pytest.mark.parametrize(
    "cmd",
    [
        # A prefix word whose EVALUATION can stop the launch: an expansion that
        # errors, a substitution, or arithmetic that divides by zero. True here
        # would promise a launch that never happens, so these pass through.
        "A=${VAJRA_QA_ABSENT_87219:?e} aplay f.wav",
        'A="${VAJRA_QA_ABSENT_87219:?e}" aplay f.wav',
        "A=${} aplay f.wav",
        "A=$(printf x) aplay f.wav",
        "A=`printf x` aplay f.wav",
        "A=$((1/0)) aplay f.wav",
        "env A=${VAJRA_QA_ABSENT_87219:?e} aplay f.wav",
        "nohup env A=${VAJRA_QA_ABSENT_87219:?e} aplay f.wav",
        "A=x B=${VAJRA_QA_ABSENT_87219:?e} aplay f.wav",
        # Default forms whose word is not a plain literal, so undecidable.
        "A=${VAJRA_QA_ABSENT_87219:-$HOME} aplay f.wav",
        "A=${VAJRA_QA_ABSENT_87219:-$(printf x)} aplay f.wav",
        "A=${X:-${Y}} aplay f.wav",
        # ':=' is an assignment form, excluded from the safe set.
        "A=${VAJRA_QA_ABSENT_87219:=d} aplay f.wav",
        # Unbalanced substitution / brace: the shell errors, so passthrough.
        "A=$(printf x aplay f.wav",
        "A=`printf x aplay f.wav",
        "A=${ aplay f.wav",
    ],
)
def test_is_audio_player_command_fail_capable_prefix_passes_through(cmd: str) -> None:
    """A prefix whose evaluation can stop the launch must not be swallowed."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Names that cannot behave as a plain assignment under BASH: it refuses
        # to assign its own readonly variables (rc 1), and a PATH override
        # changes program lookup, so the player is never found. Under dash the
        # six readonly names ARE ordinary assignments and the player LAUNCHES
        # — see test_readonly_name_prefix_launches_under_a_dash_like_shell;
        # the PATH entries behave the same under both shells (lookup fails or
        # redirects before the player is found).
        "UID=1 aplay f.wav",
        "EUID=1 aplay f.wav",
        "PPID=1 aplay f.wav",
        "SHELLOPTS=x aplay f.wav",
        "BASHOPTS=x aplay f.wav",
        "BASH_VERSINFO=x aplay f.wav",
        "PATH=/nonexistent aplay f.wav",
        "PATH=/usr/bin aplay f.wav",
        # env applies PATH before it looks the program up, so the same applies.
        "env PATH=/nonexistent aplay f.wav",
    ],
)
def test_is_audio_player_command_readonly_and_path_names_pass_through(cmd: str) -> None:
    """Readonly and PATH assignment names must not be swallowed."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Safe default forms with a plain literal word: cannot fail, so the
        # player launches and these must STAY swallowed.
        "A=${VAJRA_QA_ABSENT_87219:-d} aplay f.wav",
        "A=${VAJRA_QA_ABSENT_87219-d} aplay f.wav",
        "A=${VAJRA_QA_ABSENT_87219:+d} aplay f.wav",
        "A=${VAJRA_QA_ABSENT_87219+d} aplay f.wav",
        "A=${HOME:-/x/y.z} aplay f.wav",
        'A="${X:-d}" aplay f.wav',
        "A=${X:-a-b} aplay f.wav",
        # Plain expansions cannot fail.
        "A=$HOME aplay f.wav",
        "A=${HOME} aplay f.wav",
        'A="$HOME/x y" aplay f.wav',
        "A=$1 aplay f.wav",
        "A=$? aplay f.wav",
        "A=x$ aplay f.wav",
        "A=$X$Y aplay f.wav",
        # Single quotes are literal, so nothing expands.
        "A='$(not expanded)' aplay f.wav",
        "A='${X:?e}' aplay f.wav",
        # An escaped $ is literal, so there is no expansion.
        r"A=\$HOME aplay f.wav",
        r'A="$HOME" aplay f.wav',
        # Ordinary names, including other special-but-assignable variables.
        "RANDOM=1 aplay f.wav",
        "IFS=x aplay f.wav",
        "AUDIODEV=hw:0,0 aplay f.wav",
        "env A=$HOME aplay f.wav",
    ],
)
def test_is_audio_player_command_evaluable_prefixes_stay_supported(cmd: str) -> None:
    """Prefixes that cannot fail are still swallowed."""
    assert conftest._is_audio_player_command(cmd) is True


def test_evaluation_failing_prefix_class_ground_truth() -> None:
    """Ground truth for both directions of the evaluation-failing class.

    An EXTERNAL bare-name stand-in on a scratch PATH, never a player and never
    a player name in a shell string. A positive control runs first so no check
    below can pass vacuously. The scratch dir is PREPENDED to the real PATH so
    auxiliary commands in a line still resolve.
    """
    import os as _os
    import shutil
    import stat
    import subprocess
    import tempfile

    scratch = tempfile.mkdtemp(prefix="devb-r8-", dir="/tmp")
    try:
        stand_in = pathlib.Path(scratch) / "qplay"
        stand_in.write_text("#!/bin/sh\nprintf 'ok\\n'\n")
        stand_in.chmod(stand_in.stat().st_mode | stat.S_IEXEC)
        shell_env = {"PATH": f"{scratch}:{_os.environ.get('PATH', '/usr/bin:/bin')}"}

        control = subprocess.run(["/bin/sh", "-c", "qplay"], capture_output=True, text=True, timeout=10, env=shell_env)
        assert control.stdout.strip() == "ok", "stand-in unreachable; checks below would be vacuous"

        # 'UID=1' is bash-only ground truth (bash: readonly variable, rc 1;
        # dash: ordinary assignment, the command RUNS) — pinned separately in
        # test_readonly_name_prefix_launches_under_a_dash_like_shell — so it is
        # verified under an EXPLICIT bash here, never against /bin/sh. The
        # remaining prefixes are portable POSIX behaviour.
        not_run = [
            "A=${VAJRA_QA_ABSENT_87219:?e}",
            "A=${}",
            "A=$((1/0))",
            "PATH=/nonexistent",
        ]
        for prefix in not_run:
            result = subprocess.run(
                ["/bin/sh", "-c", f"{prefix} qplay"], capture_output=True, text=True, timeout=10, env=shell_env
            )
            assert result.stdout.strip() != "ok", f"stand-in unexpectedly ran for {prefix!r}"

        # CI-1 ground truth is bash-MODE-specific: bash invoked AS sh
        # (argv0='sh') aborts the command on the readonly assignment (rc 1),
        # while bash 5.3 in normal mode prints the error but STILL runs it.
        # The bash-sh mode is the one pinned here; the dash-side truth lives
        # in test_readonly_name_prefix_launches_under_a_dash_like_shell.
        bash_path = shutil.which("bash")
        if bash_path is None:
            pytest.skip("bash not available: cannot verify the bash-sh readonly-UID ground truth")
        readonly_result = subprocess.run(
            ["sh", "-c", "UID=1 qplay"],
            capture_output=True,
            text=True,
            timeout=10,
            env=shell_env,
            executable=bash_path,
        )
        assert readonly_result.stdout.strip() != "ok", "stand-in unexpectedly ran for 'UID=1'"

        does_run = [
            "A=${VAJRA_QA_ABSENT_87219:-d}",
            "A=${HOME:-/x/y.z}",
            "A=$HOME",
            "A=${HOME}",
            "RANDOM=1",
            "IFS=x",
        ]
        for prefix in does_run:
            result = subprocess.run(
                ["/bin/sh", "-c", f"{prefix} qplay"], capture_output=True, text=True, timeout=10, env=shell_env
            )
            assert result.stdout.strip() == "ok", f"stand-in did not run for {prefix!r}: {result.stderr!r}"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# A shim that behaves as dash does for exactly the delta this file cares
# about, for machines with no dash (this developer box: /bin/sh -> bash).
# IMMUTABLE template: {python} is the only substitution.
_DASH_SIMULATION_SHIM = """#!{python}
# SIMULATED dash for CI-1: identical to bash EXCEPT that leading NAME=VALUE
# prefixes whose NAME bash refuses as readonly are ordinary assignments and
# the command runs, as in dash/POSIX sh. Everything else is run by bash.
import os
import subprocess
import sys

BASH_READONLY = {{"UID", "EUID", "PPID", "SHELLOPTS", "BASHOPTS", "BASH_VERSINFO"}}

args = sys.argv[1:]
if not args or args[0] != "-c" or len(args) < 2:
    os.execv("/bin/bash", ["bash"] + args)

words = args[1].split()
env = dict(os.environ)
rest = list(words)
while rest:
    name, sep, _value = rest[0].partition("=")
    if sep and name in BASH_READONLY:
        env[name] = _value
        rest.pop(0)
        continue
    break
raise SystemExit(subprocess.run(["/bin/bash", "-c", " ".join(rest)], env=env).returncode)
"""


def _dash_like_shell(scratch: pathlib.Path) -> tuple[list[str], str]:
    """Resolve a shell with dash's prefix-assignment semantics.

    Prefers a REAL dash binary. Where none exists (this developer box has
    only bash and zsh, and zsh also refuses UID), it writes a SIMULATED dash
    into the scratch directory: a shim identical to bash except that the
    names bash treats as readonly are ordinary prefix assignments and the
    command runs — dash's documented behaviour (dash defines no readonly
    UID/EUID; POSIX prefix assignments precede the utility). Returns the
    shell argv and a label the caller must surface, so no run ever pretends
    it used a real dash when it used the simulation.
    """
    import shutil
    import sys

    real_dash = shutil.which("dash")
    if real_dash is not None:
        return [real_dash], "real dash"
    shim = scratch / "dashlike-sh"
    shim.write_text(_DASH_SIMULATION_SHIM.format(python=sys.executable))
    shim.chmod(0o755)
    return [str(shim)], "SIMULATED dash (bash + readonly-name assignment delta)"


@pytest.mark.parametrize(
    "name",
    ["UID", "EUID", "PPID", "SHELLOPTS", "BASHOPTS", "BASH_VERSINFO"],
)
def test_readonly_name_prefix_launches_under_a_dash_like_shell(name: str, tmp_path) -> None:
    """Ground truth: under dash, a bash-readonly NAME=VALUE prefix RUNS the program.

    bash refuses to assign UID/EUID/PPID/SHELLOPTS/BASHOPTS/BASH_VERSINFO,
    so 'NAME=1 prog' never launches there — which is why the guard passes
    those names through (test_is_audio_player_command_readonly_and_path_
    names_pass_through). dash (Ubuntu CI's /bin/sh) defines no such readonly
    variables: the prefix is an ordinary assignment and the program LAUNCHES.
    This pins that per-shell truth with a stand-in, the bash direction of the
    same truth (which is also this test's built-in RED control: pointed at
    bash, the dash-side assertion fails), and the guard's CURRENT verdict
    (False = passthrough) for the same inputs: on a dash system that verdict
    fails OPEN for this class — a real player would run. Whether the guard
    should instead swallow these fail-closed is the CI-1 item-3 lead
    decision; conftest.py is deliberately unchanged in this round.

    Never runs a player: the stand-in is an external scratch script and no
    player name is ever passed to a shell.
    """
    import shutil
    import stat
    import subprocess

    scratch = pathlib.Path(str(tmp_path))
    stand_in = scratch / "devbstandin"
    stand_in.write_text("#!/bin/sh\nprintf 'STOOD-IN'\n")
    stand_in.chmod(stand_in.stat().st_mode | stat.S_IEXEC)

    shell_argv, label = _dash_like_shell(scratch)
    # Scratch-only PATH proves the stand-in is found via the scratch dir; the
    # shim's shebang is absolute, so the shim itself still runs.
    env = {"PATH": str(scratch)}

    control = subprocess.run(shell_argv + ["-c", "devbstandin"], capture_output=True, text=True, timeout=10, env=env)
    assert "STOOD-IN" in control.stdout, f"stand-in unreachable under {label}; the checks below would be vacuous"

    ran = subprocess.run(
        shell_argv + ["-c", f"{name}=1 devbstandin"], capture_output=True, text=True, timeout=10, env=env
    )
    assert (
        "STOOD-IN" in ran.stdout
    ), f"under {label}, {name!r}=1 did NOT run the stand-in: dash treats it as an ordinary assignment"

    bash_path = shutil.which("bash")
    if bash_path is not None:
        # argv0='sh' on purpose: bash AS sh aborts the command on the readonly
        # assignment; bash 5.3 in NORMAL mode prints the error but STILL runs
        # the command (verified on 5.3.20) — so the mode is part of the truth
        # this asserts. This block is also the test's built-in RED control:
        # pointed at sh-mode bash, the dash-side assertion above fails.
        blocked = subprocess.run(
            ["sh", "-c", f"{name}=1 devbstandin"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            executable=bash_path,
        )
        assert "STOOD-IN" not in blocked.stdout, f"bash (as sh) unexpectedly ran the stand-in for {name!r}=1"

    # Pin the guard's CURRENT verdict: False (passthrough). On dash systems
    # this is fail-open for this class; see the docstring and CI-1 item 3.
    assert conftest._is_audio_player_command(f"{name}=1 aplay f.wav") is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Unquoted, unescaped shell METACHARACTERS inside a prefix word change
        # what the shell runs, but shlex keeps them inside one token, so the
        # token's basename is still 'A=x...' and looks like a plain assignment.
        # True here would promise a launch that does not happen.
        "A=x|| aplay f.wav",  # A=x succeeds, so the right side never runs
        "A=x> aplay f.wav",  # a redirect: it runs f.wav, not a player
        "A=x< aplay f.wav",  # same, input redirect
        "A=x) aplay f.wav",  # shell syntax error
        "A=( aplay f.wav",  # shell syntax error
        "A=x( aplay f.wav",  # shell syntax error
        "B=x;y aplay f.wav",  # runs y, not the player
        "env A=x|| aplay f.wav",
        "env A=(x) aplay f.wav",
        "A=x&& aplay f.wav",
        "A=x; aplay f.wav",
        "A=x| aplay f.wav",
        "A=x& aplay f.wav",
        "A=x&&y aplay f.wav",
        "nohup env A=x|| aplay f.wav",
        "env -- A=x|| aplay f.wav",
        "A=x|| B=y aplay f.wav",
    ],
)
def test_is_audio_player_command_metacharacter_prefix_passes_through(cmd: str) -> None:
    """An unquoted metacharacter in a prefix word must not be swallowed."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # Quoted or escaped metacharacters stay SUPPORTED: the shell does not
        # treat them as operators, so the assignment is a real assignment and
        # the player really does launch.
        'A="x;y" aplay f.wav',
        "A='x|y' aplay f.wav",
        'A="x(y)" aplay f.wav',
        "A='(x)' aplay f.wav",
        r"A=\(x aplay f.wav",
        r"A=x\; aplay f.wav",
        r'A="x\;y" aplay f.wav',
        "A='x;y' aplay f.wav",
        r"A=x\&y aplay f.wav",
        r"A=\|x aplay f.wav",
        r"A=\<x aplay f.wav",
        r"A=\>x aplay f.wav",
        r"A=\)x aplay f.wav",
        # env sees the dequoted word, so a quoted metacharacter is data there too.
        'env A="x;y" aplay f.wav',
        "env A='x|y' aplay f.wav",
        # Ordinary assignments and other supported forms are untouched.
        "A=x aplay f.wav",
        'A="x y" aplay f.wav',
        "AUDIODEV=hw:0,0 aplay f.wav",
        "RANDOM=1 aplay f.wav",
    ],
)
def test_is_audio_player_command_quoted_metacharacters_stay_supported(cmd: str) -> None:
    """Quoted or escaped metacharacters do not change what the shell runs."""
    assert conftest._is_audio_player_command(cmd) is True


def test_metacharacter_prefix_class_ground_truth() -> None:
    """Ground truth for both directions of the metacharacter-prefix class.

    The stand-in lives in its OWN read-only directory, separate from the shell's
    cwd: a generated redirect such as 'A=x> qplay' would otherwise truncate the
    stand-in and silently invalidate the run. The stand-in is chmod 0555 and its
    directory 0555, and the suite re-checks it after the run. A positive control
    runs first, so no check below can pass vacuously. The scratch bin is
    PREPENDED to the real PATH so auxiliary commands in a line still resolve.
    No player name is ever passed to a shell.
    """
    import os as _os
    import shutil
    import subprocess
    import tempfile

    root = tempfile.mkdtemp(prefix="devb-r9-", dir="/tmp")
    try:
        bindir = pathlib.Path(root) / "bin"
        work = pathlib.Path(root) / "cwd"
        bindir.mkdir()
        work.mkdir()
        stand_in = bindir / "qplay"
        stand_in.write_text("#!/bin/sh\nprintf 'ok\\n'\n")
        stand_in.chmod(0o555)
        bindir.chmod(0o555)
        env = {"PATH": f"{bindir}:{_os.environ.get('PATH', '/usr/bin:/bin')}"}

        def control() -> bool:
            r = subprocess.run(["sh", "-c", "qplay"], capture_output=True, text=True, env=env, timeout=10, cwd=work)
            return r.stdout.strip() == "ok"

        assert control(), "stand-in unreachable; the checks below would be vacuous"

        should_not_run = [
            "A=x||",
            "A=x>",
            "A=x<",
            "A=x)",
            "A=(",
            "A=x(",
            "B=x;y",
        ]
        for prefix in should_not_run:
            analog = f"{prefix} qplay"
            assert "aplay" not in analog
            result = subprocess.run(["sh", "-c", analog], capture_output=True, text=True, env=env, timeout=10, cwd=work)
            assert result.stdout.strip() != "ok", f"stand-in unexpectedly ran for {prefix!r}"
            assert conftest._is_audio_player_command(f"{prefix} aplay f.wav") is False

        should_run = [
            'A="x;y"',
            "A='x|y'",
            'A="x(y)"',
            "A='(x)'",
            r"A=\(x",
            r"A=x\;",
            "A=x",
        ]
        for prefix in should_run:
            analog = f"{prefix} qplay"
            assert "aplay" not in analog
            result = subprocess.run(["sh", "-c", analog], capture_output=True, text=True, env=env, timeout=10, cwd=work)
            assert result.stdout.strip() == "ok", f"stand-in did not run for {prefix!r}: {result.stderr!r}"
            assert conftest._is_audio_player_command(f"{prefix} aplay f.wav") is True

        # The redirect cases above wrote into the shell's cwd, never into bindir.
        assert control(), "stand-in was damaged by a generated redirect; the run is INVALID"
    finally:
        bindir.chmod(0o755)
        shutil.rmtree(root, ignore_errors=True)


def test_raw_split_matches_shlex_on_adversarial_escapes() -> None:
    """The fail-safe invariant: the raw split must reproduce the shlex tokens.

    The helper only has to DISAGREE detectably, so this asserts the property
    the caller depends on across adversarial quoting shapes — escapes inside
    double quotes, single quotes, $, backtick and backslash-newline. It calls
    the helper directly, so it tests alignment rather than the player verdict.
    """
    import shlex

    shapes = [
        'A="x\\"y" z',
        'A="x\\" y" "C=q" z',
        'A="x\\"   y" z',
        "A='x\\' \"C=q\" z",
        'A="x\\\\" z',
        'A="x\\y z" z',
        "A=$HOME z",
        "A=`echo hi` z",
        'A="$HOME" z',
        "A='$HOME' z",
        "A=x\\ y z",
        "A=x\\\ny z",
        'A="a\\"b" W="c d" z',
        "A='\\'' z",
        'A="\'" z',
        'A="\\"" z',
        "A=x\ty",
        "A=x\r\ny z",
        'A="x"y z',
        "A='x'y z",
    ]
    for shape in shapes:
        try:
            tokens = shlex.split(shape)
        except ValueError:
            # shlex cannot tokenize this shape (unbalanced quoting), so the
            # classifier is never reached: it only calls the splitter after
            # shlex.split has already succeeded. Out of contract by design.
            continue
        words = conftest._leading_quoted_words(shape)
        assert len(words) == len(tokens), f"word count desync for {shape!r}: {words} vs {tokens}"
        for word, token in zip(words, tokens):
            _is_assignment, dequoted, _raw = word
            assert dequoted == token, f"dequoted text desync for {shape!r}: {dequoted!r} != {token!r}"


@pytest.mark.parametrize(
    "cmd",
    [
        # Controls: env receives the DEQUOTED, UNESCAPED word in argv and
        # applies no such rule, so a quoted/escaped name is a valid assignment
        # for env and the player does launch. These must stay True.
        'env AUDIO"DEV"=x aplay f.wav',
        r"env AUDIO\DEV=x aplay f.wav",
        'env "A=x" aplay f.wav',
        'env A"B"=x aplay f.wav',
    ],
)
def test_is_audio_player_command_env_accepts_quoted_or_escaped_name(cmd: str) -> None:
    """env sees the deescaped word, so shell quoting rules stop at the exec boundary."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # A quoted VALUE is not a quoted word: the shell still sees a single
        # assignment word, and the player really does launch.
        'AUDIODEV="x" aplay f.wav',
        "AUDIODEV='x' aplay f.wav",
        'AUDIODEV="x"y aplay f.wav',
        "AUDIODEV='x'y aplay f.wav",
        'VAR1=1 AUDIODEV="hw:0,0" aplay file.wav',
        'VAR1=1 AUDIODEV="x" nohup aplay f.wav',
        'A="foo bar" aplay f.wav',
    ],
)
def test_is_audio_player_command_quoted_value_is_still_an_assignment(cmd: str) -> None:
    """A quoted value keeps the leading word a real shell assignment."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # env receives the UNQUOTED string as an argv element, and treats
        # "A=x" as an ordinary valid assignment, so the player does launch.
        # These must stay True even though the same spelling is False at shell
        # level: quoting rules stop at the exec boundary.
        'env "A=x" aplay f.wav',
        "env 'A=x' aplay f.wav",
        'env -- "A=x" aplay f.wav',
        'env -i "A=x" aplay f.wav',
        'env "/usr/bin/aplay" f.wav',
        "env 'A=x' '/usr/bin/aplay' f.wav",
    ],
)
def test_is_audio_player_command_env_receives_unquoted_assignment(cmd: str) -> None:
    """env sees the dequoted string, so a quoted whole token is still an assignment."""
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        "env aplay file.wav",
        "env AUDIODEV=x aplay f.wav",
        "/usr/bin/env AUDIODEV=x aplay f.wav",
        "/bin/env AUDIODEV=x aplay f.wav",
        "env VAR1=1 VAR2=2 paplay file.wav",
        "env AUDIODEV=x '/usr/bin/afplay' audio.aiff",
        'env FOO="bar baz" ffplay sound.wav',
        "env -i aplay f.wav",
        "env --ignore-environment aplay f.wav",
        "env -u X aplay f.wav",
        "env --unset X aplay f.wav",
        "env --unset=ALSA aplay f.wav",
        "env -- aplay f.wav",
        "env -u AUDIODEV AUDIODEV=hw:0 aplay f.wav",
        "/usr/bin/env -i AUDIODEV=x aplay f.wav",
        "env -i -u X -- aplay f.wav",
    ],
)
def test_is_audio_player_command_env_prefix_accepted_options(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        "nohup aplay f.wav",
        "/usr/bin/nohup aplay f.wav",
        "/bin/nohup aplay f.wav",
        "nohup env aplay f.wav",
        "nohup env -i aplay f.wav",
        "nohup env AUDIODEV=x aplay f.wav",
        "AUDIODEV=x nohup aplay f.wav",
        "env nohup aplay f",
        "env -i nohup aplay f",
        "env AUDIODEV=x nohup aplay f",
    ],
)
def test_is_audio_player_command_nohup_prefix(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is True


@pytest.mark.parametrize(
    "cmd",
    [
        # In shell syntax ('sh -c'), nohup does not parse assignments;
        # NAME=VALUE is treated as the executable argument, exiting 127 without running a player.
        "nohup AUDIODEV=x aplay f.wav",
        "env nohup AUDIODEV=x aplay f",
        "/usr/bin/nohup AUDIODEV=x aplay f.wav",
        "/bin/nohup AUDIODEV=x aplay f.wav",
    ],
)
def test_is_audio_player_command_nohup_assignment_false_swallow_prevention(cmd: str) -> None:
    """Verify that variable assignments following nohup are not swallowed."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # GNU env exits 125 for empty or invalid unset variable names without running command
        "env --unset= aplay f.wav",
        "env --unset='' aplay f.wav",
        "env -u '' aplay f.wav",
        "env --unset '' aplay f.wav",
        "env --unset=FOO=BAR aplay f.wav",
        "env -u FOO=BAR aplay f.wav",
        "env -u aplay",
    ],
)
def test_is_audio_player_command_empty_or_invalid_unset_passthrough(cmd: str) -> None:
    """Verify that empty or malformed unset options pass through without swallow."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # GNU env stops option parsing at the first assignment;
        # any subsequent option-like token (-i, --, -u) is treated as the executable name,
        # failing with exit 127 without running the player.
        "env AUDIODEV=x -i aplay f.wav",
        "env AUDIODEV=x -- aplay f.wav",
        "env AUDIODEV=x -u X aplay f.wav",
        "nohup env AUDIODEV=x -i aplay f.wav",
        "nohup env AUDIODEV=x -- aplay f.wav",
    ],
)
def test_is_audio_player_command_env_options_after_assignment_fail(cmd: str) -> None:
    """Verify that env stops option parsing upon reaching assignments."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("aplay x && echo y", True),
        ("aplay f | cat", True),
        ("echo y && aplay", False),
        ("cat file | aplay", False),
    ],
)
def test_is_audio_player_command_compound_chaining_and_pipes(cmd: str, expected: bool) -> None:
    """Pin the four explicit compound behaviors:

    Commands starting with a player are swallowed (safe direction);
    commands where another command precedes a player pass through (known gap).
    """
    assert conftest._is_audio_player_command(cmd) is expected


@pytest.mark.parametrize(
    "cmd",
    [
        # Known false negatives / coverage gaps.
        # For these forms the player command really does still run, so the helper
        # returns False and the command is NOT intercepted. "Passthrough" means
        # "we do not stub this out" -- it does NOT mean "safe". The only effect
        # of returning False here is that os.system reaches the real shell, so
        # the real player launches. Treat these as recorded debt, not as
        # protection.
        'env -S "aplay f"',
        "env -S aplay f",
        "env -C /tmp aplay f.wav",
        "env --chdir=/tmp aplay f.wav",
        "env -v aplay f.wav",
        "env --debug aplay f.wav",
        "env -iu X aplay f.wav",
        "env - aplay f.wav",
        "nohup -- aplay",
    ],
)
def test_is_audio_player_command_known_false_negatives_coverage_gaps(cmd: str) -> None:
    """Pin known false-negative coverage gaps where helper returns False without invoking player."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # NOT a gap, and not a swallow either: '-u NAME' consumes NAME as the
        # variable to unset, so a player-looking token in that slot is never the
        # command. 'env -iu aplay f.wav' unsets 'aplay' and then tries to run
        # 'f.wav' (GNU env exits 127, "env: 'f.wav': No such file or
        # directory"). Returning True would swallow a command whose program is
        # not a player, so False is the correct verdict — verified by effect,
        # never by running a player. Pinned separately from the real '-iu X'
        # gap above so the two are not conflated.
        "env -u aplay f.wav",
        "env -iu aplay f.wav",
        "env -i -u aplay f.wav",
        "env -u aplay",
    ],
)
def test_is_audio_player_command_unset_consumes_player_looking_name(cmd: str) -> None:
    """Pin the case where a player-looking token is consumed as -u's NAME argument."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        # dev-grok findings: programs where the actual executed command is not a player
        "env -S 'printf \"ran-printf\\n\"' aplay",
        "env --split-string 'printf \"ran-printf\\n\"' aplay",
        "env --split-string=printf aplay",
        "env -a aplay printf 'a-ok\\n'",
        "env --argv0 aplay printf 'argv0-ok\\n'",
        # GNU env exits 125 for -0 with a command
        "env -0 aplay f.wav",
        "nohup --help aplay",
    ],
)
def test_is_audio_player_command_env_unsupported_options_and_failures(cmd: str) -> None:
    """Verify that commands executing non-players or failing under env/nohup return False."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        "/opt/myapp/env aplay file",
        "./env aplay file",
        "/custom/bin/env aplay file",
    ],
)
def test_is_audio_player_command_narrowed_env_path_passthrough(cmd: str) -> None:
    """Verify that only exact 'env', '/usr/bin/env', or '/bin/env' match the env prefix."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        "µ=1 aplay",
        "π=3.14 aplay",
    ],
)
def test_is_audio_player_command_non_ascii_assignment_passthrough(cmd: str) -> None:
    """Verify that non-ASCII variable assignments are not recognized as shell assignments."""
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        "aplaylist file.wav",
        "echo aplay",
        'sh -c "aplay file.wav"',
        "env echo aplay",
        "AUDIODEV=x echo aplay",
        "env aplaylist file.wav",
        "AUDIODEV=x aplaylist file.wav",
        "nohup echo aplay",
        "nohup env echo aplay",
        "ls -la",
        "python -c 'import os'",
        "cat aplay",
    ],
)
def test_is_audio_player_command_non_player_and_lookalikes(cmd: str) -> None:
    assert conftest._is_audio_player_command(cmd) is False


@pytest.mark.parametrize(
    "cmd",
    [
        "",
        "   ",
        "AUDIODEV=x",
        "env",
        "env AUDIODEV=x",
        "env -i",
        "env -u X",
        "nohup",
        'aplay "unclosed quote',
        None,
        123,
    ],
)
def test_is_audio_player_command_edge_cases(cmd: object) -> None:
    assert conftest._is_audio_player_command(cmd) is False  # type: ignore[arg-type]


def test_guard_swallows_player_and_passes_through_non_player(monkeypatch) -> None:
    """Verify guarded os.system behavior with a recorder placed beneath it."""
    passed_through: list[str] = []

    def fake_underlying_system(command: str) -> int:
        passed_through.append(command)
        return 42

    monkeypatch.setattr(os, "system", fake_underlying_system)

    del conftest._AUDIO_STUB_CALLS[:]
    conftest._guard_os_system_player(monkeypatch)

    player_commands = [
        "aplay file.wav",
        "/usr/bin/aplay file.wav",
        '"/usr/bin/aplay" file.wav',
        "'aplay' file.wav",
        "AUDIODEV=x aplay f.wav",
        "VAR1=1 VAR2=2 aplay f.wav",
        "env AUDIODEV=x aplay f.wav",
        "env aplay f.wav",
        "env -i aplay f.wav",
        "env -u X aplay f.wav",
        "nohup aplay f.wav",
        "env nohup aplay f",
        "aplay x && echo y",
        "aplay f | cat",
        'AUDIODEV="x" aplay f.wav',
        "AUDIODEV='x' aplay f.wav",
        'env "A=x" aplay f.wav',
        r"AUDIODEV=\x aplay f.wav",
        'env AUDIO"DEV"=x aplay f.wav',
    ]

    for cmd in player_commands:
        rc = os.system(cmd)
        assert rc == 0, f"Expected 0 for swallowed player command: {cmd}"

    assert len(passed_through) == 0, "No player commands should reach the underlying system"
    assert len(conftest._AUDIO_STUB_CALLS) == len(player_commands)
    for stub_call in conftest._AUDIO_STUB_CALLS:
        assert stub_call["call"] == "os.system"

    non_player_commands = [
        "aplaylist file.wav",
        "echo aplay",
        'sh -c "aplay x"',
        "env echo aplay",
        "AUDIODEV=x echo aplay",
        "/opt/myapp/env aplay file",
        "µ=1 aplay",
        "echo y && aplay",
        "cat file | aplay",
        "env -S 'printf \"ran-printf\\n\"' aplay",
        "env --split-string 'printf \"ran-printf\\n\"' aplay",
        "env --split-string=printf aplay",
        "env -a aplay printf 'a-ok\\n'",
        "env --argv0 aplay printf 'argv0-ok\\n'",
        "env -0 aplay f.wav",
        "nohup AUDIODEV=x aplay f.wav",
        "env nohup AUDIODEV=x aplay f",
        "env --unset= aplay f.wav",
        "env AUDIODEV=x -i aplay f.wav",
        '"AUDIODEV=x" aplay f.wav',
        "'AUDIODEV=x' aplay f.wav",
        'VAR1=1 "AUDIODEV=x" aplay f.wav',
        'nohup "AUDIODEV=x" aplay f.wav',
        'AUDIO"DEV"=x aplay f.wav',
        "AUDIO'DEV'=x aplay f.wav",
        r"AUDIO\DEV=x aplay f.wav",
        r"\AUDIODEV=x aplay f.wav",
        'VAR1=1 AUDIO"DEV"=x aplay f.wav',
        'A"B"=x aplay f.wav',
    ]

    for cmd in non_player_commands:
        rc = os.system(cmd)
        assert rc == 42, f"Expected 42 for passed-through command: {cmd}"

    assert passed_through == non_player_commands
    assert len(conftest._AUDIO_STUB_CALLS) == len(player_commands)


def test_guard_monkeypatch_restoration() -> None:
    """Verify that monkeypatching can be undone to restore the original os.system."""
    mp = pytest.MonkeyPatch()
    before = os.system
    conftest._guard_os_system_player(mp)
    after = os.system
    assert after is not before
    mp.undo()
    assert os.system is before


def test_opt_in_env_var_leaves_audio_untouched_by_inspection() -> None:
    """Verify by inspection only that VAJRA_TEST_AUDIO=1 bypasses audio silencing without execution."""
    source = inspect.getsource(conftest._silence_test_audio)
    assert 'if os.environ.get(_TEST_AUDIO_ENV) == "1":' in source
    assert "yield" in source
    assert "return" in source
    assert "_guard_os_system_player(monkeypatch)" in source
