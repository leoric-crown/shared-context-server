#!/usr/bin/env python
import re
import sys


def main():
    makefile_path = sys.argv[1] if len(sys.argv) > 1 else "Makefile"
    with open(makefile_path) as f:
        lines = f.readlines()

    print("Usage: make [target]")
    print("\nAvailable targets:")

    targets = []
    for line in lines:
        if re.match(r"^[a-zA-Z_-]+:.*?##.*", line):
            target = line.split(":")[0]
            comment = line.split("##")[1].strip()
            targets.append((target, comment))

    for target, comment in targets:
        print(f"  \033[36m{target:<20}\033[0m {comment}")


if __name__ == "__main__":
    main()
