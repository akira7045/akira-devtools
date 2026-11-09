"""Console-script wrappers so each tool installs as its own command."""
import sys


def secretscan_main():
    from akira_devtools import secretscan
    sys.argv = ["secretscan"] + sys.argv[1:]
    return secretscan.main()


def apidiff_main():
    from akira_devtools.apidiff import main
    return main(sys.argv[1:])


def jsonl2csv_main():
    from akira_devtools.jsonl2csv import main
    return main(sys.argv[1:])


def dupfind_main():
    from akira_devtools.dupfind import main
    return main(sys.argv[1:])


def envcheck_main():
    from akira_devtools.envcheck import main
    return main(sys.argv[1:])


def logsum_main():
    from akira_devtools.logsum import main
    return main(sys.argv[1:])
