"""Java harness.

Judge0 compiles the submission as `Main.java`, so the entry point must be
`public class Main` and the person's `class Solution` rides alongside it in the
same file — which is legal exactly as long as Solution is not itself public.

Arguments are converted by **reflection**, not by switching on LeetCode's type
strings. `getGenericParameterTypes()` reports what the method actually declares,
including the type arguments of a `List<List<Integer>>`, so one recursive
converter covers every problem instead of an enumeration that has to be extended
each time a new shape appears. The type strings are still used for `supports`,
because that has to answer before any code exists.

There is no JSON parser in the Java standard library and Judge0 offers no jars,
so the parser below is hand-written. It is small because the input is small: the
values are always the literals from the problem's own examples.
"""

from __future__ import annotations

SCALARS = {"integer", "long", "double", "string", "boolean", "character", "void"}
STRUCTURED = {"ListNode", "TreeNode"}


def _base(type_name: str) -> str:
    name = (type_name or "").strip()
    while True:
        if name.endswith("[]"):
            name = name[:-2]
        elif name.startswith("list<") and name.endswith(">"):
            name = name[5:-1]
        else:
            return name


def supports(signature: dict) -> bool:
    if not signature or not signature.get("name"):
        return False
    types = [p.get("type", "") for p in signature.get("params") or []]
    types.append((signature.get("return") or {}).get("type", ""))
    for t in types:
        base = _base(t)
        if base.lower() in SCALARS or base in STRUCTURED:
            continue
        return False
    return signature.get("params") is not None


_PREAMBLE = """import java.util.*;
import java.io.*;
import java.lang.reflect.*;

class ListNode {
    int val; ListNode next;
    ListNode() {}
    ListNode(int v) { val = v; }
    ListNode(int v, ListNode n) { val = v; next = n; }
}

class TreeNode {
    int val; TreeNode left, right;
    TreeNode() {}
    TreeNode(int v) { val = v; }
    TreeNode(int v, TreeNode l, TreeNode r) { val = v; left = l; right = r; }
}

"""

_RUNNER = """

// ---------------------------------------------------------------------------
// Added by Memoize. Reads one JSON argument per line, calls your method, and
// prints what it returns. You never need to touch this.
public class Main {

    // ------------------------------------------------------------- JSON in
    private static String src;
    private static int pos;

    static Object parse(String text) {
        src = text; pos = 0;
        skip();
        return value();
    }

    private static void skip() {
        while (pos < src.length() && Character.isWhitespace(src.charAt(pos))) pos++;
    }

    private static Object value() {
        skip();
        char c = src.charAt(pos);
        if (c == '[') return array();
        if (c == '"') return string();
        if (src.startsWith("true", pos)) { pos += 4; return Boolean.TRUE; }
        if (src.startsWith("false", pos)) { pos += 5; return Boolean.FALSE; }
        if (src.startsWith("null", pos)) { pos += 4; return null; }
        return number();
    }

    private static List<Object> array() {
        List<Object> out = new ArrayList<>();
        pos++;                                  // '['
        skip();
        if (pos < src.length() && src.charAt(pos) == ']') { pos++; return out; }
        while (true) {
            out.add(value());
            skip();
            char c = src.charAt(pos++);
            if (c == ']') return out;
            // anything other than ',' here means malformed input, which can
            // only come from us, so let it fail loudly rather than guessing.
        }
    }

    private static String string() {
        StringBuilder sb = new StringBuilder();
        pos++;                                  // opening quote
        while (src.charAt(pos) != '"') {
            char c = src.charAt(pos++);
            if (c == '\\\\') {
                char e = src.charAt(pos++);
                switch (e) {
                    case 'n': sb.append('\\n'); break;
                    case 't': sb.append('\\t'); break;
                    case 'r': sb.append('\\r'); break;
                    case 'b': sb.append('\\b'); break;
                    case 'f': sb.append('\\f'); break;
                    case 'u':
                        sb.append((char) Integer.parseInt(src.substring(pos, pos + 4), 16));
                        pos += 4;
                        break;
                    default: sb.append(e);
                }
            } else {
                sb.append(c);
            }
        }
        pos++;                                  // closing quote
        return sb.toString();
    }

    private static Object number() {
        int start = pos;
        while (pos < src.length() && "+-.eE0123456789".indexOf(src.charAt(pos)) >= 0) pos++;
        String text = src.substring(start, pos);
        if (text.contains(".") || text.contains("e") || text.contains("E")) {
            return Double.parseDouble(text);
        }
        return Long.parseLong(text);
    }

    // -------------------------------------------------------- JSON -> types
    @SuppressWarnings("unchecked")
    static Object convert(Object v, Type t) {
        if (t instanceof ParameterizedType) {
            ParameterizedType p = (ParameterizedType) t;
            Type arg = p.getActualTypeArguments()[0];
            List<Object> src = (List<Object>) v;
            List<Object> out = new ArrayList<>();
            for (Object item : src) out.add(convert(item, arg));
            return out;
        }

        Class<?> c = (Class<?>) t;
        if (c.isArray()) {
            List<Object> src = (List<Object>) v;
            Class<?> element = c.getComponentType();
            Object out = Array.newInstance(element, src.size());
            for (int i = 0; i < src.size(); i++) Array.set(out, i, convert(src.get(i), element));
            return out;
        }
        if (c == ListNode.class) return toList((List<Object>) v);
        if (c == TreeNode.class) return toTree((List<Object>) v);
        if (v == null) return null;
        if (c == int.class || c == Integer.class) return (int) ((Number) v).longValue();
        if (c == long.class || c == Long.class) return ((Number) v).longValue();
        if (c == double.class || c == Double.class) return ((Number) v).doubleValue();
        if (c == boolean.class || c == Boolean.class) return v;
        if (c == char.class || c == Character.class) return ((String) v).charAt(0);
        return v;                               // String, and anything already right
    }

    static ListNode toList(List<Object> values) {
        ListNode head = null, tail = null;
        if (values == null) return null;
        for (Object v : values) {
            ListNode node = new ListNode((int) ((Number) v).longValue());
            if (head == null) { head = tail = node; } else { tail.next = node; tail = node; }
        }
        return head;
    }

    static TreeNode toTree(List<Object> values) {
        if (values == null || values.isEmpty() || values.get(0) == null) return null;
        TreeNode root = new TreeNode((int) ((Number) values.get(0)).longValue());
        Deque<TreeNode> queue = new ArrayDeque<>();
        queue.add(root);
        int i = 1;
        while (!queue.isEmpty() && i < values.size()) {
            TreeNode node = queue.poll();
            if (i < values.size()) {
                Object v = values.get(i++);
                if (v != null) { node.left = new TreeNode((int) ((Number) v).longValue()); queue.add(node.left); }
            }
            if (i < values.size()) {
                Object v = values.get(i++);
                if (v != null) { node.right = new TreeNode((int) ((Number) v).longValue()); queue.add(node.right); }
            }
        }
        return root;
    }

    // ------------------------------------------------------------ JSON out
    static String ser(Object o) {
        if (o == null) return "null";
        if (o instanceof ListNode) return ser(fromList((ListNode) o));
        if (o instanceof TreeNode) return ser(fromTree((TreeNode) o));
        if (o instanceof String) return quote((String) o);
        if (o instanceof Character) return quote(o.toString());
        if (o instanceof Boolean || o instanceof Number) return o.toString();
        if (o instanceof Collection) {
            StringBuilder sb = new StringBuilder("[");
            boolean first = true;
            for (Object item : (Collection<?>) o) {
                if (!first) sb.append(',');
                sb.append(ser(item));
                first = false;
            }
            return sb.append(']').toString();
        }
        if (o.getClass().isArray()) {
            StringBuilder sb = new StringBuilder("[");
            int n = Array.getLength(o);
            for (int i = 0; i < n; i++) {
                if (i > 0) sb.append(',');
                sb.append(ser(Array.get(o, i)));
            }
            return sb.append(']').toString();
        }
        return quote(o.toString());
    }

    static String quote(String s) {
        StringBuilder sb = new StringBuilder("\\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': sb.append("\\\\\\""); break;
                case '\\\\': sb.append("\\\\\\\\"); break;
                case '\\n': sb.append("\\\\n"); break;
                case '\\t': sb.append("\\\\t"); break;
                case '\\r': sb.append("\\\\r"); break;
                default: sb.append(c);
            }
        }
        return sb.append('"').toString();
    }

    static List<Integer> fromList(ListNode node) {
        List<Integer> out = new ArrayList<>();
        while (node != null) { out.add(node.val); node = node.next; }
        return out;
    }

    static List<Integer> fromTree(TreeNode root) {
        List<Integer> out = new ArrayList<>();
        if (root == null) return out;
        // LinkedList, not ArrayDeque: this BFS pushes null children on purpose,
        // because a null is how a gap in the level order is written. ArrayDeque
        // rejects null elements, so it threw on every tree with a missing child.
        Deque<TreeNode> queue = new LinkedList<>();
        queue.add(root);
        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            if (node == null) { out.add(null); continue; }
            out.add(node.val);
            queue.add(node.left);
            queue.add(node.right);
        }
        while (!out.isEmpty() && out.get(out.size() - 1) == null) out.remove(out.size() - 1);
        return out;
    }

    // ---------------------------------------------------------------- main
    public static void main(String[] args) throws Exception {
        StringBuilder all = new StringBuilder();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        String line;
        while ((line = in.readLine()) != null) all.append(line).append('\\n');
        String[] lines = all.toString().split("\\n");

        Method target = null;
        for (Method m : Solution.class.getDeclaredMethods()) {
            if (m.getName().equals(METHOD)) { target = m; break; }
        }
        Type[] declared = target.getGenericParameterTypes();
        Object[] values = new Object[declared.length];
        for (int i = 0; i < declared.length; i++) {
            values[i] = convert(parse(lines[i]), declared[i]);
        }

        Object result = target.invoke(new Solution(), values);
        // A void problem mutates its first argument; that mutation is the answer.
        if (target.getReturnType() == void.class) result = values.length > 0 ? values[0] : null;
        // An empty list or tree is `[]`, not `null`.
        if (result == null && (target.getReturnType() == ListNode.class
                || target.getReturnType() == TreeNode.class)) result = new ArrayList<>();
        System.out.println(ser(result));
    }
}
"""


def build(signature: dict, code: str) -> str:
    # LeetCode's starter says `class Solution`, but people paste `public class
    # Solution` from an IDE often enough to matter — and Judge0 compiles this
    # file as Main.java, where a second public class is a compile error the
    # person cannot diagnose from the message.
    body = code.rstrip().replace("public class Solution", "class Solution")

    # Java requires every import before the first type declaration, and the
    # preamble declares ListNode/TreeNode above the person's code. So a pasted
    # solution that begins `import java.util.*;` -- which anything using a
    # HashMap does -- landed mid-file and failed to compile, pointing at a line
    # they did not write. Hoist their imports to the very top instead;
    # duplicating an import the preamble already has is legal.
    kept, hoisted = [], []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import "):
            hoisted.append(stripped)
        elif stripped.startswith("package "):
            pass  # Judge0 compiles a bare Main.java; a package declaration breaks it
        else:
            kept.append(line)
    body = "\n".join(kept)
    prefix = "\n".join(dict.fromkeys(hoisted))
    if prefix:
        prefix += "\n"

    name = signature["name"].replace('"', '')
    return f'{prefix}{_PREAMBLE}{body}\n\nclass _MzMeta {{ }}\n{_RUNNER.replace("METHOD", chr(34) + name + chr(34))}'
