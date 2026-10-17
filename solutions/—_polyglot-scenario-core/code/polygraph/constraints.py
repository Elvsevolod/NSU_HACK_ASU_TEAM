"""A small semantic bridge to Z3, not a second hand-written solver.

Only UNSAT eliminates a branch. Unknown, timeouts and unsupported encodings
preserve both outcomes. Floating-point, strings and nullable references are
deliberately outside this integer/boolean encoding.
"""
import operator
from time import perf_counter

import z3

from .values import Formula, Symbol


class PathSolver:
    def __init__(self, enabled=True, timeout_ms=50):
        self.enabled = enabled
        self.solver = z3.Solver() if enabled else None
        if enabled:
            self.solver.set(timeout=timeout_ms)
        self.statistics = {"checks": 0, "pruned_outcomes": 0, "unknown": 0, "seconds": 0.0}
        self.failures = []
        self.terms = {}

    @staticmethod
    def coerce(value, sort):
        if sort == "bool":
            if type(value) is bool:
                return z3.BoolVal(value)
            if z3.is_bool(value):
                return value
            raise ValueError("non-boolean in boolean formula")
        if type(value) is bool:
            value = int(value)
        if sort.startswith("bv"):
            width = int(sort[2:])
            if type(value) is int:
                return z3.BitVecVal(value, width)
            if z3.is_int(value):
                return z3.Int2BV(value, width)
            if z3.is_bv(value):
                return z3.SignExt(width - value.size(), value) if value.size() < width else z3.Extract(width - 1, 0, value) if value.size() > width else value
        if sort == "int":
            if type(value) is int:
                return z3.IntVal(value)
            if z3.is_int(value):
                return value
            if z3.is_bv(value):
                return z3.BV2Int(value, is_signed=True)
        raise ValueError("unsupported solver coercion to " + sort)

    def term(self, value):
        if not isinstance(value, (Symbol, Formula)):
            return value
        if value in self.terms:
            return self.terms[value]
        if isinstance(value, Symbol):
            if value.sort == "bool":
                result = z3.Bool(value.identity)
            elif value.sort == "int":
                result = z3.Int(value.identity)
            elif value.sort in {"bv32", "bv64"}:
                result = z3.BitVec(value.identity, int(value.sort[2:]))
            else:
                raise ValueError("unsupported symbolic sort " + value.sort)
        elif value.op.startswith("cast:"):
            width = int(value.op.split(":")[1])
            result = self.coerce(self.term(value.args[0]), "bv" + str(width))
            result = self.coerce(result, value.sort)
        else:
            comparisons = {"==", "!=", ">", "<", ">=", "<="}
            sort = value.sort
            if value.op in comparisons:
                sorts = {getattr(arg, "sort", "") for arg in value.args}
                sort = value.operand_sort or ("bool" if "bool" in sorts else "bv64" if value.language == "java" and "bv64" in sorts else "bv32" if value.language == "java" else "int")
            left, right = (self.coerce(self.term(arg), sort) for arg in value.args)
            if value.op in {"/", "//", "%"} and sort.startswith("bv"):
                result = z3.SRem(left, right) if value.op == "%" else left / right
            elif value.op in {"//", "%"}:
                # Z3 integer division is Euclidean; Python floors toward -inf.
                quotient = z3.If(right > 0, left / right, (-left) / (-right))
                result = left - right * quotient if value.op == "%" else quotient
            elif value.op in {"<<", ">>", ">>>"}:
                if not sort.startswith("bv"):
                    raise ValueError("symbolic Python shifts are not encoded")
                amount = right & (63 if sort == "bv64" else 31)
                result = left << amount if value.op == "<<" else z3.LShR(left, amount) if value.op == ">>>" else left >> amount
            else:
                operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                              "==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt,
                              ">=": operator.ge, "<=": operator.le, "&": operator.and_, "|": operator.or_, "^": operator.xor}
                if value.op not in operations:
                    raise ValueError("unsupported solver operation " + value.op)
                result = operations[value.op](left, right)
        self.terms[value] = result
        return result

    def predicate(self, value):
        result = self.term(value)
        return result if z3.is_bool(result) else result != 0 if z3.is_int(result) or z3.is_bv(result) else None

    def outcomes(self, value):
        if not self.enabled:
            return (False, True), None
        try:
            predicate = self.predicate(value)
            if predicate is None:
                return (False, True), None
            feasible = []
            for outcome in (False, True):
                self.solver.push()
                try:
                    self.solver.add(predicate if outcome else z3.Not(predicate))
                    start = perf_counter()
                    result = self.solver.check()
                    self.statistics["seconds"] += perf_counter() - start
                    self.statistics["checks"] += 1
                    if result == z3.unsat:
                        self.statistics["pruned_outcomes"] += 1
                    else:
                        feasible.append(outcome)
                        if result == z3.unknown:
                            self.statistics["unknown"] += 1
                            self.failures.append(self.solver.reason_unknown())
                finally:
                    self.solver.pop()
            return tuple(feasible), predicate
        except (ValueError, TypeError, z3.Z3Exception) as exc:
            self.statistics["unknown"] += 1
            self.failures.append(str(exc))
            return (False, True), None

    def assume(self, predicate, outcome):
        if predicate is not None and self.enabled:
            self.solver.add(predicate if outcome else z3.Not(predicate))
