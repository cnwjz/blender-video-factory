"""Blender 5.1.2 exit code probe.

Usage:
  blender --background --factory-startup --python blender_exit_code_probe.py -- --method sys_exit --code 0
  blender --background --factory-startup --python blender_exit_code_probe.py -- --method os_exit --code 1

Verifies that sys.exit(N) or os._exit(N) reliably propagates
exit code N through the Blender process.
"""

import sys, os


def main():
    method = "sys_exit"
    code = 0

    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    i = 0
    while i < len(args):
        if args[i] == "--method" and i + 1 < len(args):
            method = args[i + 1]; i += 2
        elif args[i] == "--code" and i + 1 < len(args):
            code = int(args[i + 1]); i += 2
        else:
            i += 1

    msg = f"BLENDER_EXIT_PROBE method={method} code={code}"
    print(msg)
    sys.stdout.flush()
    sys.stderr.flush()

    if method == "sys_exit":
        raise SystemExit(code)
    elif method == "os_exit":
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    else:
        print(f"ERROR: unknown method {method}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
