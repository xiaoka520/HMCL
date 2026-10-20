#!/usr/bin/env python3
"""Reapply and verify the fork's unconditional download policy after upstream merges."""

import argparse
from pathlib import Path
import re
import subprocess
import zipfile

REGION = Path("HMCL/src/main/java/org/jackhuang/hmcl/util/RegionUtils.java")
JAVA_ROOTS = ("HMCL/src/main/java", "HMCLCore/src/main/java", "HMCLBoot/src/main/java")
UI_CALLERS = {
    "HMCL/src/main/java/org/jackhuang/hmcl/ui/download/VersionsPage.java",
    "HMCL/src/main/java/org/jackhuang/hmcl/ui/instances/DownloadListPage.java",
}
METHODS = {
    "init", "checkMachineIsChinaMainland", "isIsChinaMainlandMachine",
    "checkChinaMainlandNetwork", "isIsChinaMainlandNetwork", "RegionUtils",
}


def masked_java(source):
    """Mask comments and literals so braces in either do not affect method extraction."""
    return re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
        lambda match: "".join("\n" if c == "\n" else " " for c in match[0]),
        source,
    )


def method_body(source, name):
    masked = masked_java(source)
    matches = list(re.finditer(r"\b" + re.escape(name) + r"\s*\([^()]*\)\s*\{", masked))
    if len(matches) != 1:
        raise ValueError(f"Expected one method declaration for {name}, found {len(matches)}")
    start = matches[0].end()
    depth = 1
    for end in range(start, len(masked)):
        depth += (masked[end] == "{") - (masked[end] == "}")
        if depth == 0:
            return source[start:end]
    raise ValueError(f"Unclosed method: {name}")


def render_region(source):
    """Preserve upstream's machine detector, replacing all network detection code."""
    declarations = set(re.findall(
        r"(?:public|private)\s+(?:static\s+)?(?:boolean\s+|void\s+)?(\w+)\s*\(",
        masked_java(source),
    ))
    if declarations - METHODS:
        raise ValueError(f"RegionUtils gained unknown API: {sorted(declarations - METHODS)}")
    machine = method_body(source, "checkMachineIsChinaMainland")
    machine = re.sub(r"(?<!@Nullable )Kernel32 kernel32", "@Nullable Kernel32 kernel32", machine)
    marker = source.find("package org.jackhuang.hmcl.util;")
    if marker < 0:
        raise ValueError("Unexpected RegionUtils package")
    return source[:marker] + '''package org.jackhuang.hmcl.util;

import org.jackhuang.hmcl.util.i18n.LocaleUtils;
import org.jackhuang.hmcl.util.platform.NativeUtils;
import org.jackhuang.hmcl.util.platform.OperatingSystem;
import org.jackhuang.hmcl.util.platform.windows.Kernel32;
import org.jackhuang.hmcl.util.platform.windows.WinConstants;
import org.jetbrains.annotations.NotNullByDefault;
import org.jetbrains.annotations.Nullable;

import java.time.Duration;
import java.time.ZoneId;
import java.time.ZonedDateTime;

/// Region information for mirror selection and account defaults, without download restrictions.
@NotNullByDefault
public final class RegionUtils {

    /// Cached machine region; independent of the unrestricted download policy.
    private static final boolean IS_CHINA_MAINLAND_MACHINE = checkMachineIsChinaMainland();

    /// Keeps the upstream startup API without scheduling network requests.
    public static void init() {
        // This fork never queries the user's public IP to restrict downloads.
    }

    /// Detects the machine region using the upstream time zone and system region rules.
    private static boolean checkMachineIsChinaMainland() {''' + machine + '''}

    /// Returns the machine region for existing mirror and account behavior.
    public static boolean isIsChinaMainlandMachine() {
        return IS_CHINA_MAINLAND_MACHINE;
    }

    /// Always permits downloads, irrespective of machine region, IP, or network availability.
    public static boolean isIsChinaMainlandNetwork() {
        return false;
    }

    /// Prevents instantiation of this utility class.
    private RegionUtils() {
    }
}
'''


def verify(root):
    source = (root / REGION).read_text(encoding="utf-8")
    if source != render_region(source):
        raise ValueError("RegionUtils is not the fork's unrestricted implementation")
    for folder in JAVA_ROOTS:
        for path in (root / folder).rglob("*.java"):
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8")
            code = masked_java(text)
            if "ipwho.is" in text or "checkChinaMainlandNetwork" in code:
                raise ValueError(f"IP region detection reintroduced: {relative}")
            if path == root / REGION:
                continue
            if "isIsChinaMainlandNetwork" in code or 'i18n("download.china")' in text:
                if relative not in UI_CALLERS:
                    raise ValueError(f"Unknown download restriction caller: {relative}")
                for line in text.splitlines():
                    if "isIsChinaMainlandNetwork" in line and line.strip() != "if (RegionUtils.isIsChinaMainlandNetwork()) {":
                        raise ValueError(f"Download restriction condition changed: {relative}")
    print("Download policy verified: no IP lookup, network restriction always false.")


def verify_jar(jar):
    """Check actual shipped bytecode, including absence of the upstream IP lookup."""
    with zipfile.ZipFile(jar) as archive:
        data = archive.read("org/jackhuang/hmcl/util/RegionUtils.class")
        if b"ipwho.is" in data or b"checkChinaMainlandNetwork" in data:
            raise ValueError("Built RegionUtils contains network detection")
    output = subprocess.check_output([
        "javap", "-classpath", str(jar), "-c", "org.jackhuang.hmcl.util.RegionUtils"
    ], text=True)
    for name, expected in (("init", ["return"]), ("isIsChinaMainlandNetwork", ["iconst_0", "ireturn"])):
        match = re.search(r"public static \w+ " + name + r"\(\);\s+Code:\s*([\s\S]*?)(?=\n\s*\n)", output)
        if not match:
            raise ValueError(f"Missing bytecode for {name}")
        instructions = re.findall(r"^\s*\d+:\s+(.*)$", match[1], re.MULTILINE)
        if instructions != expected:
            raise ValueError(f"Unexpected bytecode for {name}: {instructions}")
    print(f"Shipped bytecode verified: {jar}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()
    if args.apply:
        path = args.root / REGION
        path.write_text(render_region(path.read_text(encoding="utf-8")), encoding="utf-8")
    verify(args.root)
    if args.jar:
        verify_jar(args.jar)


if __name__ == "__main__":
    main()
