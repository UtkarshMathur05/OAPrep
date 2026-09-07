"""C harness — the awkward one.

C has no containers, so LeetCode expands every array argument into several
parameters and returns arrays through out-params:

    int* twoSum(int* nums, int numsSize, int target, int* returnSize)
    int** merge(int** a, int aSize, int* aColSize, int* returnSize, int** returnColumnSizes)

That convention is not documented anywhere, so it was derived from the starters
and then checked against every C snippet in the corpus: **510 matched, 9 did
not**, and all nine turned out to be problems where `metaData` does not describe
the real function at all (`hasCycle` lists a `pos` argument that exists in no
language). Those are refused in ai.corpus.load_signatures rather than papered
over here.

Everything the caller allocates is leaked deliberately. The process runs one
test case and exits; a free() would only add a way to crash.
"""

from __future__ import annotations

SCALAR = {"integer": "int", "int": "int", "long": "long long", "double": "double",
          "boolean": "bool", "character": "char", "string": "char*"}
NODE = {"ListNode": "struct ListNode*", "TreeNode": "struct TreeNode*"}
# How to read one element out of the parsed JSON tree, per scalar type.
_READ = {"int": "(int)mz_ll({j}->num)", "long long": "(long long)mz_ll({j}->num)",
         "double": "{j}->num", "bool": "{j}->boolean", "char": "mz_char({j})",
         "char*": "mz_str({j})"}


def _peel(type_name: str) -> tuple[str, int]:
    name = (type_name or "").strip()
    depth = 0
    while True:
        if name.endswith("[]"):
            name, depth = name[:-2], depth + 1
        elif name.startswith("list<") and name.endswith(">"):
            name, depth = name[5:-1], depth + 1
        else:
            return name, depth


def _c_type(base: str, depth: int) -> str | None:
    """`integer`,2 -> `int**`. Strings already carry one star."""
    if base in NODE:
        # `ListNode[]` is `struct ListNode**` plus a size, the same expansion
        # every other array gets. Deeper nesting has no starter to copy, so it
        # is refused rather than guessed at.
        return NODE[base] + "*" * depth if depth <= 1 else None
    if base.lower() not in SCALAR:
        return None
    if depth > 2:
        return None
    return SCALAR[base.lower()] + "*" * depth


def supports(signature: dict) -> bool:
    if not signature or not signature.get("name") or signature.get("params") is None:
        return False
    for param in signature["params"]:
        base, depth = _peel(param.get("type", ""))
        if _c_type(base, depth) is None:
            return False
    ret = (signature.get("return") or {}).get("type", "")
    if ret.lower() == "void":
        return True
    base, depth = _peel(ret)
    if base in NODE and depth:
        return False  # returning an array of nodes: no convention, and none occurs
    return _c_type(base, depth) is not None


_PREAMBLE = r"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <ctype.h>
#include <math.h>
#include <limits.h>

/* Judge0 compiles C without -lm, so mz_ll() fails at link time. Rounding by
   hand costs nothing and removes the dependency entirely. */
static long long mz_ll(double v) { return (long long)(v < 0 ? v - 0.5 : v + 0.5); }

struct ListNode { int val; struct ListNode *next; };
struct TreeNode { int val; struct TreeNode *left; struct TreeNode *right; };

"""

_LIB = r"""

// ---------------------------------------------------------------------------
// Added by Memoize. Reads one JSON argument per line, calls your function, and
// prints what it returns. You never need to touch this.
typedef struct MzJ {
    enum { MZ_NUL, MZ_NUM, MZ_STR, MZ_BOOL, MZ_ARR } kind;
    double num;
    char *str;
    bool boolean;
    struct MzJ **arr;
    int len;
} MzJ;

static const char *mz_p;

static MzJ *mz_value(void);

static void mz_skip(void) { while (*mz_p && isspace((unsigned char)*mz_p)) mz_p++; }

static MzJ *mz_new(int kind) {
    MzJ *j = (MzJ *)calloc(1, sizeof(MzJ));
    j->kind = kind;
    return j;
}

static MzJ *mz_array(void) {
    MzJ *j = mz_new(MZ_ARR);
    int cap = 8;
    j->arr = (MzJ **)malloc(sizeof(MzJ *) * cap);
    mz_p++;                                  /* '[' */
    mz_skip();
    if (*mz_p == ']') { mz_p++; return j; }
    for (;;) {
        if (j->len == cap) { cap *= 2; j->arr = (MzJ **)realloc(j->arr, sizeof(MzJ *) * cap); }
        j->arr[j->len++] = mz_value();
        mz_skip();
        char c = *mz_p++;
        if (c == ']' || c == '\0') break;
    }
    return j;
}

static MzJ *mz_string(void) {
    MzJ *j = mz_new(MZ_STR);
    mz_p++;                                  /* opening quote */
    const char *start = mz_p;
    int len = 0;
    for (const char *q = start; *q && *q != '"'; q++, len++) if (*q == '\\') q++;
    j->str = (char *)malloc(len + 1);
    int i = 0;
    while (*mz_p && *mz_p != '"') {
        char c = *mz_p++;
        if (c == '\\' && *mz_p) {
            char e = *mz_p++;
            if (e == 'n') c = '\n';
            else if (e == 't') c = '\t';
            else if (e == 'r') c = '\r';
            else c = e;
        }
        j->str[i++] = c;
    }
    j->str[i] = '\0';
    if (*mz_p == '"') mz_p++;
    return j;
}

static MzJ *mz_value(void) {
    mz_skip();
    if (*mz_p == '[') return mz_array();
    if (*mz_p == '"') return mz_string();
    if (!strncmp(mz_p, "true", 4))  { mz_p += 4; MzJ *j = mz_new(MZ_BOOL); j->boolean = true;  return j; }
    if (!strncmp(mz_p, "false", 5)) { mz_p += 5; MzJ *j = mz_new(MZ_BOOL); j->boolean = false; return j; }
    if (!strncmp(mz_p, "null", 4))  { mz_p += 4; return mz_new(MZ_NUL); }
    MzJ *j = mz_new(MZ_NUM);
    char *end;
    j->num = strtod(mz_p, &end);
    mz_p = end;
    return j;
}

static MzJ *mz_parse(const char *text) { mz_p = text; return mz_value(); }

static char *mz_str(MzJ *j)  { return j->str ? j->str : (char *)""; }
static char  mz_char(MzJ *j) { return j->str && j->str[0] ? j->str[0] : '\0'; }

static struct ListNode *mz_to_list(MzJ *j) {
    struct ListNode *head = NULL, *tail = NULL;
    for (int i = 0; i < j->len; i++) {
        struct ListNode *n = (struct ListNode *)calloc(1, sizeof(struct ListNode));
        n->val = (int)mz_ll(j->arr[i]->num);
        if (!head) head = tail = n; else { tail->next = n; tail = n; }
    }
    return head;
}

static struct TreeNode *mz_to_tree(MzJ *j) {
    if (j->len == 0 || j->arr[0]->kind == MZ_NUL) return NULL;
    struct TreeNode **q = (struct TreeNode **)malloc(sizeof(struct TreeNode *) * (j->len + 1));
    int head = 0, tail = 0;
    struct TreeNode *root = (struct TreeNode *)calloc(1, sizeof(struct TreeNode));
    root->val = (int)mz_ll(j->arr[0]->num);
    q[tail++] = root;
    int i = 1;
    while (head < tail && i < j->len) {
        struct TreeNode *node = q[head++];
        if (i < j->len) {
            if (j->arr[i]->kind != MZ_NUL) {
                struct TreeNode *l = (struct TreeNode *)calloc(1, sizeof(struct TreeNode));
                l->val = (int)mz_ll(j->arr[i]->num);
                node->left = l; q[tail++] = l;
            }
            i++;
        }
        if (i < j->len) {
            if (j->arr[i]->kind != MZ_NUL) {
                struct TreeNode *r = (struct TreeNode *)calloc(1, sizeof(struct TreeNode));
                r->val = (int)mz_ll(j->arr[i]->num);
                node->right = r; q[tail++] = r;
            }
            i++;
        }
    }
    return root;
}

/* ----------------------------------------------------------------- JSON out */
static void mz_quote(const char *s) {
    putchar('"');
    for (; *s; s++) {
        if (*s == '"' || *s == '\\') { putchar('\\'); putchar(*s); }
        else if (*s == '\n') printf("\\n");
        else if (*s == '\t') printf("\\t");
        else putchar(*s);
    }
    putchar('"');
}

static void mz_list_out(struct ListNode *n) {
    putchar('[');
    for (int first = 1; n; n = n->next, first = 0) {
        if (!first) putchar(',');
        printf("%d", n->val);
    }
    putchar(']');
}

static void mz_tree_out(struct TreeNode *root) {
    if (!root) { printf("[]"); return; }
    int cap = 1024, head = 0, tail = 0;
    struct TreeNode **q = (struct TreeNode **)malloc(sizeof(struct TreeNode *) * cap);
    int *vals = (int *)malloc(sizeof(int) * cap);
    bool *nul = (bool *)malloc(sizeof(bool) * cap);
    int n = 0;
    q[tail++] = root;
    while (head < tail) {
        struct TreeNode *node = q[head++];
        if (n + 1 >= cap) {
            cap *= 2;
            q = (struct TreeNode **)realloc(q, sizeof(struct TreeNode *) * cap);
            vals = (int *)realloc(vals, sizeof(int) * cap);
            nul = (bool *)realloc(nul, sizeof(bool) * cap);
        }
        if (!node) { nul[n] = true; vals[n++] = 0; continue; }
        nul[n] = false; vals[n++] = node->val;
        q[tail++] = node->left;
        q[tail++] = node->right;
    }
    while (n > 0 && nul[n - 1]) n--;
    putchar('[');
    for (int i = 0; i < n; i++) {
        if (i) putchar(',');
        if (nul[i]) printf("null"); else printf("%d", vals[i]);
    }
    putchar(']');
}

static char *mz_line(void) {
    size_t cap = 1024, len = 0;
    char *buf = (char *)malloc(cap);
    int c;
    while ((c = getchar()) != EOF && c != '\n') {
        if (len + 1 >= cap) { cap *= 2; buf = (char *)realloc(buf, cap); }
        buf[len++] = (char)c;
    }
    buf[len] = '\0';
    return buf;
}

int main(void) {
__BODY__
    putchar('\n');
    return 0;
}
"""


def _read_arg(index: int, param: dict) -> list[str]:
    """Declare and fill one argument, expanding arrays into C's extra params."""
    name, ptype = f"a{index}", param.get("type", "")
    base, depth = _peel(ptype)
    out = [f'    MzJ *j{index} = mz_parse(mz_line());']

    if base in NODE:
        builder = "mz_to_list" if base == "ListNode" else "mz_to_tree"
        if depth == 0:
            out.append(f"    {NODE[base]} {name} = {builder}(j{index});")
            return out
        # An array of nodes: one chain per row, plus the size C needs.
        out += [
            f"    int {name}Size = j{index}->len;",
            f"    {NODE[base]} *{name} = ({NODE[base]} *)malloc(sizeof({NODE[base]}) * "
            f"(j{index}->len ? j{index}->len : 1));",
            f"    for (int i = 0; i < j{index}->len; i++) "
            f"{name}[i] = {builder}(j{index}->arr[i]);",
        ]
        return out

    element = SCALAR[base.lower()]
    read = _READ[element]

    if depth == 0:
        out.append(f"    {element} {name} = {read.format(j=f'j{index}')};")
    elif depth == 1:
        out += [
            f"    int {name}Size = j{index}->len;",
            f"    {element} *{name} = ({element} *)malloc(sizeof({element}) * "
            f"(j{index}->len ? j{index}->len : 1));",
            f"    for (int i = 0; i < j{index}->len; i++) "
            f"{name}[i] = {read.format(j=f'j{index}->arr[i]')};",
        ]
    else:
        out += [
            f"    int {name}Size = j{index}->len;",
            f"    int *{name}ColSize = (int *)malloc(sizeof(int) * "
            f"(j{index}->len ? j{index}->len : 1));",
            f"    {element} **{name} = ({element} **)malloc(sizeof({element} *) * "
            f"(j{index}->len ? j{index}->len : 1));",
            f"    for (int i = 0; i < j{index}->len; i++) {{",
            f"        MzJ *row = j{index}->arr[i];",
            f"        {name}ColSize[i] = row->len;",
            f"        {name}[i] = ({element} *)malloc(sizeof({element}) * "
            "(row->len ? row->len : 1));",
            f"        for (int k = 0; k < row->len; k++) "
            f"{name}[i][k] = {read.format(j='row->arr[k]')};",
            "    }",
        ]
    return out


def _print_value(expr: str, base: str, depth: int, size: str, colsize: str) -> list[str]:
    """Emit the code that prints one C value as JSON."""
    if base in NODE:
        return [f"    {'mz_list_out' if base == 'ListNode' else 'mz_tree_out'}({expr});"]
    element = SCALAR[base.lower()]
    fmt = {"int": '"%d"', "long long": '"%lld"', "double": '"%.10g"'}.get(element)

    def scalar(item: str) -> str:
        if element == "char*":
            return f"mz_quote({item});"
        if element == "char":
            return f'{{ char _t[2] = {{{item}, 0}}; mz_quote(_t); }}'
        if element == "bool":
            return f'printf("%s", ({item}) ? "true" : "false");'
        return f"printf({fmt}, {item});"

    if depth == 0:
        return ["    " + scalar(expr)]
    if depth == 1:
        return [
            "    putchar('[');",
            f"    for (int i = 0; i < {size}; i++) {{",
            "        if (i) putchar(',');",
            "        " + scalar(f"{expr}[i]"),
            "    }",
            "    putchar(']');",
        ]
    return [
        "    putchar('[');",
        f"    for (int i = 0; i < {size}; i++) {{",
        "        if (i) putchar(',');",
        "        putchar('[');",
        f"        for (int k = 0; k < {colsize}[i]; k++) {{",
        "            if (k) putchar(',');",
        "            " + scalar(f"{expr}[i][k]"),
        "        }",
        "        putchar(']');",
        "    }",
        "    putchar(']');",
    ]


def build(signature: dict, code: str) -> str:
    params = signature.get("params") or []
    ret = (signature.get("return") or {}).get("type", "")

    body: list[str] = []
    for index, param in enumerate(params):
        body += _read_arg(index, param)

    names: list[str] = []
    for index, param in enumerate(params):
        base, depth = _peel(param.get("type", ""))
        names.append(f"a{index}")
        if not (base in NODE and depth == 0) and depth >= 1:
            names.append(f"a{index}Size")
            if depth == 2:
                names.append(f"a{index}ColSize")

    is_void = ret.lower() == "void"
    rbase, rdepth = _peel(ret)

    # An array return hands its length back through out-params, exactly as the
    # starter's signature declares them.
    if not is_void and rdepth >= 1 and rbase not in NODE:
        body.append("    int _rsize = 0;")
        names.append("&_rsize")
        if rdepth == 2:
            body.append("    int *_rcols = NULL;")
            names.append("&_rcols")

    call = f"{signature['name']}({', '.join(names)})"

    if is_void:
        body.append(f"    {call};")
        # The answer is the mutated first argument.
        base, depth = _peel(params[0]["type"]) if params else ("integer", 0)
        body += _print_value("a0", base, depth, "a0Size", "a0ColSize")
    else:
        rtype = _c_type(rbase, rdepth)
        body.append(f"    {rtype} _r = {call};")
        body += _print_value("_r", rbase, rdepth, "_rsize", "_rcols")

    return _PREAMBLE + code.rstrip() + "\n" + _LIB.replace("__BODY__", "\n".join(body))
