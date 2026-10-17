"""The analyzer never imports target modules or opens network/process APIs."""
import sys

sys.dont_write_bytecode = True


def offline(event, args):
    if event in {"socket.connect", "socket.connect_ex", "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
        raise RuntimeError("Analyzer runtime forbids network and child processes: " + event)


sys.addaudithook(offline)

from polygraph.cli import main

if __name__ == "__main__":
    main()
