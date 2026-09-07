"""C++ harness.

C++ has no reflection, so unlike Java the argument types cannot be read off the
method. They come from LeetCode's `metaData` instead, and the call site is
generated: declare each argument at its concrete type, fill it from the parsed
JSON, then call. The conversion and serialisation library below is fixed; only
the dozen lines of `main` differ per problem.

Judge0 offers a bare toolchain — no nlohmann/json, no Boost — so the JSON parser
is hand-written, as it is for Java.
"""

from __future__ import annotations

_SCALAR_CPP = {
    "integer": "int", "int": "int",
    "long": "long long",
    "double": "double",
    "boolean": "bool",
    "string": "string",
    "character": "char",
}
STRUCTURED = {"ListNode": "ListNode*", "TreeNode": "TreeNode*"}


def _peel(type_name: str) -> tuple[str, int]:
    """Return (element type, container depth). `list<list<integer>>` -> (integer, 2)."""
    name = (type_name or "").strip()
    depth = 0
    while True:
        if name.endswith("[]"):
            name, depth = name[:-2], depth + 1
        elif name.startswith("list<") and name.endswith(">"):
            name, depth = name[5:-1], depth + 1
        else:
            return name, depth


def cpp_type(type_name: str) -> str | None:
    """The C++ declaration for a LeetCode type, or None if we cannot express it."""
    base, depth = _peel(type_name)
    lowered = base.lower()
    if base in STRUCTURED:
        # A list of nodes is `vector<ListNode*>`, which is rare but valid.
        inner = STRUCTURED[base]
    elif lowered in _SCALAR_CPP:
        inner = _SCALAR_CPP[lowered]
    else:
        return None
    for _ in range(depth):
        inner = f"vector<{inner}>"
    return inner


def supports(signature: dict) -> bool:
    if not signature or not signature.get("name"):
        return False
    if signature.get("params") is None:
        return False
    for param in signature["params"]:
        if cpp_type(param.get("type", "")) is None:
            return False
    ret = (signature.get("return") or {}).get("type", "")
    return ret.lower() == "void" or cpp_type(ret) is not None


_PREAMBLE = r"""#include <bits/stdc++.h>
using namespace std;

struct ListNode {
    int val; ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *n) : val(x), next(n) {}
};

struct TreeNode {
    int val; TreeNode *left; TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *l, TreeNode *r) : val(x), left(l), right(r) {}
};

"""

_LIB = r"""

// ---------------------------------------------------------------------------
// Added by Memoize. Reads one JSON argument per line, calls your method, and
// prints what it returns. You never need to touch this.
namespace mz {

struct J {
    enum Kind { NUL, NUM, STR, BOOL, ARR } kind = NUL;
    double num = 0;
    string str;
    bool boolean = false;
    vector<J> arr;
};

struct Parser {
    const string &s; size_t i = 0;
    explicit Parser(const string &src) : s(src) {}
    void skip() { while (i < s.size() && isspace((unsigned char)s[i])) i++; }
    J value() {
        skip();
        if (i >= s.size()) return J{};
        char c = s[i];
        if (c == '[') return array();
        if (c == '"') return str();
        if (!s.compare(i, 4, "true"))  { i += 4; J j; j.kind = J::BOOL; j.boolean = true;  return j; }
        if (!s.compare(i, 5, "false")) { i += 5; J j; j.kind = J::BOOL; j.boolean = false; return j; }
        if (!s.compare(i, 4, "null"))  { i += 4; return J{}; }
        return num();
    }
    J array() {
        J j; j.kind = J::ARR; i++; skip();
        if (i < s.size() && s[i] == ']') { i++; return j; }
        while (true) {
            j.arr.push_back(value());
            skip();
            if (i >= s.size()) break;
            char c = s[i++];
            if (c == ']') break;
        }
        return j;
    }
    J str() {
        J j; j.kind = J::STR; i++;
        while (i < s.size() && s[i] != '"') {
            char c = s[i++];
            if (c == '\\' && i < s.size()) {
                char e = s[i++];
                switch (e) {
                    case 'n': j.str += '\n'; break;
                    case 't': j.str += '\t'; break;
                    case 'r': j.str += '\r'; break;
                    default:  j.str += e;
                }
            } else j.str += c;
        }
        i++;
        return j;
    }
    J num() {
        size_t start = i;
        while (i < s.size() && (isdigit((unsigned char)s[i]) || strchr("+-.eE", s[i]))) i++;
        J j; j.kind = J::NUM; j.num = strtod(s.substr(start, i - start).c_str(), nullptr);
        return j;
    }
};

inline J parse(const string &text) { Parser p(text); return p.value(); }

// ------------------------------------------------------------ J -> C++ types
inline void from(const J &j, int &out)       { out = (int)llround(j.num); }
inline void from(const J &j, long long &out) { out = (long long)llround(j.num); }
inline void from(const J &j, double &out)    { out = j.num; }
inline void from(const J &j, bool &out)      { out = j.boolean; }
inline void from(const J &j, string &out)    { out = j.str; }
inline void from(const J &j, char &out)      { out = j.str.empty() ? '\0' : j.str[0]; }

template <class T>
inline void from(const J &j, vector<T> &out) {
    out.clear();
    out.reserve(j.arr.size());
    for (const J &item : j.arr) { T v{}; from(item, v); out.push_back(v); }
}

inline void from(const J &j, ListNode *&out) {
    out = nullptr; ListNode *tail = nullptr;
    for (const J &item : j.arr) {
        ListNode *node = new ListNode((int)llround(item.num));
        if (!out) out = tail = node; else { tail->next = node; tail = node; }
    }
}

inline void from(const J &j, TreeNode *&out) {
    out = nullptr;
    if (j.arr.empty() || j.arr[0].kind == J::NUL) return;
    out = new TreeNode((int)llround(j.arr[0].num));
    queue<TreeNode *> q; q.push(out);
    size_t i = 1;
    while (!q.empty() && i < j.arr.size()) {
        TreeNode *node = q.front(); q.pop();
        if (i < j.arr.size()) {
            if (j.arr[i].kind != J::NUL) { node->left = new TreeNode((int)llround(j.arr[i].num)); q.push(node->left); }
            i++;
        }
        if (i < j.arr.size()) {
            if (j.arr[i].kind != J::NUL) { node->right = new TreeNode((int)llround(j.arr[i].num)); q.push(node->right); }
            i++;
        }
    }
}

// ------------------------------------------------------------------ JSON out
inline string quote(const string &s) {
    string out = "\"";
    for (char c : s) {
        if (c == '"' || c == '\\') { out += '\\'; out += c; }
        else if (c == '\n') out += "\\n";
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    return out + "\"";
}

inline string ser(int v)       { return to_string(v); }
inline string ser(long long v) { return to_string(v); }
inline string ser(bool v)      { return v ? "true" : "false"; }
inline string ser(char v)      { return quote(string(1, v)); }
inline string ser(const string &v) { return quote(v); }
inline string ser(double v) {
    ostringstream os; os << setprecision(10) << v; return os.str();
}

template <class T>
inline string ser(const vector<T> &v) {
    string out = "[";
    for (size_t i = 0; i < v.size(); i++) { if (i) out += ','; out += ser(v[i]); }
    return out + "]";
}

inline string ser(ListNode *node) {
    vector<int> out;
    for (; node; node = node->next) out.push_back(node->val);
    return ser(out);
}

inline string ser(TreeNode *root) {
    if (!root) return "[]";
    vector<string> out;
    queue<TreeNode *> q; q.push(root);
    while (!q.empty()) {
        TreeNode *node = q.front(); q.pop();
        if (!node) { out.push_back("null"); continue; }
        out.push_back(to_string(node->val));
        q.push(node->left); q.push(node->right);
    }
    while (!out.empty() && out.back() == "null") out.pop_back();
    string s = "[";
    for (size_t i = 0; i < out.size(); i++) { if (i) s += ','; s += out[i]; }
    return s + "]";
}

inline vector<string> lines() {
    vector<string> out; string line;
    while (getline(cin, line)) out.push_back(line);
    return out;
}

}  // namespace mz

int main() {
    ios::sync_with_stdio(false);
    vector<string> _in = mz::lines();
    Solution _sol;
__BODY__
    return 0;
}
"""


def build(signature: dict, code: str) -> str:
    params = signature.get("params") or []
    ret = (signature.get("return") or {}).get("type", "")

    body = []
    for index, param in enumerate(params):
        declared = cpp_type(param["type"])
        body.append(f"    {declared} a{index}{{}};")
        body.append(f"    mz::from(mz::parse(_in[{index}]), a{index});")
    call_args = ", ".join(f"a{i}" for i in range(len(params)))
    call = f"_sol.{signature['name']}({call_args})"

    if ret.lower() == "void":
        # The answer is the mutated first argument, not the (absent) return.
        body.append(f"    {call};")
        body.append("    cout << mz::ser(a0) << endl;")
    else:
        body.append(f"    auto _r = {call};")
        body.append("    cout << mz::ser(_r) << endl;")

    return _PREAMBLE + code.rstrip() + "\n" + _LIB.replace("__BODY__", "\n".join(body))
