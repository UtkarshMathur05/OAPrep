"""The languages a solution can be written in.

Multi-language is nearly free here, and the reason is a decision made early:
**the contract is a whole program over stdin/stdout, not a function signature.**
CLAUDE.md §9 assumed each language would need its own driver to parse stdin,
call a named function and print the result — that is true for a LeetCode-shaped
signature, and it is what makes multi-language expensive. Because a solution
here is just "read stdin, print the answer", a new language costs one Judge0 id
and one starter template, and the test cases do not change at all.

Judge0 ids come from `GET {JUDGE0_URL}/languages`. They are pinned to specific
compiler versions on CE, so they are recorded here rather than looked up.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    id: str          # our stable key, used in the API and stored on submissions
    label: str       # shown in the picker
    judge0_id: int
    monaco: str      # Monaco's own language id, for syntax highlighting
    starter: str     # a whole program that reads stdin and prints an answer


_PYTHON = '''import sys

def main():
    data = sys.stdin.read().split()
    # your solution here
    print(0)

if __name__ == "__main__":
    main()
'''

_JAVASCRIPT = '''const data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/);

// your solution here
console.log(0);
'''

_TYPESCRIPT = '''declare const require: any;

const data: string[] = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/);

// your solution here
console.log(0);
'''

# Judge0 compiles the file as Main.java, so the public class must be Main.
_JAVA = '''import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line).append(' ');
        StringTokenizer st = new StringTokenizer(sb.toString());

        // your solution here
        System.out.println(0);
    }
}
'''

_CPP = '''#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // your solution here
    cout << 0 << "\\n";
    return 0;
}
'''

_C = '''#include <stdio.h>

int main(void) {
    /* your solution here */
    printf("%d\\n", 0);
    return 0;
}
'''

_GO = '''package main

import (
\t"bufio"
\t"fmt"
\t"os"
)

func main() {
\treader := bufio.NewReader(os.Stdin)
\twriter := bufio.NewWriter(os.Stdout)
\tdefer writer.Flush()
\t_ = reader

\t// your solution here
\tfmt.Fprintln(writer, 0)
}
'''

_KOTLIN = '''fun main() {
    val data = generateSequence(::readLine).joinToString(" ").trim().split(Regex("\\\\s+"))

    // your solution here
    println(0)
}
'''

_RUBY = '''data = $stdin.read.split

# your solution here
puts 0
'''

_RUST = '''use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let _data: Vec<&str> = input.split_whitespace().collect();

    // your solution here
    println!("{}", 0);
}
'''

_CSHARP = '''using System;

class Program {
    static void Main() {
        string input = Console.In.ReadToEnd();

        // your solution here
        Console.WriteLine(0);
    }
}
'''


LANGUAGES: list[Language] = [
    Language("python",     "Python 3",   71, "python",     _PYTHON),
    Language("cpp",        "C++",        54, "cpp",        _CPP),
    Language("java",       "Java",       62, "java",       _JAVA),
    Language("javascript", "JavaScript", 63, "javascript", _JAVASCRIPT),
    Language("c",          "C",          50, "c",          _C),
    Language("go",         "Go",         60, "go",         _GO),
    Language("csharp",     "C#",         51, "csharp",     _CSHARP),
    Language("kotlin",     "Kotlin",     78, "kotlin",     _KOTLIN),
    Language("ruby",       "Ruby",       72, "ruby",       _RUBY),
    Language("rust",       "Rust",       73, "rust",       _RUST),
    Language("typescript", "TypeScript", 74, "typescript", _TYPESCRIPT),
]

BY_ID: dict[str, Language] = {lang.id: lang for lang in LANGUAGES}

DEFAULT = "python"


def get(language_id: str) -> Language | None:
    return BY_ID.get((language_id or "").strip().lower())
