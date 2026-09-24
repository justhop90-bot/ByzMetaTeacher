#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const contractOnly = process.argv.includes("--contract-only");
const controllerPath = path.resolve(
  process.argv[2] ?? path.join(repoRoot, "Basilisk", "Basilisk.per"),
);
const legacyValidatorPath = path.join(
  repoRoot,
  "validation",
  "repair-lifecycle-replay.js",
);

const source = fs.readFileSync(controllerPath, "utf8");

function stripComments(text) {
  let result = "";
  let inString = false;
  let escaped = false;
  let inComment = false;

  for (const ch of text) {
    if (inComment) {
      result += ch === "\n" ? "\n" : " ";
      if (ch === "\n") {
        inComment = false;
      }
      continue;
    }

    if (inString) {
      result += ch;
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
      continue;
    }

    if (ch === '"') {
      inString = true;
      result += ch;
    } else if (ch === ";") {
      inComment = true;
      result += " ";
    } else {
      result += ch;
    }
  }

  return result;
}

function maskStrings(text) {
  let result = "";
  let inString = false;
  let escaped = false;

  for (const ch of text) {
    if (inString) {
      result += ch === "\n" ? "\n" : " ";
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
      continue;
    }

    if (ch === '"') {
      inString = true;
      result += " ";
    } else {
      result += ch;
    }
  }

  return result;
}

function sanitizeStructure(text) {
  return maskStrings(stripComments(text));
}

function extractRules(text) {
  const rules = [];
  let cursor = 0;
  const sanitized = sanitizeStructure(text);
  while ((cursor = sanitized.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    const startLine = sanitized.slice(0, cursor).split("\n").length;
    assert.notEqual(
      end,
      -1,
      `[Missing closing parenthesis] defrule begins at line ${startLine} and is not closed`,
    );
    rules.push(sanitized.slice(cursor, end));
    cursor = end;
  }
  return rules;
}

function validateBalancedParens(text) {
  const sanitized = maskStrings(stripComments(text));
  const stack = [];
  let line = 1;
  let column = 0;

  const lineColumnAt = (offset) => {
    const prefix = sanitized.slice(0, offset);
    const lastNewline = prefix.lastIndexOf("\n");
    return {
      line: prefix.split("\n").length,
      column: offset - lastNewline,
    };
  };

  const headAtOpen = (offset) => {
    const match = sanitized
      .slice(offset + 1)
      .match(/^\s*([A-Za-z][A-Za-z0-9_-]*)/);
    return match ? match[1] : "<unknown>";
  };

  for (let index = 0; index < sanitized.length; index += 1) {
    const ch = sanitized[index];
    if (ch === "(") {
      const location = lineColumnAt(index);
      stack.push({
        head: headAtOpen(index),
        line: location.line,
        column: location.column,
      });
      continue;
    }
    if (ch === ")") {
      if (stack.length === 0) {
        assert.fail(
          "[Missing opening parenthesis] unexpected ')' at line " +
            line +
            ", column " +
            (column + 1),
        );
      }
      stack.pop();
    }
    if (ch === "\n") {
      line += 1;
      column = 0;
    } else {
      column += 1;
    }
  }

  if (stack.length > 0) {
    const opening = stack.at(-1);
    assert.fail(
      "[Missing closing parenthesis] expression '" +
        opening.head +
        "' opened at line " +
        opening.line +
        ", column " +
        opening.column +
        " remains unclosed",
    );
  }
}

function validateGoalFactSyntax(sourceText) {
  const sanitized = sanitizeStructure(sourceText);
  const invalidComparisons = [
    ...sanitized.matchAll(
      /\(goal\s+[A-Za-z][A-Za-z0-9_-]*\s+(>=|<=|>|<|!=)\s+/g,
    ),
  ];
  assert.equal(
    invalidComparisons.length,
    0,
    `[Goal syntax] goal facts accept exact equality only; use up-compare-goal for comparisons. Invalid forms found: ${invalidComparisons
      .map((match) => match[1])
      .join(", ")}`,
  );
}

function validateBooleanArity(text) {
  const sanitized = sanitizeStructure(text);
  const logicalArity = new Map([
    ["not", 1],
    ["and", 2],
    ["nand", 2],
    ["nor", 2],
    ["or", 2],
    ["xor", 2],
    ["xnor", 2],
  ]);
  let cursor = 0;
  while ((cursor = sanitized.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    assert.notEqual(end, -1, "[Boolean arity] unclosed defrule");
    const rule = sanitized.slice(cursor, end);
    const stack = [];
    let token = "";
    const flushToken = () => {
      if (!token) return;
      const frame = stack.at(-1);
      frame.items += 1;
      if (frame.items === 1) frame.head = token;
      token = "";
    };
    for (const ch of rule) {
      if (ch === "(") {
        flushToken();
        if (stack.length) stack.at(-1).items += 1;
        stack.push({ items: 0, head: null });
      } else if (ch === ")") {
        flushToken();
        const frame = stack.pop();
        const operands = frame.items - 1;
        const expected = logicalArity.get(frame.head);
        if (expected !== undefined) {
          assert.equal(
            operands,
            expected,
            `[Boolean arity] ${frame.head} has ${operands} operands; expected exactly ${expected}`,
          );
        }
      } else if (/\s/.test(ch)) {
        flushToken();
      } else {
        token += ch;
      }
    }
    cursor = end;
  }
}

function validateRuleStructure(sourceText) {
  const sanitized = sanitizeStructure(sourceText);
  let cursor = 0;

  while (cursor < sanitized.length) {
    while (cursor < sanitized.length && /\s/.test(sanitized[cursor])) cursor += 1;
    if (cursor >= sanitized.length) break;

    if (sanitized[cursor] === "#") {
      const newline = sanitized.indexOf("\n", cursor);
      cursor = newline === -1 ? sanitized.length : newline + 1;
      continue;
    }

    assert.equal(
      sanitized[cursor],
      "(",
      `[Top-level syntax] unexpected token near source offset ${cursor}; expected a top-level form`,
    );

    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }

    assert.notEqual(
      end,
      -1,
      `[Missing closing parenthesis] top-level form begins near source offset ${cursor} and is not closed`,
    );

    const form = sanitized.slice(cursor, end);
    const rawForm = sourceText.slice(cursor, end);
    const headMatch = form.match(/^\(\s*([A-Za-z][A-Za-z0-9_-]*)/);
    assert.ok(
      headMatch,
      `[Top-level syntax] could not identify form head near source offset ${cursor}`,
    );

    const head = headMatch[1];
    assert.ok(
      head === "defconst" || head === "defrule" || head === "include",
      `[Top-level syntax] unsupported top-level form '${head}' near source offset ${cursor}`,
    );

    if (head === "include") {
      const includeMatch = rawForm.match(
        /^\(\s*include\s+"([^"\\]*(?:\\.[^"\\]*)*)"\s*\)$/,
      );
      assert.ok(
        includeMatch,
        `[Include] include near source offset ${cursor} must contain exactly one quoted target`,
      );
      assert.ok(
        includeMatch[1].toLowerCase().endsWith(".xs"),
        `[Include] include near source offset ${cursor} must target a .xs file`,
      );
      cursor = end;
      continue;
    }
    if (head === "defrule") {
      const arrowPositions = [...form.matchAll(/=>/g)].map((match) => match.index);
      assert.equal(
        arrowPositions.length,
        1,
        `[Rule structure] defrule near source offset ${cursor} must contain exactly one => separator; found ${arrowPositions.length}`,
      );
      assert.ok(
        /\(/.test(form.slice(arrowPositions[0] + 2)),
        `[Rule structure] defrule near source offset ${cursor} has no action form after =>`,
      );
    }

    cursor = end;
  }
}


function parseStrictTopLevelForms(sourceText) {
  const text = stripComments(sourceText);

  const lineOf = (offset) => text.slice(0, offset).split("\n").length;
  const columnOf = (offset) => {
    const lastNewline = text.lastIndexOf("\n", offset - 1);
    return offset - lastNewline;
  };

  function skipWhitespace(index) {
    let cursor = index;
    while (cursor < text.length && /\s/.test(text[cursor])) cursor += 1;
    return cursor;
  }

  function readAtom(index) {
    if (text[index] === "\"") {
      const start = index;
      let cursor = index + 1;
      let escaped = false;
      while (cursor < text.length) {
        const ch = text[cursor];
        if (escaped) {
          escaped = false;
        } else if (ch === "\\") {
          escaped = true;
        } else if (ch === "\"") {
          return {
            kind: "atom",
            value: text.slice(start, cursor + 1),
            start,
            end: cursor + 1,
          };
        }
        cursor += 1;
      }
      assert.fail(
        "[Parser] unterminated quoted string opened at line " +
          lineOf(start) +
          ", column " +
          columnOf(start),
      );
    }

    let cursor = index;
    while (
      cursor < text.length &&
      !/\s/.test(text[cursor]) &&
      text[cursor] !== "(" &&
      text[cursor] !== ")"
    ) {
      cursor += 1;
    }
    return {
      kind: "atom",
      value: text.slice(index, cursor),
      start: index,
      end: cursor,
    };
  }

  function readExpression(start) {
    assert.equal(
      text[start],
      "(",
      "[Parser] internal expression parser expected '('",
    );
    const line = lineOf(start);
    const column = columnOf(start);
    let cursor = skipWhitespace(start + 1);

    if (cursor >= text.length) {
      assert.fail(
        "[Missing closing parenthesis] expression opened at line " +
          line +
          ", column " +
          column +
          " reaches end of file",
      );
    }
    if (text[cursor] === ")") {
      assert.fail(
        "[Parser] empty expression '()' at line " +
          line +
          ", column " +
          column,
      );
    }

    const headToken = readAtom(cursor);
    const head = headToken.value;
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(head)) {
      assert.fail(
        "[Parser] invalid expression head '" +
          head +
          "' at line " +
          line +
          ", column " +
          column,
      );
    }
    cursor = headToken.end;
    const args = [];

    while (cursor < text.length) {
      cursor = skipWhitespace(cursor);
      if (cursor >= text.length) {
        assert.fail(
          "[Missing closing parenthesis] expression '" +
            head +
            "' opened at line " +
            line +
            ", column " +
            column +
            " is not closed",
        );
      }
      if (text[cursor] === ")") {
        return {
          kind: "expression",
          head,
          args,
          line,
          column,
          start,
          end: cursor + 1,
        };
      }
      if (text[cursor] === "(") {
        const child = readExpression(cursor);
        args.push(child);
        cursor = child.end;
        continue;
      }
      const atom = readAtom(cursor);
      if (!atom.value) {
        assert.fail(
          "[Parser] empty atom in expression '" +
            head +
            "' at line " +
            line +
            ", column " +
            column,
        );
      }
      args.push(atom);
      cursor = atom.end;
    }

    assert.fail(
      "[Missing closing parenthesis] expression '" +
        head +
        "' opened at line " +
        line +
        ", column " +
        column +
        " is not closed",
    );
  }

  const forms = [];
  let cursor = 0;
  while (cursor < text.length) {
    cursor = skipWhitespace(cursor);
    if (cursor >= text.length) break;

    if (text[cursor] === "#") {
      const lineEnd = text.indexOf("\n", cursor);
      cursor = lineEnd === -1 ? text.length : lineEnd + 1;
      continue;
    }

    if (text[cursor] === ")") {
      assert.fail(
        "[Missing opening parenthesis] unexpected ')' at line " +
          lineOf(cursor) +
          ", column " +
          columnOf(cursor),
      );
    }
    if (text[cursor] !== "(") {
      assert.fail(
        "[Top-level syntax] stray token near line " +
          lineOf(cursor) +
          ", column " +
          columnOf(cursor) +
          ": " +
          text.slice(cursor, Math.min(text.length, cursor + 32)).trim(),
      );
    }

    const form = readExpression(cursor);
    forms.push(form);
    cursor = form.end;
  }

  return forms;
}

function validateParserGradeRuleStructure(sourceText) {
  const forms = parseStrictTopLevelForms(sourceText);
  const logicalArity = new Map([
    ["not", 1],
    ["and", 2],
    ["nand", 2],
    ["nor", 2],
    ["or", 2],
    ["xor", 2],
    ["xnor", 2],
  ]);

  assert.ok(forms.length > 0, "[Parser] no top-level forms found");

  const validateRuleExpression = (expr) => {
    if (logicalArity.has(expr.head)) {
      const expected = logicalArity.get(expr.head);
      assert.equal(
        expr.args.length,
        expected,
        "[Logical arity] " +
          expr.head +
          " at line " +
          expr.line +
          " has " +
          expr.args.length +
          " operands; expected exactly " +
          expected,
      );
      assert.ok(
        expr.args.every((arg) => arg.kind === "expression"),
        "[Rule syntax] " +
          expr.head +
          " at line " +
          expr.line +
          " must contain only fact expressions as operands",
      );
      for (const child of expr.args) validateRuleExpression(child);
      return;
    }

    for (const arg of expr.args) {
      assert.ok(
        arg.kind === "atom",
        "[Rule syntax] command '" +
          expr.head +
          "' at line " +
          expr.line +
          " contains a nested expression argument; command parameters must be atomic values",
      );
    }
  };

  const defconstAliases = new Map();
  for (const form of forms) {
    if (form.head !== "defconst") continue;
    const value = form.args[1]?.value;
    if (
      typeof value === "string" &&
      !value.startsWith('"') &&
      !/^-?\d+$/.test(value)
    ) {
      defconstAliases.set(form.args[0].value, value);
    }
  }

  const reportedAliasCycles = new Set();
  for (const start of defconstAliases.keys()) {
    const path = [];
    const seen = new Map();
    let current = start;
    while (defconstAliases.has(current)) {
      if (seen.has(current)) {
        const cycle = path.slice(seen.get(current));
        const key = [...cycle].sort().join("|");
        if (!reportedAliasCycles.has(key)) {
          reportedAliasCycles.add(key);
          assert.fail(
            "[Defconst] alias cycle " +
              [...cycle, current].join(" -> ") +
              " cannot resolve",
          );
        }
        break;
      }
      seen.set(current, path.length);
      path.push(current);
      current = defconstAliases.get(current);
    }
  }

  for (const form of forms) {
    if (form.head === "include") {
      assert.equal(
        form.args.length,
        1,
        "[Include] include at line " + form.line + " requires exactly one path",
      );
      assert.ok(
        form.args[0].kind === "atom" &&
          /^".+\.xs"$/.test(form.args[0].value),
        "[Include] include at line " + form.line + " must target a .xs file",
      );
      continue;
    }

    if (form.head === "defconst") {
      assert.equal(
        form.args.length,
        2,
        "[Defconst] defconst at line " +
          form.line +
          " requires exactly a name and one value",
      );
      assert.ok(
        form.args[0].kind === "atom" &&
          /^[A-Za-z][A-Za-z0-9_-]*$/.test(form.args[0].value) &&
          !form.args[0].value.startsWith("\""),
        "[Defconst] defconst at line " +
          form.line +
          " has an invalid constant name",
      );
      assert.ok(
        form.args[1].kind === "atom",
        "[Defconst] defconst at line " +
          form.line +
          " value must be a single integer, alias, or quoted string",
      );
      continue;
    }

    assert.equal(
      form.head,
      "defrule",
      "[Top-level syntax] unsupported top-level form '" +
        form.head +
        "' at line " +
        form.line,
    );

    const arrowIndexes = form.args
      .map((arg, index) => (arg.kind === "atom" && arg.value === "=>" ? index : -1))
      .filter((index) => index >= 0);

    assert.equal(
      arrowIndexes.length,
      1,
      "[Rule structure] defrule at line " +
        form.line +
        " must contain exactly one direct => separator; found " +
        arrowIndexes.length,
    );

    const arrowIndex = arrowIndexes[0];
    const facts = form.args.slice(0, arrowIndex);
    const actions = form.args.slice(arrowIndex + 1);

    assert.ok(
      facts.length > 0,
      "[Rule structure] defrule at line " +
        form.line +
        " has an empty facts section",
    );
    assert.ok(
      actions.length > 0,
      "[Rule structure] defrule at line " +
        form.line +
        " has an empty actions section",
    );
    assert.ok(
      facts.every((arg) => arg.kind === "expression"),
      "[Rule syntax] defrule at line " +
        form.line +
        " contains a non-expression token in its facts section",
    );
    assert.ok(
      actions.every((arg) => arg.kind === "expression"),
      "[Rule syntax] defrule at line " +
        form.line +
        " contains a non-expression token in its actions section",
    );

    for (const expr of [...facts, ...actions]) {
      if (expr.head === "defrule" || expr.head === "defconst") {
        assert.fail(
          "[Rule syntax] top-level form '" +
            expr.head +
            "' is nested inside defrule at line " +
            expr.line,
        );
      }
      validateRuleExpression(expr);
    }
  }

  return forms;
}


function validatePreprocessorStructure(sourceText) {
  const lines = stripComments(sourceText).split("\n");
  const stack = [];
  const MAX_DEPTH = 50;

  for (let index = 0; index < lines.length; index += 1) {
    const lineNumber = index + 1;
    const trimmed = lines[index].trim();
    if (!trimmed.startsWith("#")) continue;

    const definedMatch = trimmed.match(
      /^#load-if-defined\s+([A-Za-z_][A-Za-z0-9_-]*)\s*$/,
    );
    if (definedMatch) {
      stack.push({ line: lineNumber, inElse: false });
      assert.ok(
        stack.length <= MAX_DEPTH,
        "[Preprocessor] conditional loading exceeds " +
          MAX_DEPTH +
          " nested levels at line " +
          lineNumber,
      );
      continue;
    }

    const notDefinedMatch = trimmed.match(
      /^#load-if-not-defined\s+([A-Za-z_][A-Za-z0-9_-]*)\s*$/,
    );
    if (notDefinedMatch) {
      stack.push({ line: lineNumber, inElse: false });
      assert.ok(
        stack.length <= MAX_DEPTH,
        "[Preprocessor] conditional loading exceeds " +
          MAX_DEPTH +
          " nested levels at line " +
          lineNumber,
      );
      continue;
    }

    if (/^#load-if-(?:defined|not-defined)\b/.test(trimmed)) {
      assert.fail(
        "[Preprocessor] malformed conditional directive at line " +
          lineNumber +
          "; expected a symbol name",
      );
    }

    if (trimmed === "#else") {
      assert.ok(
        stack.length > 0,
        "[Preprocessor] unexpected #else at line " +
          lineNumber +
          "; no matching conditional block",
      );
      const frame = stack.at(-1);
      assert.ok(
        !frame.inElse,
        "[Preprocessor] duplicate #else at line " +
          lineNumber +
          "; conditional block already has an else branch",
      );
      frame.inElse = true;
      continue;
    }

    if (trimmed === "#end-if") {
      assert.ok(
        stack.length > 0,
        "[Preprocessor] unexpected #end-if at line " +
          lineNumber +
          "; no matching conditional block",
      );
      stack.pop();
      continue;
    }

    if (
      /^#(?:load-if-defined|load-if-not-defined|else|end-if)\b/.test(trimmed)
    ) {
      assert.fail(
        "[Preprocessor] malformed directive at line " + lineNumber,
      );
    }
  }

  assert.equal(
    stack.length,
    0,
    "[Preprocessor] unterminated conditional block opened at line " +
      stack.at(-1)?.line,
  );
}

function renderRule(rule) {
  return String(rule);
}

function countRuleElements(rule) {
  let forms = 0;
  for (const ch of rule) {
    if (ch === "(") forms += 1;
  }
  return forms - 1;
}

function validateEngineLimits(sourceText, rules) {
  const lines = sourceText.split("\n");
  const maxLineLength = Math.max(...lines.map((line) => line.length));
  assert.ok(
    rules.length <= 10000,
    `[Engine limits] controller has ${rules.length} rules; DE limit is 10000`,
  );
  assert.ok(
    maxLineLength <= 255,
    `[Engine limits] controller line reaches ${maxLineLength} characters; DE limit is 255`,
  );

  const MAX_RULE_ELEMENTS = 32;
  const NEAR_RULE_ELEMENTS = 30;
  const COMPLEX_SINGLE_LINE_RULE_LENGTH = 150;
  let worstRule = -1;
  let worstElements = 0;
  const nearLimitRules = [];
  const atLimitRules = [];
  const complexSingleLineRules = [];

  for (let index = 0; index < rules.length; index += 1) {
    const elements = countRuleElements(rules[index]);
    if (elements > worstElements) {
      worstElements = elements;
      worstRule = index;
    }

    if (elements >= NEAR_RULE_ELEMENTS && elements < MAX_RULE_ELEMENTS) {
      nearLimitRules.push({
        rule: index + 1,
        elements,
        headroom: MAX_RULE_ELEMENTS - elements,
        risk: "near-limit",
      });
    }

    if (elements === MAX_RULE_ELEMENTS) {
      atLimitRules.push({
        rule: index + 1,
        elements,
        headroom: 0,
        risk: "at-limit",
      });
    }

    assert.ok(
      elements <= MAX_RULE_ELEMENTS,
      `[Rule too long] rule ${index + 1} has ${elements} elements; DE hard limit is ${MAX_RULE_ELEMENTS}`,
    );

    const nonBlankLines = rules[index]
      .split("\n")
      .filter((line) => line.trim().length > 0);
    if (
      nonBlankLines.length === 1 &&
      nonBlankLines[0].length > COMPLEX_SINGLE_LINE_RULE_LENGTH
    ) {
      complexSingleLineRules.push({
        rule: index + 1,
        length: nonBlankLines[0].length,
      });
    }
  }

  assert.equal(
    complexSingleLineRules.length,
    0,
    `[Complex single-line rule] DE-risk threshold is ${COMPLEX_SINGLE_LINE_RULE_LENGTH} characters; rules: ${complexSingleLineRules
      .map((entry) => `#${entry.rule}=${entry.length}`)
      .join(", ")}`,
  );

  const badDefconstTimers = [...sanitizeStructure(sourceText).matchAll(
    /\(defconst\s+[^\s)]+timer[^\s)]*\s+(-?\d+)\)/g,
  )]
    .map((match) => Number(match[1]))
    .filter((value) => value < 1 || value > 50);
  assert.equal(
    badDefconstTimers.length,
    0,
    `[Engine limits] numeric timer defconst outside 1..50: ${badDefconstTimers.join(", ")}`,
  );

  const badLiteralTimers = [...sanitizeStructure(sourceText).matchAll(
    /\((?:enable-timer|disable-timer|timer-triggered|up-timer-status|up-get-timer|up-set-timer)\s+(-?\d+)(?:\s|\))/g,
  )]
    .map((match) => Number(match[1]))
    .filter((value) => value < 1 || value > 50);
  assert.equal(
    badLiteralTimers.length,
    0,
    `[Engine limits] numeric timer command outside 1..50: ${badLiteralTimers.join(", ")}`,
  );

  return {
    maxLineLength,
    worstRule,
    worstElements,
    maxRuleHeadroom: MAX_RULE_ELEMENTS - worstElements,
    nearLimitRules,
    atLimitRules,
    nearLimitThreshold: NEAR_RULE_ELEMENTS,
    hardRuleElementLimit: MAX_RULE_ELEMENTS,
    complexSingleLineThreshold: COMPLEX_SINGLE_LINE_RULE_LENGTH,
  };
}
function addKnownIdentifier(set, value) {
  if (typeof value !== "string") return;
  for (const raw of value.split(",")) {
    const token = raw.trim().split(/\s+/)[0];
    if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(token)) set.add(token);
  }
}

function validateIdentifiers(sourceText, repoRootPath) {
  const registryFiles = {
    object: path.join(repoRootPath, "docs", "reference", "inventories", "airef-object-inventory.json"),
    tech: path.join(repoRootPath, "docs", "reference", "inventories", "airef-tech-inventory.json"),
    strategicNumber: path.join(repoRootPath, "docs", "reference", "inventories", "airef-strategic-number-inventory.json"),
    class: path.join(repoRootPath, "docs", "reference", "inventories", "airef-class-inventory.json"),
    valueFamily: path.join(repoRootPath, "docs", "reference", "inventories", "airef-value-family-inventory.json"),
  };
  const known = {
    defconst: new Set(),
    object: new Set(),
    tech: new Set(),
    strategicNumber: new Set(),
  };
  for (const match of sourceText.matchAll(/\(defconst\s+([A-Za-z][A-Za-z0-9_-]*)\b/g)) {
    known.defconst.add(match[1]);
  }

  const loadJson = (kind, filePath) => {
    assert.ok(
      fs.existsSync(filePath),
      "[Invalid identifier] required " + kind + " reference inventory is missing: " + filePath,
    );
    try {
      return JSON.parse(fs.readFileSync(filePath, "utf8"));
    } catch (error) {
      assert.fail(
        "[Invalid identifier] could not parse " + kind + " reference inventory " + filePath + ": " + error.message,
      );
    }
  };

  const objects = loadJson("object", registryFiles.object);
  const techs = loadJson("technology", registryFiles.tech);
  const strategicNumbers = loadJson("strategic-number", registryFiles.strategicNumber);
  const classes = loadJson("class", registryFiles.class);
  const valueFamilies = loadJson("value-family", registryFiles.valueFamily);

  const objectLinesByName = {};
  for (const entry of objects.objects ?? []) {
    addKnownIdentifier(known.object, entry.ai_name);
    addKnownIdentifier(known.object, entry.line);
    if (
      entry.dataset === "standard" &&
      typeof entry.ai_name === "string" &&
      typeof entry.line === "string" &&
      entry.line
    ) {
      for (const raw of entry.ai_name.split(",")) {
        const token = raw.trim().split(/\s+/)[0];
        if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(token)) objectLinesByName[token] = entry.line;
      }
    }
  }
  for (const entry of techs.techs ?? []) {
    addKnownIdentifier(known.tech, entry.ai_name);
  }
  for (const entry of strategicNumbers.strategic_numbers ?? []) {
    addKnownIdentifier(known.strategicNumber, entry.name);
  }

  const universalValues = new Set();
  for (const entry of objects.objects ?? []) {
    addKnownIdentifier(universalValues, entry.ai_name);
    addKnownIdentifier(universalValues, entry.line);
  }
  for (const entry of techs.techs ?? []) {
    addKnownIdentifier(universalValues, entry.ai_name);
  }
  for (const entry of classes.entries ?? []) {
    addKnownIdentifier(universalValues, entry.symbol);
    for (const alias of entry.aliases ?? []) addKnownIdentifier(universalValues, alias);
  }
  for (const family of valueFamilies.families ?? []) {
    for (const entry of family.entries ?? []) {
      addKnownIdentifier(universalValues, entry.name);
      for (const alias of entry.aliases ?? []) addKnownIdentifier(universalValues, alias);
    }
  }

  // These engine-native aliases are not present as named AIRef identifiers.
  // They must therefore be explicitly materialized as local defconst values.
  const engineSupplements = new Set([
    "siege-tower",
    "ri-logistica",
    "ri-elite-varangian-guard",
  ]);
  const runtimeRejectedAliases = new Map([
    ["arbalester", "arbalest"],
    ["ri-arbalester", "ri-arbalest"],
  ]);

  for (const value of engineSupplements) {
    assert.ok(
      known.defconst.has(value),
      "[Invalid identifier] site-specific engine identifier '" +
        value +
        "' must be explicitly defined with defconst before use",
    );
  }

  const identifierSource = sanitizeStructure(sourceText);
  const failures = [];
  const check = (regex, family, label) => {
    for (const match of identifierSource.matchAll(regex)) {
      const token = match[1];
      if (/^-?\d+$/.test(token)) continue;
      if (runtimeRejectedAliases.has(token)) {
        const line = sourceText.slice(0, match.index).split("\n").length;
        failures.push({
          label,
          token,
          line,
          replacement: runtimeRejectedAliases.get(token),
        });
        continue;
      }
      const recognized =
        known.defconst.has(token) ||
        known[family]?.has(token) ||
        universalValues.has(token);
      if (!recognized) {
        const line = sourceText.slice(0, match.index).split("\n").length;
        failures.push({ label, token, line });
      }
    }
  };

  check(/\((?:can-build(?:-with-escrow)?|build)\s+([A-Za-z][A-Za-z0-9_-]*)/g, "object", "build");
  check(/\((?:can-train(?:-with-escrow)?|train)\s+([A-Za-z][A-Za-z0-9_-]*)/g, "object", "train");
  check(/\((?:can-research(?:-with-escrow)?|research)\s+([A-Za-z][A-Za-z0-9_-]*)/g, "tech", "research");
  check(/\((?:goal|set-goal|up-compare-goal)\s+([A-Za-z][A-Za-z0-9_-]*)/g, "defconst", "goal");
  check(/\((?:strategic-number|set-strategic-number)\s+([A-Za-z][A-Za-z0-9_-]*)/g, "strategicNumber", "strategic-number");
  check(/\bc:\s+([A-Za-z][A-Za-z0-9_-]*)/g, null, "constant-operand");
  check(/\bg:[^\s()]+\s+([A-Za-z][A-Za-z0-9_-]*)/g, "defconst", "goal-operand");
  check(/\bs:[^\s()]+\s+([A-Za-z][A-Za-z0-9_-]*)/g, "strategicNumber", "strategic-number-operand");

  const numericDefconsts = new Map(
    [...identifierSource.matchAll(
      /\(defconst\s+([A-Za-z][A-Za-z0-9_-]*)\s+(-?\d+)\)/g,
    )].map((match) => [match[1], Number(match[2])]),
  );

  const defconstDefinitions = [...identifierSource.matchAll(
    /\(defconst\s+([A-Za-z][A-Za-z0-9_-]*)\b/g,
  )];
  const duplicateDefconsts = [
    ...defconstDefinitions
      .map((match) => match[1])
      .filter((name, index, names) => names.indexOf(name) !== index),
  ];
  assert.equal(
    duplicateDefconsts.length,
    0,
    `[Defconst] duplicate definition(s): ${[...new Set(duplicateDefconsts)].join(", ")}`,
  );

  for (const [name, value] of numericDefconsts) {
    assert.ok(
      value >= -32768 && value <= 32767,
      `[Defconst] ${name} has numeric value ${value} outside -32768..32767`,
    );
  }

  for (const match of identifierSource.matchAll(
    /\((enable-timer|disable-timer|timer-triggered|up-timer-status|up-get-timer|up-set-timer)\s+(-?\d+|[A-Za-z][A-Za-z0-9_-]*)/g,
  )) {
    const token = match[2];
    const line = identifierSource.slice(0, match.index).split("\n").length;
    const value = /^-?\d+$/.test(token) ? Number(token) : numericDefconsts.get(token);

    assert.ok(
      value !== undefined,
      `[Timer] ${match[1]} uses undefined or non-numeric timer identifier '${token}' at line ${line}`,
    );
    assert.ok(
      value >= 1 && value <= 50,
      `[Timer] ${match[1]} uses timer ${token}=${value} outside 1..50 at line ${line}`,
    );
  }

  for (const match of identifierSource.matchAll(/\b(bt-[A-Za-z0-9_-]*-goal)\b/g)) {
    assert.ok(
      known.defconst.has(match[1]),
      `[Invalid identifier] Basilisk goal symbol '${match[1]}' at line ${identifierSource.slice(0, match.index).split("\n").length} is not defined by defconst`,
    );
  }

  for (const match of identifierSource.matchAll(/\b(ri-[A-Za-z0-9_-]+)\b/g)) {
    assert.ok(
      known.tech.has(match[1]) ||
        known.defconst.has(match[1]) ||
        universalValues.has(match[1]),
      `[Invalid identifier] technology-like symbol '${match[1]}' at line ${identifierSource.slice(0, match.index).split("\n").length} is not resolvable`,
    );
  }

  if (failures.length > 0) {
    const detail = failures
      .slice(0, 12)
      .map(({ label, token, line, replacement }) =>
        label +
        " '" +
        token +
        "' at line " +
        line +
        (replacement ? " (DE runtime canonical identifier: '" + replacement + "')" : ""),
      )
      .join("; ");
    const suffix = failures.length > 12 ? "; plus " + (failures.length - 12) + " more" : "";
    assert.fail(
      "[Invalid identifier] " + failures.length + " unresolved engine identifier(s): " + detail + suffix,
    );
  }

  return {
    checkedSlots: "build/train/research/goal/strategic-number plus typed c:/g:/s: operands and timers",
    engineSupplements: [...engineSupplements],
    siteSpecificEngineIdentifiersRequireDefconst: true,
    objectLinesByName,
  };
}




function validateAIRefCommandVocabulary(sourceText, rules, repoRootPath) {
  const inventoryPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-command-inventory.json",
  );
  assert.ok(
    fs.existsSync(inventoryPath),
    "[AIRef command] command inventory is missing: " + inventoryPath,
  );

  let registry;
  try {
    registry = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));
  } catch (error) {
    assert.fail(
      "[AIRef command] could not parse command inventory " +
        inventoryPath +
        ": " +
        error.message,
    );
  }

  assert.equal(
    registry?.metadata?.source,
    "https://airef.github.io/commands/commands-index.html",
    "[AIRef command] command inventory is not anchored to the AIRef command index",
  );
  assert.ok(
    registry?.metadata?.source_blob_sha,
    "[AIRef command] command inventory is missing the AIRef source blob SHA",
  );

  const commands = Array.isArray(registry.commands) ? registry.commands : [];
  assert.ok(commands.length > 0, "[AIRef command] command inventory contains no commands");

  const byName = new Map();
  const duplicates = [];
  for (const command of commands) {
    assert.ok(
      typeof command.name === "string" &&
        typeof command.type === "string" &&
        typeof command.version === "string",
      "[AIRef command] every command entry must contain name/type/version",
    );
    if (byName.has(command.name)) duplicates.push(command.name);
    byName.set(command.name, command);
  }
  assert.equal(
    duplicates.length,
    0,
    "[AIRef command] duplicate command names in registry: " +
      [...new Set(duplicates)].join(", "),
  );

  const logicalOperators = new Set([
    "and",
    "nand",
    "nor",
    "not",
    "or",
    "xor",
    "xnor",
  ]);
  const failures = [];
  const used = new Set();

  for (let index = 0; index < rules.length; index += 1) {
    const rule = rules[index];
    const arrow = rule.indexOf("=>");
    assert.notEqual(arrow, -1, "[AIRef command] rule " + index + " has no => separator");

    for (const side of [
      { role: "fact", text: rule.slice(0, arrow) },
      { role: "action", text: rule.slice(arrow + 2) },
    ]) {
      for (const match of side.text.matchAll(/\(([A-Za-z][A-Za-z0-9_-]*)\b/g)) {
        const name = match[1];
        if (name === "defrule" || name === "defconst") continue;
        used.add(name);
        const command = byName.get(name);

        if (!command) {
          failures.push({
            kind: "unknown-command",
            name,
            role: side.role,
            rule: index + 1,
          });
          continue;
        }
        if (command.type === "Fact" && side.role !== "fact") {
          failures.push({
            kind: "fact-used-as-action",
            name,
            role: side.role,
            rule: index + 1,
          });
        }
        if (command.type === "Action" && side.role !== "action") {
          failures.push({
            kind: "action-used-as-fact",
            name,
            role: side.role,
            rule: index + 1,
          });
        }
        if (
          command.type === "Other" &&
          side.role === "action" &&
          !logicalOperators.has(name)
        ) {
          failures.push({
            kind: "other-command-in-action-side",
            name,
            role: side.role,
            rule: index + 1,
          });
        }
        if (
          command.type === "Other" &&
          side.role === "fact" &&
          !logicalOperators.has(name)
        ) {
          failures.push({
            kind: "unsupported-other-command",
            name,
            role: side.role,
            rule: index + 1,
          });
        }
      }
    }
  }

  assert.equal(
    failures.length,
    0,
    "[AIRef command] " +
      failures.length +
      " command contract failure(s): " +
      failures
        .slice(0, 12)
        .map(
          (failure) =>
            failure.kind +
            " '" +
            failure.name +
            "' in " +
            failure.role +
            " side of rule " +
            failure.rule,
        )
        .join("; "),
  );

  const versionCounts = {};
  for (const name of used) {
    const version = byName.get(name)?.version;
    if (!version) continue;
    versionCounts[version] = (versionCounts[version] ?? 0) + 1;
  }

  return {
    commandCount: commands.length,
    usedCommandCount: used.size,
    sourceBlobSha: registry.metadata.source_blob_sha,
    versionCounts,
  };
}


function parseCommandExpressions(text) {
  const expressions = [];

  function skipWhitespace(index) {
    let cursor = index;
    while (cursor < text.length && /\s/.test(text[cursor])) cursor += 1;
    return cursor;
  }

  function readAtom(index) {
    if (text[index] === '"') {
      let cursor = index + 1;
      let escaped = false;
      while (cursor < text.length) {
        const ch = text[cursor];
        if (escaped) {
          escaped = false;
        } else if (ch === "\\") {
          escaped = true;
        } else if (ch === '"') {
          return {
            value: text.slice(index, cursor + 1),
            end: cursor + 1,
          };
        }
        cursor += 1;
      }
      return { value: text.slice(index), end: text.length };
    }

    let cursor = index;
    while (
      cursor < text.length &&
      !/\s/.test(text[cursor]) &&
      text[cursor] !== "(" &&
      text[cursor] !== ")"
    ) {
      cursor += 1;
    }
    return {
      value: text.slice(index, cursor),
      end: cursor,
    };
  }

  function readExpression(start) {
    assert.equal(text[start], "(", "[AIRef schema] expression parser expected '('");
    let cursor = skipWhitespace(start + 1);
    const headToken = readAtom(cursor);
    const head = headToken.value;
    cursor = headToken.end;

    const args = [];
    while (cursor < text.length) {
      cursor = skipWhitespace(cursor);
      if (text[cursor] === ")") {
        return {
          head,
          args,
          start,
          end: cursor + 1,
        };
      }
      if (text[cursor] === "(") {
        const child = readExpression(cursor);
        args.push(child);
        cursor = child.end;
        continue;
      }
      const atom = readAtom(cursor);
      args.push(atom.value);
      cursor = atom.end;
    }

    assert.fail(
      "[AIRef schema] expression '" + head + "' is not closed",
    );
  }

  let cursor = 0;
  while (cursor < text.length) {
    cursor = skipWhitespace(cursor);
    if (cursor >= text.length) break;
    if (text[cursor] !== "(") {
      cursor += 1;
      continue;
    }
    const expression = readExpression(cursor);
    expressions.push(expression);
    cursor = expression.end;
  }

  return expressions;
}

function loadAIRefCommandSchema(repoRootPath) {
  const schemaPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-command-schema.json",
  );
  assert.ok(
    fs.existsSync(schemaPath),
    "[AIRef schema] command schema is missing: " + schemaPath,
  );

  let registry;
  try {
    registry = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
  } catch (error) {
    assert.fail(
      "[AIRef schema] could not parse command schema " +
        schemaPath +
        ": " +
        error.message,
    );
  }

  assert.equal(
    registry?.metadata?.source_commands_js_blob_sha,
    "e2fc2c9b6a6b23f63d0743524dc94252eacfc2af",
    "[AIRef schema] schema is not anchored to the current AIRef commands.js blob",
  );

  const commandInventoryPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-command-inventory.json",
  );
  assert.ok(
    fs.existsSync(commandInventoryPath),
    "[AIRef schema] current AIRef command inventory is missing: " + commandInventoryPath,
  );

  let commandInventory;
  try {
    commandInventory = JSON.parse(fs.readFileSync(commandInventoryPath, "utf8"));
  } catch (error) {
    assert.fail(
      "[AIRef schema] could not parse current AIRef command inventory: " +
        error.message,
    );
  }

  assert.equal(
    commandInventory?.metadata?.source_blob_sha,
    registry?.metadata?.source_commands_js_blob_sha,
    "[AIRef schema] slot schema and AIRef command vocabulary are anchored to different commands.js blobs",
  );
  assert.equal(
    registry?.metadata?.ai_ref_command_count,
    385,
    "[AIRef schema] expected the complete 385-command AIRef catalog",
  );

  const commands = Array.isArray(registry.commands) ? registry.commands : [];
  const inventoryCommands = Array.isArray(commandInventory?.commands)
    ? commandInventory.commands
    : [];
  assert.equal(
    commands.length,
    inventoryCommands.length,
    "[AIRef schema] slot schema command count does not match the current AIRef command inventory",
  );
  assert.equal(
    commands.length,
    385,
    "[AIRef schema] slot schema does not contain all 385 AIRef commands",
  );
  assert.ok(
    commands.length > 0,
    "[AIRef schema] command schema contains no commands",
  );

  const inventoryByName = new Map(
    inventoryCommands.map((command) => [command.name, command]),
  );
  const byName = new Map();
  for (const command of commands) {
    assert.ok(
      typeof command.name === "string" &&
        Array.isArray(command.parameters) &&
        typeof command.syntax === "string",
      "[AIRef schema] every command entry must contain name, syntax, and parameters",
    );
    assert.ok(
      !byName.has(command.name),
      "[AIRef schema] duplicate command entry: " + command.name,
    );
    const inventoryEntry = inventoryByName.get(command.name);
    assert.ok(
      inventoryEntry,
      "[AIRef schema] slot schema contains command not present in current AIRef inventory: " +
        command.name,
    );
    assert.equal(
      command.version,
      inventoryEntry.version,
      "[AIRef schema] version mismatch for " + command.name,
    );
    assert.equal(
      command.command_type,
      inventoryEntry.type,
      "[AIRef schema] command-type mismatch for " + command.name,
    );
    byName.set(command.name, command);
  }

  assert.equal(
    byName.size,
    inventoryByName.size,
    "[AIRef schema] command names differ between slot schema and AIRef inventory",
  );

  return {
    path: schemaPath,
    metadata: registry.metadata ?? {},
    commands,
    byName,
  };
}

function loadAIRefSchemaSymbolFamilies(sourceText, repoRootPath) {
  const strategicNumberPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-strategic-number-inventory.json",
  );
  const techPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-tech-inventory.json",
  );
  const objectPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-object-inventory.json",
  );
  const classPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-class-inventory.json",
  );
  const valueFamilyPath = path.join(
    repoRootPath,
    "docs",
    "reference",
    "inventories",
    "airef-value-family-inventory.json",
  );

  const load = (filePath) => {
    assert.ok(
      fs.existsSync(filePath),
      "[AIRef schema] supporting inventory is missing: " + filePath,
    );
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  };

  const strategicNumberInventory = load(strategicNumberPath);
  const techInventory = load(techPath);
  const objectInventory = load(objectPath);
  const classInventory = load(classPath);
  const valueFamilyInventory = load(valueFamilyPath);

  const strategicNumbers = new Set(
    (strategicNumberInventory.strategic_numbers ?? [])
      .map((entry) => entry.name)
      .filter(Boolean),
  );
  const techs = new Set();
  for (const entry of techInventory.techs ?? []) {
    if (typeof entry.ai_name === "string") {
      for (const raw of entry.ai_name.split(",")) {
        const token = raw.trim().split(/\s+/)[0];
        if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(token)) techs.add(token);
      }
    }
  }

  const objects = new Set();
  const objectWildcards = new Set();
  for (const entry of objectInventory.objects ?? []) {
    for (const value of [entry.ai_name, entry.line]) {
      if (typeof value !== "string") continue;
      for (const raw of value.split(",")) {
        const token = raw.trim().split(/\s+/)[0];
        if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(token)) objects.add(token);
      }
    }
    if (typeof entry.notes === "string") {
      for (const match of entry.notes.matchAll(
        /(?:counted|used)\s+with\s+([A-Za-z][A-Za-z0-9_-]*)/gi,
      )) {
        objectWildcards.add(match[1]);
      }
    }
  }

  const classes = new Set(
    (classInventory.entries ?? [])
      .flatMap((entry) => [entry.symbol, ...(entry.aliases ?? [])])
      .filter(Boolean),
  );

  const parameterValues = new Map();
  const strictParameterValues = new Map();
  for (const family of valueFamilyInventory.families ?? []) {
    const names = parameterValues.get(family.parameter_name) ?? new Set();
    for (const entry of family.entries ?? []) {
      if (typeof entry.name === "string") {
        for (const token of entry.name.split(",")) {
          const normalized = token.trim();
          if (normalized) names.add(normalized);
        }
      }
      for (const alias of entry.aliases ?? []) {
        if (typeof alias === "string" && alias.trim()) names.add(alias.trim());
      }
    }
    parameterValues.set(family.parameter_name, names);
    if (family.family_type === "value-list") {
      strictParameterValues.set(family.parameter_name, names);
    }
  }

  const defconsts = new Set();
  const defconstValues = new Map();
  for (const match of sanitizeStructure(sourceText).matchAll(
    /\(defconst\s+([A-Za-z][A-Za-z0-9_-]*)\s+(-?\d+)\)/g,
  )) {
    defconsts.add(match[1]);
    defconstValues.set(match[1], Number(match[2]));
  }

  return {
    defconsts,
    defconstValues,
    strategicNumbers,
    techs,
    objects,
    objectWildcards,
    classes,
    parameterValues,
    strictParameterValues,
    constantSymbols: new Set([
      ...strategicNumbers,
      ...techs,
      ...objects,
      ...classes,
      ...[...parameterValues.values()].flatMap((values) => [...values]),
      ...defconsts,
    ]),
  };
}


function documentedParameterValue(parameterName, value, families, parameterType = null) {
  if (!value || /^-?\d+$/.test(value) || value.startsWith('"')) return true;
  if (families.defconsts.has(value)) return true;
  if (value.startsWith("g:") || value.startsWith("s:") || value.startsWith("c:")) {
    return false;
  }
  const strictValues = families.strictParameterValues.get(parameterName);
  if (strictValues) return strictValues.has(value);
  if (parameterType === "Const") return families.constantSymbols.has(value);
  return true;
}

function parseAIRefSimpleNumericRange(rangeText) {
  const text = String(rangeText ?? "");
  if (!text || /\bor\b/i.test(text)) return null;
  const matches = [...text.matchAll(/(-?\d[\d,]*)\s+to\s+(-?\d[\d,]*)/gi)];
  if (matches.length !== 1) return null;
  const minimum = Number(matches[0][1].replaceAll(",", ""));
  const maximum = Number(matches[0][2].replaceAll(",", ""));
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) return null;
  return minimum <= maximum ? [minimum, maximum] : [maximum, minimum];
}

function isSymbolicSchemaValue(value) {
  return (
    /^[A-Za-z][A-Za-z0-9_-]*$/.test(value) &&
    !/^-?\d+$/.test(value)
  );
}

function typedSchemaFamily(value, families) {
  if (!value || /^-?\d+$/.test(value)) return null;
  if (families.strategicNumbers.has(value) || /^sn-/.test(value)) {
    return "strategic number";
  }
  if (
    families.defconsts.has(value) &&
    (/^(?:gl-|goal-)/.test(value) || /-goal$/.test(value))
  ) {
    return "goal";
  }
  if (families.techs.has(value) || /^ri-/.test(value)) return "tech";
  if (families.objects.has(value)) return "object";
  return null;
}

function allowsObjectWildcard(commandName, parameterName) {
  return (
    parameterName === "UnitId" &&
    /(?:^|-)unit-type-count(?:-total)?$/.test(commandName)
  );
}

function expectedAIRefFamily(parameterName) {
  if (
    parameterName === "GoalId" ||
    parameterName === "EscrowGoalId" ||
    parameterName === "OptionGoalId" ||
    parameterName === "SharedGoalId"
  ) {
    return "goal";
  }
  if (parameterName === "SnId") return "strategic number";
  if (parameterName === "TechId") return "tech";
  if (
    parameterName === "BuildingId" ||
    parameterName === "UnitId" ||
    parameterName === "ObjectId" ||
    parameterName === "ClassId"
  ) {
    return "object";
  }
  if (parameterName === "PlayerNumber") return "player";
  return null;
}

const AIREF_TYPE_PREFIXES = new Set(["c:", "g:", "s:"]);
const AIREF_COMPARE_OPS = new Set([
  "<",
  "<=",
  ">",
  ">=",
  "==",
  "!=",
  "c:<",
  "c:<=",
  "c:>",
  "c:>=",
  "c:==",
  "c:!=",
  "g:<",
  "g:<=",
  "g:>",
  "g:>=",
  "g:==",
  "g:!=",
  "s:<",
  "s:<=",
  "s:>",
  "s:>=",
  "s:==",
  "s:!=",
]);
const AIREF_MATH_OPS = new Set([
  "c:=",
  "c:+",
  "c:-",
  "c:*",
  "c:/",
  "c:z/",
  "c:mod",
  "c:min",
  "c:max",
  "c:neg",
  "c:%*",
  "c:%/",
  "g:=",
  "g:+",
  "g:-",
  "g:*",
  "g:/",
  "g:z/",
  "g:mod",
  "g:min",
  "g:max",
  "g:neg",
  "g:%*",
  "g:%/",
  "s:=",
  "s:+",
  "s:-",
  "s:*",
  "s:/",
  "s:z/",
  "s:mod",
  "s:min",
  "s:max",
  "s:neg",
  "s:%*",
  "s:%/",
]);

function normalizeAIRefTypedOperands(args, parameters) {
  const normalized = [];
  let cursor = 0;

  for (const parameter of parameters) {
    const first = args[cursor];
    if (
      parameter.name !== "typeOp" &&
      typeof first === "string" &&
      AIREF_TYPE_PREFIXES.has(first)
    ) {
      return null;
    }

    normalized.push({
      value: first,
      typePrefix: null,
    });
    cursor += 1;
  }

  if (cursor !== args.length) return null;
  return normalized;
}

function validateAIRefCommandSchema(sourceText, rules, repoRootPath) {
  const schema = loadAIRefCommandSchema(repoRootPath);
  const families = loadAIRefSchemaSymbolFamilies(sourceText, repoRootPath);
  const failures = [];
  const logicalOperators = new Set([
    "and",
    "nand",
    "nor",
    "not",
    "or",
    "xor",
    "xnor",
  ]);

  const cleanSource = stripComments(sourceText);
  const reportFailure = (kind, expression, parameterIndex, message) => {
    failures.push({
      kind,
      command: expression.head,
      parameterIndex,
      line: cleanSource.slice(0, expression.start).split("\n").length,
      message,
    });
  };

  const allExpressions = parseCommandExpressions(cleanSource);

  const validateExpression = (expression) => {
    if (
      logicalOperators.has(expression.head) ||
      expression.head === "defrule" ||
      expression.head === "defconst"
    ) {
      for (const arg of expression.args) {
        if (arg && typeof arg === "object") validateExpression(arg);
      }
      return;
    }

    const command = schema.byName.get(expression.head);
    if (!command) {
      for (const arg of expression.args) {
        if (arg && typeof arg === "object") validateExpression(arg);
      }
      return;
    }

    const nestedArgument = expression.args.find(
      (arg) => arg && typeof arg === "object",
    );
    if (nestedArgument) {
      reportFailure(
        "command-nested-expression-mismatch",
        expression,
        expression.args.indexOf(nestedArgument) + 1,
        command.name +
          " argument " +
          (expression.args.indexOf(nestedArgument) + 1) +
          " is a nested expression; AIRef command parameters are atomic values",
      );
      for (const arg of expression.args) {
        if (arg && typeof arg === "object") validateExpression(arg);
      }
      return;
    }

    const parameters = command.parameters;
    const splitTypedComparison =
      expression.args.some(
        (arg, index) =>
          typeof arg === "string" &&
          AIREF_COMPARE_OPS.has(arg) &&
          (expression.args[index + 1] === "g:" ||
            expression.args[index + 1] === "s:"),
      );
    if (splitTypedComparison) {
      return;
    }

    const normalizedArguments = normalizeAIRefTypedOperands(
      expression.args,
      parameters,
    );
    if (!normalizedArguments) {
      reportFailure(
        "command-arity-mismatch",
        expression,
        null,
        command.name +
          " expects " +
          parameters.length +
          " logical arguments, got " +
          expression.args.length +
          " lexical arguments",
      );
      return;
    }

    for (let index = 0; index < parameters.length; index += 1) {
      const parameter = parameters[index];
      const parameterName = parameter.name;
      const argument = normalizedArguments[index];
      const value = argument.value;
      const typePrefix = argument.typePrefix;

      if (parameterName === "typeOp") {
        if (!AIREF_TYPE_PREFIXES.has(value)) {
          reportFailure(
            "command-typed-prefix-mismatch",
            expression,
            index + 1,
            command.name +
              " argument " +
              (index + 1) +
              " is '" +
              value +
              "'; expected one of c:, g:, s: for typeOp",
          );
        }
      } else if (parameterName === "compareOp") {
        if (!AIREF_COMPARE_OPS.has(value)) {
          reportFailure(
            "command-argument-mismatch",
            expression,
            index + 1,
            command.name +
              " argument " +
              (index + 1) +
              " is '" +
              value +
              "'; expected an AIRef compareOp",
          );
        }
      } else if (parameterName === "mathOp") {
        if (!AIREF_MATH_OPS.has(value)) {
          reportFailure(
            "command-argument-mismatch",
            expression,
            index + 1,
            command.name +
              " argument " +
              (index + 1) +
              " is '" +
              value +
              "'; expected an AIRef mathOp",
          );
        }
      }

      const range = parseAIRefSimpleNumericRange(parameter.range);
      if (range) {
        let numericValue;
        if (/^-?\d+$/.test(value)) {
          numericValue = Number(value);
        } else if (families.defconstValues.has(value)) {
          numericValue = families.defconstValues.get(value);
        }
        if (
          numericValue !== undefined &&
          (numericValue < range[0] || numericValue > range[1])
        ) {
          reportFailure(
            "command-numeric-range-mismatch",
            expression,
            index + 1,
            command.name +
              " " +
              parameterName +
              " argument " +
              (index + 1) +
              " uses " +
              value +
              "=" +
              numericValue +
              "; expected " +
              range[0] +
              " to " +
              range[1],
          );
        }
      }

      if (
        parameter.type === "Const" &&
        isSymbolicSchemaValue(value) &&
        !documentedParameterValue(parameterName, value, families, parameter.type) && !(parameterName === "UnitId" && families.objectWildcards.has(value) && allowsObjectWildcard(command.name, parameterName))
      ) {
        reportFailure(
          "command-argument-mismatch",
          expression,
          index + 1,
          command.name +
            " " +
            parameterName +
            " argument " +
            (index + 1) +
            " uses undocumented AIRef value '" +
            value +
            "'",
        );
      }

      const expectedFamily = expectedAIRefFamily(parameterName);
      const actualFamily = typedSchemaFamily(value, families);
      const expectedTypedFamily =
        typePrefix === "g:"
          ? "goal"
          : typePrefix === "s:"
            ? "strategic number"
            : null;

      if (
        expectedTypedFamily &&
        actualFamily &&
        actualFamily !== expectedTypedFamily
      ) {
        reportFailure(
          "command-typed-operand-mismatch",
          expression,
          index + 1,
          command.name +
            " argument " +
            (index + 1) +
            " uses '" +
            value +
            "', which is a " +
            actualFamily +
            "; type prefix '" +
            typePrefix +
            "' requires a " +
            expectedTypedFamily +
            " operand",
        );
      }

      if (
        !typePrefix &&
        expectedFamily === "object" &&
        isSymbolicSchemaValue(value) &&
        !families.defconsts.has(value) &&
        !families.objects.has(value) &&
        !(
          families.objectWildcards.has(value) &&
          allowsObjectWildcard(command.name, parameterName)
        ) &&
        !families.parameterValues.get(parameterName)?.has(value) &&
        !(parameterName === "ClassId" && families.classes.has(value)) &&
        !(parameterName === "UnitId" && families.classes.has(value))
      ) {
        reportFailure(
          "command-argument-mismatch",
          expression,
          index + 1,
          command.name +
            " " +
            parameterName +
            " argument " +
            (index + 1) +
            " uses undocumented AIRef object identifier '" +
            value +
            "'",
        );
      }
      if (
        !typePrefix &&
        expectedFamily &&
        actualFamily &&
        expectedFamily !== actualFamily
      ) {
        reportFailure(
          "command-family-mismatch",
          expression,
          index + 1,
          command.name +
            " " +
            parameterName +
            " argument " +
            (index + 1) +
            " uses '" +
            value +
            "', which looks like a " +
            actualFamily +
            "; expected " +
            expectedFamily,
        );
      }

      if (
        index > 0 &&
        ["typeOp", "compareOp", "mathOp"].includes(parameters[index - 1].name)
      ) {
        const operator = expression.args[index - 1];
        let expectedTypedFamily = null;
        if (typeof operator === "string" && operator.startsWith("g:")) {
          expectedTypedFamily = "goal";
        } else if (
          typeof operator === "string" &&
          operator.startsWith("s:")
        ) {
          expectedTypedFamily = "strategic number";
        }

        if (expectedTypedFamily) {
          const actualTypedFamily = typedSchemaFamily(value, families);
          if (
            actualTypedFamily &&
            actualTypedFamily !== expectedTypedFamily
          ) {
            reportFailure(
              "command-typed-operand-mismatch",
              expression,
              index + 1,
              command.name +
                " argument " +
                (index + 1) +
                " uses '" +
                value +
                "', which looks like a " +
                actualTypedFamily +
                "; operator '" +
                operator +
                "' requires a " +
                expectedTypedFamily +
                " operand",
            );
          }
        }
      }
    }
  };

  for (const expression of allExpressions) validateExpression(expression);

  assert.equal(
    failures.length,
    0,
    "[AIRef schema] " +
      failures.length +
      " command-schema failure(s): " +
      failures
        .slice(0, 12)
        .map(
          (failure) =>
            failure.kind +
            " '" +
            failure.command +
            "' argument " +
            failure.parameterIndex +
            " at line " +
            failure.line +
            ": " +
            failure.message,
        )
        .join("; "),
  );

  return {
    schemaCommandCount: schema.commands.length,
    schemaCoveredUsageCount: new Set(
      allExpressions.map((expression) => expression.head),
    ).size,
  };
}


function validateAIRefTypedComparisonSyntax(sourceText) {
  const sanitized = sanitizeStructure(sourceText);
  const failures = [];
  const splitComparison = /\s(?:<=|>=|<|>|==|!=)\s+g:|\s(?:<=|>=|<|>|==|!=)\s+s:/g;

  for (const match of sanitized.matchAll(splitComparison)) {
    const line = sanitized.slice(0, match.index).split("\n").length;
    failures.push({
      line,
      text: match[0],
    });
  }

  assert.equal(
    failures.length,
    0,
    "[AIRef schema] split-typed-comparison " +
      failures.length +
      " violation(s); use typed comparison operators such as g:< or s:==",
  );
}

function validateAIRefDucStateSafety(sourceText) {
  const sanitized = sanitizeStructure(sourceText);
  const rules = extractRules(sanitized);
  let localReady = false;
  let remoteReady = false;
  const failures = [];

  const walk = (expression, line) => {
    if (!expression || typeof expression !== "object") return;
    const head = expression.head;
    const args = expression.args.map((arg) =>
      typeof arg === "string" ? arg : null,
    );

    if (head === "up-full-reset-search") {
      localReady = false;
      remoteReady = false;
    } else if (head === "up-reset-search") {
      if (args.length < 4) {
        localReady = false;
        remoteReady = false;
      } else {
        if (args[1] === "1") localReady = false;
        if (args[3] === "1") remoteReady = false;
      }
    } else if (head === "up-find-local") {
      localReady = true;
    } else if (head === "up-find-remote" || head === "up-find-resource") {
      remoteReady = true;
    } else if (
      head === "up-set-group" ||
      head === "up-set-target-object"
    ) {
      const source = args[0];
      if (head === "up-set-target-object") {
        if (source === "search-local" && !localReady) {
          failures.push({
            kind: "unsafe-set-target-object",
            command: head,
            line,
            message:
              head +
              " uses search-local before retained local search state has rebuilt that list",
          });
        }
        if (source === "search-remote" && !remoteReady) {
          failures.push({
            kind: "unsafe-set-target-object",
            command: head,
            line,
            message:
              head +
              " uses search-remote before retained remote search state has rebuilt that list",
          });
        }
      }
      if (source === "search-local") localReady = true;
      if (source === "search-remote") remoteReady = true;
    } else if (head === "up-target-point" || head === "up-target-objects") {
      if (!localReady) {
        failures.push({
          kind: "unscoped-duc-target",
          command: head,
          line,
          message:
            head +
            " runs without a retained local search/group state",
        });
      }
    }

    for (const arg of expression.args) {
      if (arg && typeof arg === "object") walk(arg, line);
    }
  };

  for (const rule of rules) {
    const expressions = parseCommandExpressions(rule);
    const line = sanitized.slice(
      0,
      sanitized.indexOf(rule),
    ).split("\n").length + 1;
    for (const expression of expressions) walk(expression, line);
  }

  assert.equal(
    failures.length,
    0,
    "[AIRef DUC] " +
      failures.length +
      " retained-search safety failure(s): " +
      failures
        .slice(0, 12)
        .map(
          (failure) =>
            failure.kind +
            " '" +
            failure.command +
            "' at line " +
            failure.line +
            ": " +
            failure.message,
        )
        .join("; "),
  );
}

function validateAIRefGoalOutputSafety(sourceText) {

  const sanitized = sanitizeStructure(sourceText);
  const numericDefconsts = new Map(
    [...sanitized.matchAll(
      /\(defconst\s+([A-Za-z][A-Za-z0-9_-]*)\s+(-?\d+)\)/g,
    )].map((match) => [match[1], Number(match[2])]),
  );

  const specs = [
    {
      command: "up-get-point",
      regex: /\(up-get-point\s+\S+\s+(-?\d+|[A-Za-z][A-Za-z0-9_-]*)\)/g,
      outputs: 2,
      maxBase: 15998,
      forbidden: new Set([511, 512]),
    },
    {
      command: "up-get-search-state",
      regex: /\(up-get-search-state\s+(-?\d+|[A-Za-z][A-Za-z0-9_-]*)\)/g,
      outputs: 4,
      maxBase: 15996,
      forbidden: new Set([509, 510, 511, 512]),
    },
    {
      command: "up-get-cost-delta",
      regex: /\(up-get-cost-delta\s+(-?\d+|[A-Za-z][A-Za-z0-9_-]*)\)/g,
      outputs: 4,
      maxBase: 15996,
      forbidden: new Set([509, 510, 511, 512]),
    },
    {
      command: "up-setup-cost-data",
      regex: /\(up-setup-cost-data\s+\S+\s+(-?\d+|[A-Za-z][A-Za-z0-9_-]*)\)/g,
      outputs: 4,
      maxBase: 15996,
      forbidden: new Set([509, 510, 511, 512]),
    },
  ];

  for (const spec of specs) {
    for (const match of sanitized.matchAll(spec.regex)) {
      const token = match[1];
      const line = sanitized.slice(0, match.index).split("\n").length;
      const base = /^-?\d+$/.test(token)
        ? Number(token)
        : numericDefconsts.get(token);

      assert.ok(
        base !== undefined,
        "[AIRef goal-output] " +
          spec.command +
          " uses undefined/non-numeric output goal '" +
          token +
          "' at line " +
          line,
      );
      assert.ok(
        base >= 41 && base <= spec.maxBase,
        "[AIRef goal-output] " +
          spec.command +
          " output block starts at goal " +
          token +
          "=" +
          base +
          " at line " +
          line +
          "; " +
          spec.outputs +
          " consecutive goals require a safe base in 41.." +
          spec.maxBase,
      );
      assert.ok(
        !spec.forbidden.has(base),
        "[AIRef goal-output] " +
          spec.command +
          " starts a " +
          spec.outputs +
          "-goal output block at reserved tail goal " +
          base +
          " at line " +
          line,
      );
    }
  }
}


function validateBombardTrebuchetDucLifecycle(rules) {
  const arm = rules.find(
    (rule) =>
      rule.includes("(goal bt-bombard-cannon-demand-goal 1)") &&
      rule.includes("(goal bt-bombard-trebuchet-duc-armed-goal 0)") &&
      rule.includes("(players-unit-type-count target-player trebuchet-set >= 1)") &&
      rule.includes("(set-goal bt-bombard-trebuchet-duc-armed-goal 1)") &&
      rule.includes("(set-goal bt-bombard-trebuchet-duc-stage-goal bt-bombard-trebuchet-duc-stage-idle)"),
  );
  assert.ok(
    arm,
    "[BBC DUC] armed-entry lifecycle edge is missing",
  );

  const disarmOnTargetLoss = rules.find(
    (rule) =>
      rule.includes("(goal bt-bombard-cannon-demand-goal 1)") &&
      rule.includes("(goal bt-bombard-trebuchet-duc-armed-goal 1)") &&
      rule.includes("(players-unit-type-count target-player trebuchet-set < 1)") &&
      rule.includes("(set-goal bt-bombard-trebuchet-duc-armed-goal 0)") &&
      rule.includes("(set-goal bt-bombard-trebuchet-duc-stage-goal bt-bombard-trebuchet-duc-stage-idle)") &&
      rule.includes("(disable-timer bt-bombard-trebuchet-target-timer)"),
  );
  assert.ok(
    disarmOnTargetLoss,
    "[BBC DUC] armed latch must disarm when the enemy Trebuchet witness disappears",
  );

  const demandCleanup = rules.find(
    (rule) =>
      rule.includes("(goal bt-bombard-cannon-demand-goal 0)") &&
      rule.includes("(goal bt-bombard-trebuchet-duc-armed-goal 1)") &&
      rule.includes("(set-goal bt-bombard-trebuchet-duc-armed-goal 0)"),
  );
  assert.ok(
    demandCleanup,
    "[BBC DUC] strategic-demand cleanup must clear the armed latch",
  );
}

function validateAIRefDucSearchBounds(sourceText) {
  const sanitized = sanitizeStructure(sourceText);

  for (const match of sanitized.matchAll(
    /\(up-find-local\b(?:[^()]|\([^()]*\))*\s+c:\s+(\d+)\)/g,
  )) {
    const value = Number(match[1]);
    const line = sanitized.slice(0, match.index).split("\n").length;
    assert.ok(
      value >= 0 && value <= 240,
      "[AIRef DUC] up-find-local requests " +
        value +
        " objects at line " +
        line +
        "; AIRef local search list limit is 240",
    );
  }

  for (const match of sanitized.matchAll(
    /\(up-find-remote\b(?:[^()]|\([^()]*\))*\s+c:\s+(\d+)\)/g,
  )) {
    const value = Number(match[1]);
    const line = sanitized.slice(0, match.index).split("\n").length;
    assert.ok(
      value >= 0 && value <= 40,
      "[AIRef DUC] up-find-remote requests " +
        value +
        " objects at line " +
        line +
        "; AIRef remote search list limit is 40",
    );
  }
}

function validateEngineActionContracts(rules, objectLinesByName) {
  for (let index = 0; index < rules.length; index += 1) {
    const rule = rules[index];
    for (const match of rule.matchAll(/\((build|train|research)\s+([^\s)]+)\)/g)) {
      const kind = match[1];
      const target = match[2];
      const exact = `(can-${kind} ${target})`;
      const escrow = `(can-${kind}-with-escrow ${target})`;
      assert.ok(
        rule.includes(exact) || rule.includes(escrow),
        `[Action contract] rule ${index} issues ${kind} ${target} without matching ${exact} or ${escrow}`,
      );

      if (kind === "train") {
        // Villager production is queue-gated by can-train villager itself.
        // A separate completed/pending witness is not required for the TC
        // producer because this is replenishing civilian production rather
        // than deficit-driven military/capability production.
        if (target === "villager") continue;

        const acceptedLines = new Set([target]);
        const familyLine = objectLinesByName[target];
        if (familyLine) acceptedLines.add(familyLine);

        const completedWitness = [...acceptedLines].some((line) =>
          rule.includes(`(unit-type-count-total ${line}`),
        );
        const pendingWitness = rule.includes(`(up-pending-objects c: ${target}`);

        assert.ok(
          completedWitness || pendingWitness,
          `[Queue witness] train ${target} at rule ${index} lacks a queued/completed witness for the trained unit or its engine unit line`,
        );
      }

      if (kind === "build") {
        const completedWitness = rule.includes(`(building-type-count-total ${target}`);
        const pendingWitness = rule.includes(`(up-pending-objects c: ${target}`);

        assert.ok(
          completedWitness || pendingWitness,
          `[Foundation witness] build ${target} at rule ${index} lacks a completed/pending witness for the same building`,
        );
      }
    }
  }
}

function validateScoutActionContracts(rules) {
  for (const [index, rule] of rules.entries()) {
    if (!rule.includes("(up-send-scout ")) continue;
    assert.ok(
      /\(unit-type-count (?:scout-cavalry-line|scout-cavalry) >= 1\)/.test(rule),
      "[Scout contract] up-send-scout rule " + index +
        " lacks a fielded Scout witness; unit-type-count-total is queue-inclusive and is not sufficient for dispatch",
    );
  }
}

function validateFarmEscrowContracts(rules) {
  for (const [index, rule] of rules.entries()) {
    if (!rule.includes("(can-build-with-escrow farm)")) continue;
    assert.ok(
      !rule.includes("(wood-amount >= bt-farm-build-wood)"),
      "[Escrow farm] farm rule " + index +
        " gates an escrow-aware build with raw wood-amount; rely on can-build-with-escrow before releasing wood",
    );
    assert.ok(
      rule.includes("(build farm)"),
      "[Escrow farm] farm rule " + index + " has escrow-aware feasibility but no build action",
    );
  }
}

function validateEcoResearchDemandRemoval(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const retired = [
    "bt-horse-collar-demand-goal",
    "bt-double-bit-axe-demand-goal",
    "bt-gold-mining-demand-goal",
    "bt-wheelbarrow-demand-goal",
    "bt-hand-cart-demand-goal",
    "bt-bow-saw-demand-goal",
    "bt-two-man-saw-demand-goal",
    "bt-gold-shaft-mining-demand-goal",
    "bt-stone-mining-demand-goal",
    "bt-stone-shaft-mining-demand-goal",
    "bt-heavy-plow-demand-goal",
    "bt-housing-demand-goal",
    "bt-mill-target-goal",
    "bt-university-demand-goal",
    "bt-imperial-prereq-demand-goal",
    "bt-castle-prereq-failure-history-goal",
    "bt-imperial-prereq-failure-history-goal",
    "bt-castle-cataphract-failure-history-goal",
  ];
  for (const symbol of retired) {
    assert.ok(
      !rules.some((rule) => rule.includes(symbol)),
      "[State removal] retired goal remains: " + symbol,
    );
  }

  const requireResearchRule = (tech, witnesses, label) => {
    const rule = rules.find(
      (candidate) =>
        candidate.includes("(research " + tech + ")") &&
        candidate.includes("(can-research-with-escrow " + tech + ")"),
    );
    assert.ok(rule, "[Eco direct] " + label + " research executor is missing");
    const text = normalize(rule);
    for (const witness of witnesses) {
      assert.ok(
        text.includes(witness),
        "[Eco direct] " + label + " is missing witness: " + witness,
      );
    }
    return rule;
  };

  requireResearchRule(
    "ri-horse-collar",
    [
      "(current-age == feudal-age)",
      "(up-research-status c: ri-horse-collar == research-available)",
      "(building-type-count mill >= 1)",
      "(goal bt-research-mill-claim-goal 0)",
    ],
    "Horse Collar",
  );
  requireResearchRule(
    "ri-double-bit-axe",
    [
      "(current-age == feudal-age)",
      "(up-research-status c: ri-double-bit-axe == research-available)",
      "(food-amount >= bt-double-bit-axe-food-buffer)",
      "(wood-amount >= bt-double-bit-axe-wood-buffer)",
      "(not (goal bt-castle-commitment-goal 1))",
      "(goal bt-research-lumber-camp-claim-goal 0)",
    ],
    "Double-Bit Axe",
  );
  requireResearchRule(
    "ri-gold-mining",
    [
      "(current-age >= castle-age)",
      "(goal bt-cataphract-demand-goal 1)",
      "(goal strategy-goal bt-strategy-flush)",
      "(goal unit-goal bt-unit-mix)",
      "(unit-type-count-total spearman-line >= bt-spear-target-1)",
      "(up-compare-goal bt-noncav-cavalry-level-goal >= 1)",
      "(building-type-count-total stable >= 1)",
      "(unit-type-count-total camel-line < bt-camel-target-1)",
      "(goal bt-research-mining-camp-claim-goal 0)",
    ],
    "Gold Mining",
  );
  requireResearchRule(
    "ri-hand-cart",
    [
      "(current-age >= castle-age)",
      "(goal strategy-goal bt-strategy-boom)",
      "(up-research-status c: ri-wheel-barrow >= research-complete)",
      "(building-type-count-total town-center >= 3)",
      "(up-compare-goal bt-research-town-center-failure-backoff-goal != ri-hand-cart)",
      "(goal bt-research-town-center-claim-goal 0)",
    ],
    "Hand Cart",
  );
  requireResearchRule(
    "ri-heavy-plow",
    [
      "(current-age == castle-age)",
      "(up-research-status c: ri-horse-collar >= research-complete)",
      "(building-type-count-total farm >= bt-mill-second-farm-threshold-1tc)",
      "(up-compare-goal bt-research-mill-failure-backoff-goal != ri-heavy-plow)",
      "(goal bt-research-mill-claim-goal 0)",
    ],
    "Heavy Plow",
  );
  requireResearchRule(
    "ri-two-man-saw",
    [
      "(current-age >= imperial-age)",
      "(unit-type-count villager >= bt-two-man-saw-villagers)",
      "(unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)",
      "(goal strategy-goal bt-strategy-boom)",
      "(not (goal bt-cataphract-demand-goal 1))",
      "(goal bt-research-lumber-camp-claim-goal 0)",
    ],
    "Two-Man Saw",
  );
  requireResearchRule(
    "ri-gold-shaft-mining",
    [
      "(current-age == castle-age)",
      "(goal strategy-goal bt-strategy-boom)",
      "(up-research-status c: ri-gold-mining >= research-complete)",
      "(building-type-count-total town-center >= 2)",
      "(not (can-research-with-escrow imperial-age))",
      "(not (goal bt-resource-mode-goal bt-resource-mode-imperial-bank-prep))",
      "(up-research-status c: ri-gold-shaft-mining == research-available)",
      "(up-compare-goal bt-research-mining-camp-failure-backoff-goal != ri-gold-shaft-mining)",
      "(building-type-count mining-camp >= 1)",
      "(goal bt-research-mining-camp-claim-goal 0)",
    ],
    "Gold Shaft Mining",
  );

  const stoneRules = rules.filter(
    (rule) =>
      rule.includes("(research ri-stone-mining)") &&
      rule.includes("(set-goal bt-research-mining-camp-claim-goal ri-stone-mining)"),
  );
  assert.equal(
    stoneRules.length,
    6,
    "[Stone direct] expected six direct Stone Mining action-boundary rules",
  );
  assert.ok(
    stoneRules.filter((rule) => rule.includes("bt-resource-mode-castle-stone-premium")).length >= 2,
    "[Stone direct] Castle-stone policy branch is missing",
  );
  assert.ok(
    stoneRules.filter((rule) => rule.includes("bt-resource-mode-tc-stone-premium")).length >= 2,
    "[Stone direct] TC-stone-premium policy branch is missing",
  );
  assert.ok(
    stoneRules.filter((rule) => rule.includes("bt-resource-mode-tc-stone")).length >= 2,
    "[Stone direct] TC-stone policy branch is missing",
  );
  assert.ok(
    stoneRules.filter((rule) => rule.includes("(goal bt-resource-mode-goal bt-resource-mode-imperial-bank-prep)")).length >= 3,
    "[Stone direct] Imperial-bank-safe branch is missing",
  );
  for (const rule of stoneRules) {
    const text = normalize(rule);
    for (const witness of [
      "(current-age >= feudal-age)",
      "(goal strategy-goal bt-strategy-boom)",
      "(can-research-with-escrow ri-stone-mining)",
      "(goal bt-research-mining-camp-claim-goal 0)",
      "(up-compare-goal bt-research-mining-camp-failure-backoff-goal != ri-stone-mining)",
    ]) {
      assert.ok(text.includes(witness), "[Stone direct] missing witness: " + witness);
    }
  }

  const housing = rules.find(
    (rule) =>
      rule.includes("(build house)") &&
      rule.includes("(housing-headroom <= bt-housing-headroom-trigger)") &&
      rule.includes("(building-type-count house >= 1)"),
  );
  assert.ok(housing, "[Housing direct] normal house executor must consume current headroom");
  assert.ok(
    housing.includes("(population-headroom <= 0)"),
    "[Housing direct] emergency population-headroom witness is missing",
  );

  const millRules = rules.filter(
    (rule) =>
      rule.includes("(goal bt-mill-project-goal 0)") &&
      rule.includes("(set-goal bt-mill-project-goal"),
  );
  assert.equal(
    millRules.length,
    5,
    "[Mill direct] expected five current-fact Mill project selectors",
  );
  assert.ok(
    millRules.some((rule) => rule.includes("(civilian-population >= 10)") && rule.includes("(set-goal bt-mill-project-goal 1)")),
    "[Mill direct] first-Mill selector is missing",
  );
  assert.ok(
    millRules.filter((rule) => rule.includes("(set-goal bt-mill-project-goal 2)")).length === 2,
    "[Mill direct] second-Mill selectors are missing",
  );
  assert.ok(
    millRules.filter((rule) => rule.includes("(set-goal bt-mill-project-goal 3)")).length === 2,
    "[Mill direct] third-Mill selectors are missing",
  );

  const universityRules = rules.filter(
    (rule) =>
      rule.includes("(build university)") &&
      rule.includes("(can-build-with-escrow university)"),
  );
  assert.ok(universityRules.length >= 2, "[University direct] shared University capability providers are missing");
  assert.ok(
    universityRules.some((rule) =>
      rule.includes("(goal bt-bombard-cannon-demand-goal 1)"),
    ),
    "[University direct] BBC/chemistry capability witness is missing",
  );
  assert.ok(
    universityRules.some((rule) => rule.includes("(building-type-count-total monastery >= 1)") && rule.includes("(building-type-count-total siege-workshop >= 1)")),
    "[University direct] Imperial two-of-three provider witness is missing",
  );

  const imperialFunding = rules.find(
    (rule) => rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)") &&
      rule.includes("(building-type-count-total monastery >= 1)"),
  );
  assert.ok(imperialFunding, "[Imperial direct] prerequisite funding rule is missing");
  for (const witness of [
    "(current-age == castle-age)",
    "(building-type-count-total castle < 1)",
    "(not (can-research-with-escrow imperial-age))",
    "(not (goal bt-resource-mode-goal bt-resource-mode-food-crisis))",
    "(not (goal bt-resource-mode-goal bt-resource-mode-gold-crisis))",
    "(not (goal bt-resource-mode-goal bt-resource-mode-wood-crisis))",
  ]) {
    assert.ok(
      imperialFunding.includes(witness),
      "[Imperial direct] funding rule is missing witness: " + witness,
    );
  }

  const imperialSiege = rules.find(
    (rule) =>
      rule.includes("(build siege-workshop)") &&
      rule.includes("(can-build-with-escrow siege-workshop)") &&
      rule.includes("(goal bt-imperial-prereq-backoff-goal 0)") &&
      rule.includes("(building-type-count-total monastery >= 1)"),
  );
  const imperialUniversity = rules.find(
    (rule) =>
      rule.includes("(build university)") &&
      rule.includes("(can-build-with-escrow university)") &&
      rule.includes("(goal bt-imperial-prereq-backoff-goal 0)") &&
      rule.includes("(building-type-count-total monastery >= 1)") &&
      rule.includes("(building-type-count-total siege-workshop >= 1)"),
  );
  assert.ok(imperialSiege, "[Imperial direct] Siege Workshop provider is missing");
  assert.ok(imperialUniversity, "[Imperial direct] University provider is missing");
}

function validateLateEcoTechnologyMaturity(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const cropRotationExecutor = rules.find(
    (rule) =>
      rule.includes("(research ri-crop-rotation)") &&
      rule.includes("(set-goal bt-research-mill-claim-goal ri-crop-rotation)"),
  );
  assert.ok(cropRotationExecutor, "[Late-eco lifecycle] Crop Rotation research executor is missing");
  const cropText = normalize(cropRotationExecutor);
  for (const witness of [
    "(current-age >= imperial-age)",
    "(building-type-count farm >= bt-crop-rotation-farm-threshold)",
    "(can-research-with-escrow ri-crop-rotation)",
  ]) {
    assert.ok(cropText.includes(witness), "[Late-eco lifecycle] Crop Rotation executor is missing maturity witness: " + witness);
  }

  const twoManExecutor = rules.find(
    (rule) =>
      rule.includes("(research ri-two-man-saw)") &&
      rule.includes("(can-research-with-escrow ri-two-man-saw)"),
  );
  assert.ok(twoManExecutor, "[Late-eco lifecycle] Two-Man Saw direct executor is missing");
  const twoManText = normalize(twoManExecutor);
  for (const witness of [
    "(current-age >= imperial-age)",
    "(unit-type-count villager >= bt-two-man-saw-villagers)",
    "(unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)",
    "(goal strategy-goal bt-strategy-boom)",
    "(not (goal bt-cataphract-demand-goal 1))",
  ]) {
    assert.ok(twoManText.includes(witness), "[Late-eco lifecycle] Two-Man Saw direct executor is missing witness: " + witness);
  }
}


function validateVillagerHygiene(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const requireRule = (needle, label) => {
    const rule = rules.find((candidate) => candidate.includes(needle));
    assert.ok(rule, "[Villager hygiene] missing " + label);
    return normalize(rule);
  };

  const dropsiteSafety = requireRule(
    "(set-strategic-number sn-defer-dropsite-update 1)",
    "completed-dropsite update deferral",
  );
  assert.ok(
    dropsiteSafety.includes("(true)"),
    "[Villager hygiene] dropsite update deferral must be a one-time initialization policy",
  );
  for (const witness of [
    "(set-strategic-number sn-dropsite-separation-distance bt-dropsite-normal-separation)",
    "(set-strategic-number sn-allow-adjacent-dropsites 0)",
    "(set-strategic-number sn-camp-max-distance bt-dropsite-radius-start)",
    "(set-strategic-number sn-lumber-camp-max-distance bt-dropsite-radius-start)",
    "(set-strategic-number sn-mining-camp-max-distance bt-dropsite-radius-start)",
  ]) {
    assert.ok(
      dropsiteSafety.includes(witness),
      "[Villager hygiene] dropsite initialization is missing witness: " + witness,
    );
  }

  for (const [campType, population] of [
    ["lumber-camp", "7"],
    ["mining-camp", "8"],
  ]) {
    const first = rules.find(
      (rule) =>
        rule.includes("(building-type-count-total " + campType + " == 0)") &&
        rule.includes("(civilian-population >= " + population + ")") &&
        rule.includes("(build " + campType + ")"),
    );
    assert.ok(
      first,
      "[Villager hygiene] first " + campType + " executor is missing",
    );
    for (const witness of [
      "(up-pending-objects c: " + campType + " == 0)",
      "(goal bt-dropsite-placement-claim-goal 0)",
      "(can-build " + campType + ")",
    ]) {
      assert.ok(
        first.includes(witness),
        "[Villager hygiene] first " + campType + " is missing witness: " + witness,
      );
    }
  }

  const dropsiteRelease = requireRule(
    "(set-goal bt-dropsite-placement-claim-goal 0)",
    "dropsite placement claim release",
  );
  for (const witness of [
    "(goal bt-dropsite-placement-claim-goal 1)",
    "(up-pending-objects c: lumber-camp == 0)",
    "(up-pending-objects c: mining-camp == 0)",
    "(set-strategic-number sn-allow-adjacent-dropsites 0)",
    "(set-strategic-number sn-dropsite-separation-distance bt-dropsite-normal-separation)",
  ]) {
    assert.ok(
      dropsiteRelease.includes(witness),
      "[Villager hygiene] dropsite placement release is missing witness: " + witness,
    );
  }

  const lumberRadius = requireRule(
    "(up-modify-sn sn-lumber-camp-max-distance c:+ bt-dropsite-radius-step)",
    "adaptive lumber-camp placement radius",
  );
  for (const witness of [
    "(resource-found wood)",
    "(dropsite-min-distance wood > 8)",
    "(strategic-number sn-lumber-camp-max-distance < bt-dropsite-radius-cap)",
  ]) {
    assert.ok(
      lumberRadius.includes(witness),
      "[Villager hygiene] lumber adaptive radius is missing witness: " + witness,
    );
  }

  const miningRadius = requireRule(
    "(up-modify-sn sn-mining-camp-max-distance c:+ bt-dropsite-radius-step)",
    "adaptive mining-camp placement radius",
  );
  for (const witness of [
    "(resource-found gold)",
    "(resource-found stone)",
    "(dropsite-min-distance gold > 8)",
    "(dropsite-min-distance stone > 8)",
    "(strategic-number sn-mining-camp-max-distance < bt-dropsite-radius-cap)",
  ]) {
    assert.ok(
      miningRadius.includes(witness),
      "[Villager hygiene] mining adaptive radius is missing witness: " + witness,
    );
  }

  for (const resource of ["wood", "gold", "stone"]) {
    const campType = resource === "wood" ? "lumber-camp" : "mining-camp";
    const rule = rules.find(
      (candidate) =>
        candidate.includes("(dropsite-min-distance " + resource + " > 8)") &&
        candidate.includes("(build " + campType + ")") &&
        candidate.includes("(set-goal bt-dropsite-placement-claim-goal 1)"),
    );
    assert.ok(
      rule,
      "[Villager hygiene] " + resource + " dropsite refresh executor is missing",
    );
    for (const witness of [
      "(resource-found " + resource + ")",
      "(up-pending-objects c: " + campType + " == 0)",
      "(goal bt-dropsite-placement-claim-goal 0)",
      "(can-build " + campType + ")",
      "(set-strategic-number sn-allow-adjacent-dropsites 1)",
      "(set-strategic-number sn-dropsite-separation-distance bt-dropsite-refresh-separation)",
    ]) {
      assert.ok(
        rule.includes(witness),
        "[Villager hygiene] " + resource + " refresh is missing witness: " + witness,
      );
    }
  }

  const attacker = requireRule(
    "(up-find-next-player enemy find-attacker bt-villager-defense-raider-player-goal)",
    "villager scout-raid attacker discovery",
  );
  assert.ok(attacker.includes("(up-enemy-units-in-town >= 1)"), "[Villager hygiene] scout defense must be town-local");
  assert.ok(attacker.includes("(players-unit-type-count any-enemy scout-cavalry-line >= 1)"), "[Villager hygiene] scout defense must require a small scout group");
  assert.ok(attacker.includes("(players-unit-type-count any-enemy scout-cavalry-line <= 2)"), "[Villager hygiene] scout defense must stay scoped to 1-2 scouts");

  const defense = requireRule(
    "(up-target-objects 0 action-default -1 stance-defensive)",
    "villager scout-raid defense action",
  );
  for (const witness of [
    "(up-find-local c: villager-class c: 6)",
    "(up-find-remote c: scout-cavalry-line c: 2)",
    "(up-get-fact player-number 0 bt-villager-defense-self-player-goal)",
    "(up-modify-sn sn-focus-player-number g:= bt-villager-defense-raider-player-goal)",
    "(up-modify-sn sn-focus-player-number g:= bt-villager-defense-self-player-goal)",
  ]) {
    assert.ok(
      defense.includes(witness),
      "[Villager hygiene] defense action missing witness: " + witness,
    );
  }
}

function validateScoutingLifecycle(sourceText, rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const source = sourceText.replace(/\s+/g, " ");
  const ruleSource = rules.map(normalize).join("\n");

  assert.ok(
    ruleSource.includes("(set-strategic-number sn-total-number-explorers 10)"),
    "[Scouting lifecycle] native explorer cap is not opened for early home scouting",
  );
  assert.ok(
    ruleSource.includes("(set-strategic-number sn-cap-civilian-explorers 0)"),
    "[Scouting lifecycle] civilian explorer cap must remain zero",
  );
  assert.ok(
    source.includes("(defconst bt-scout-first-pulse 30)"),
    "[Scouting lifecycle] explicit first scouting pulse must be 30 seconds",
  );
  assert.ok(
    source.includes("(defconst bt-scout-home-pulse 60)"),
    "[Scouting lifecycle] home-search pulse must remain 60 seconds or less",
  );
  assert.ok(
    source.includes("(defconst bt-scout-home-grace 300)"),
    "[Scouting lifecycle] protected home-search window must remain 300 seconds",
  );
  assert.ok(
    ruleSource.includes("(enable-timer bt-scouting-timer bt-scout-first-pulse)"),
    "[Scouting lifecycle] initial scouting timer must use the explicit first pulse",
  );
  assert.ok(
    ruleSource.includes("(set-strategic-number sn-home-exploration-time bt-scout-home-grace)"),
    "[Scouting lifecycle] home exploration window is missing",
  );

  const homeRule = rules.find(
    (rule) =>
      rule.includes("(up-send-scout bt-land-explore-group scout-flank)") &&
      rule.includes("(enable-timer bt-scouting-timer bt-scout-home-pulse)"),
  );
  assert.ok(
    homeRule,
    "[Scouting lifecycle] home-search pulse rule is missing",
  );
  const homeText = normalize(homeRule);
  for (const witness of [
    "(game-time < bt-scout-home-grace)",
    "(sheep-and-forage-too-far)",
    "(players-building-count target-player <= 0)",
  ]) {
    assert.ok(
      homeText.includes(witness),
      "[Scouting lifecycle] home-search rule is missing witness: " + witness,
    );
  }

  const enemyRule = rules.find(
    (rule) =>
      rule.includes("(up-send-scout bt-land-explore-group scout-enemy)") &&
      rule.includes("(enable-timer bt-scouting-timer bt-scout-enemy-pulse)"),
  );
  assert.ok(
    enemyRule,
    "[Scouting lifecycle] targeted enemy-search rule is missing",
  );
  const enemyText = normalize(enemyRule);
  for (const witness of [
    "(game-time >= bt-scout-home-grace)",
    "(not (sheep-and-forage-too-far))",
    "(players-building-count target-player > 0)",
  ]) {
    assert.ok(
      enemyText.includes(witness),
      "[Scouting lifecycle] enemy-search rule is missing witness: " + witness,
    );
  }
}

function validateDerivedThreatStateOrdering(rules) {
  const states = [
    "bt-cavalry-threat-goal",
    "bt-ranged-threat-goal",
    "bt-spear-threat-goal",
    "bt-any-threat-goal",
    "bt-cavalry-counter-level-goal",
    "bt-ranged-counter-level-goal",
    "bt-noncav-cavalry-level-goal",
  ];
  const reads = rules.flatMap((rule, index) =>
    states.some((state) =>
      rule.includes("(goal " + state) ||
      rule.includes("(up-compare-goal " + state),
    )
      ? [index]
      : [],
  );
  const firstConsumer = Math.min(...reads);
  assert.notEqual(
    firstConsumer,
    Infinity,
    "[State order] no threat/counter consumers found; regression fixture is invalid",
  );

  const resetNeedles = states.map(
    (state) => "(set-goal " + state + " 0)",
  );
  const resetCandidates = rules
    .map((rule, index) =>
      resetNeedles.every((needle) => rule.includes(needle)) ? index : -1,
    )
    .filter((index) => index >= 0);

  const resetIndex = Math.max(
    ...resetCandidates.filter((index) => index < firstConsumer),
    -1,
  );
  assert.notEqual(
    resetIndex,
    -1,
    "[State order] derived threat-state reset must occur before the first threat/counter consumer",
  );

  const writerSet = new Set(states);
  let blockEnd = resetIndex;
  const blockStates = new Set();
  const recordWriters = (rule) => {
    for (const state of states) {
      if (rule.includes("(set-goal " + state)) blockStates.add(state);
    }
  };
  recordWriters(rules[resetIndex]);
  while (blockEnd + 1 < rules.length) {
    const next = rules[blockEnd + 1];
    if (!states.some((state) => next.includes("(set-goal " + state))) break;
    blockEnd += 1;
    recordWriters(next);
  }

  assert.equal(
    blockStates.size,
    writerSet.size,
    "[State order] derived threat-state writer block does not populate every threat/counter state before consumption",
  );
  assert.ok(
    blockEnd < firstConsumer,
    "[State order] threat/counter derivation must complete before its first consumer; package logic currently reads stale state",
  );
}

function validateAttackContracts(rules) {
  const attackRules = rules.filter((rule) => rule.includes("(attack-now)"));
  assert.ok(
    attackRules.length > 0,
    "[Attack contract] no attack-now executor exists",
  );
  for (const [index, rule] of rules.entries()) {
    if (!rule.includes("(attack-now)")) continue;
    assert.ok(
      rule.includes("(timer-triggered bt-attack-timer)"),
      `[Attack contract] attack-now rule ${index} lacks the attack timer trigger`,
    );
    assert.ok(
      rule.includes("(goal attack-goal 0)"),
      `[Attack contract] attack-now rule ${index} lacks attack-goal idle gating`,
    );
    if (rule.includes("(goal strategy-goal bt-strategy-castle-power)")) {
      assert.ok(
        rule.includes("(unit-type-count crossbowman >= bt-standing-crossbow-target-goal)"),
        `[Attack completion] Castle-Power attack rule ${index} lacks actual Crossbow completion witness`,
      );
    }
    if (rule.includes("(goal strategy-goal bt-strategy-rush)")) {
      assert.ok(
        rule.includes("(unit-type-count archer-line >= bt-rush-attack-archer-witness)"),
        `[Attack completion] RUSH attack rule ${index} lacks completed Archer capability witness`,
      );
      assert.ok(
        !rule.includes("(unit-type-count-total archer-line >= bt-rush-attack-archer-witness)"),
        `[Attack completion] RUSH attack rule ${index} must not use queue-inclusive Archer count as its completion witness`,
      );
    }
  }
}


function validateResourceModeArbiter(rules) {
  const resetIndex = rules.findIndex(
    (rule) =>
      rule.includes("(true)") &&
      rule.includes("(set-goal bt-resource-mode-goal 0)") &&
      !rule.includes("(disable-self)"),
  );
  assert.ok(
    resetIndex >= 0,
    "[Resource mode] continuous mode recomputation reset is missing",
  );

  const modeWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(
      ({ rule }) =>
        /\(set-goal bt-resource-mode-goal [^)]+\)/.test(rule) &&
        !rule.includes("(set-goal bt-resource-mode-goal 0)"),
    );
  assert.ok(
    modeWriters.length >= 20,
    "[Resource mode] expected the layered mode arbitration writers",
  );
  const explicitOverrides = modeWriters.filter(
    ({ rule }) => !rule.includes("(goal bt-resource-mode-goal 0)"),
  );
  assert.equal(
    explicitOverrides.length,
    1,
    "[Resource mode] only the documented Imperial-prerequisite override may bypass the mode-0 idle gate",
  );
  assert.ok(
    explicitOverrides[0].rule.includes("(goal bt-imperial-prereq-demand-goal 1)") &&
      explicitOverrides[0].rule.includes("(not (goal bt-resource-mode-goal bt-resource-mode-food-crisis))") &&
      explicitOverrides[0].rule.includes("(not (goal bt-resource-mode-goal bt-resource-mode-gold-crisis))") &&
      explicitOverrides[0].rule.includes("(not (goal bt-resource-mode-goal bt-resource-mode-wood-crisis))") &&
      explicitOverrides[0].rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)"),
    "[Resource mode] the mode-0 exception must be the documented Imperial-prerequisite override and must explicitly yield to all P0 crises",
  );

  for (const { rule, index } of modeWriters) {
    assert.ok(
      index > resetIndex,
      "[Resource mode] mode writer must execute after the continuous reset",
    );
    if (!rule.includes("(goal bt-resource-mode-goal 0)")) continue;
  }

  const food = rules.findIndex((rule) =>
    rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-food-crisis)"),
  );
  const gold = rules.findIndex((rule) =>
    rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-gold-crisis)"),
  );
  const wood = rules.findIndex((rule) =>
    rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-wood-crisis)"),
  );
  const castleBank = rules.findIndex((rule) =>
    rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-castle-bank)"),
  );
  const baseMode = rules.findIndex((rule) =>
    rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-imperial-trash)"),
  );
  assert.ok(
    food > resetIndex &&
      gold > food &&
      wood > gold &&
      castleBank > wood &&
      baseMode > castleBank,
    "[Resource mode] source order no longer encodes P0 food -> gold -> wood -> bank -> base priority",
  );
}

function validateAttackResultLifecycle(rules) {
  const collapseConstant = rules.find((rule) =>
    rule.includes("(defconst bt-attack-collapse-force-floor -5)"),
  );
  assert.ok(
    collapseConstant,
    "[Attack result] severe-collapse force floor is missing",
  );

  const collapseIndex = rules.findIndex(
    (rule) =>
      rule.includes("(timer-triggered bt-attack-timer)") &&
      rule.includes("(goal attack-goal 1)") &&
      rule.includes("bt-attack-collapse-force-floor") &&
      rule.includes("(up-retreat-now)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)"),
  );
  const measurementConstant = rules.find((rule) =>
    rule.includes("(defconst bt-attack-measurement-seconds 180)"),
  );
  assert.ok(
    measurementConstant,
    "[Attack result] attack measurement window must use the community-aligned 180s cadence",
  );

  const start = rules.find((rule) =>
    rule.includes("(attack-now)") &&
    rule.includes("(up-get-target-fact building-count 0 bt-attack-target-buildings-start-goal)") &&
    rule.includes("(set-goal bt-attack-result-goal bt-attack-result-none)") &&
    rule.includes("(enable-timer bt-attack-timer bt-attack-measurement-seconds)"),
  );
  assert.ok(start, "[Attack result] attack entry lacks infrastructure snapshot/result reset");

  const measurementIndex = rules.findIndex(
    (rule) =>
      rule.includes("(timer-triggered bt-attack-timer)") &&
      rule.includes("(goal attack-goal 1)") &&
      rule.includes("(up-get-target-fact building-count 0 bt-attack-target-buildings-now-goal)") &&
      rule.includes("(set-goal attack-goal 0)"),
  );
  assert.ok(
    collapseIndex >= 0 && measurementIndex >= 0 && collapseIndex < measurementIndex,
    "[Attack result] severe-collapse close must precede normal attack measurement reset",
  );

  const end = rules.find((rule) =>
    rule.includes("(timer-triggered bt-attack-timer)") &&
    rule.includes("(goal attack-goal 1)") &&
    rule.includes("(up-get-target-fact building-count 0 bt-attack-target-buildings-now-goal)") &&
    rule.includes("(up-modify-goal bt-attack-buildings-destroyed-goal g:= bt-attack-target-buildings-start-goal)") &&
    rule.includes("(set-goal attack-goal 0)"),
  );
  assert.ok(end, "[Attack result] attack timer lacks a completed infrastructure-result witness");

  const resultRules = rules.filter(
    (rule) =>
      rule.includes("(goal attack-goal 0)") &&
      rule.includes("(goal bt-attack-result-goal bt-attack-result-none)") &&
      /\\(set-goal bt-attack-result-goal bt-attack-result-(damaged|stalled|reassess)\\)/.test(rule),
  );
  assert.equal(resultRules.length, 5, "[Attack result] expected damaged, second-stall, first-stall, generic-stall, and reassess result consumers");

  const gatherFailure = rules.find(
    (rule) =>
      rule.includes("(timer-triggered bt-attack-gather-watchdog-timer)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 1)"),
  );
  assert.ok(gatherFailure, "[Attack result] failed attack gathering must close as a stalled result");

  const retreatFailure = rules.find(
    (rule) =>
      rule.includes("(goal retreat-now-goal 0)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 1)"),
  );
  assert.ok(retreatFailure, "[Attack result] emergency retreat must close as a stalled result");

  assert.ok(
    resultRules.some(
      (rule) =>
        rule.includes("(up-compare-goal bt-attack-buildings-destroyed-goal >= 1)") &&
        rule.includes("bt-attack-result-damaged") &&
        rule.includes("(enable-timer bt-attack-timer 120)"),
    ),
    "[Attack result] damaged result path is missing",
  );
  assert.ok(
    resultRules.some(
      (rule) =>
        rule.includes("(up-compare-goal bt-attack-buildings-destroyed-goal <= 0)") &&
        rule.includes("(up-compare-goal bt-relative-force-goal < 0)") &&
        rule.includes("(set-goal bt-standing-army-demand-goal 1)") &&
        rule.includes("(enable-timer bt-attack-timer 300)"),
    ),
    "[Attack result] stalled/behind result path must rebuild the standing army",
  );
  assert.ok(
    resultRules.some(
      (rule) =>
        rule.includes("(up-compare-goal bt-attack-buildings-destroyed-goal <= 0)") &&
        rule.includes("(up-compare-goal bt-relative-force-goal >= 0)") &&
        rule.includes("bt-attack-result-reassess") &&
        rule.includes("(enable-timer bt-attack-timer 180)"),
    ),
    "[Attack result] non-positive-damage parity path is missing",
  );
}

function validateRushStallFailurePolicy(rules, sourceText) {
  assert.ok(
    sourceText.includes("(defconst bt-rush-stall-latch-goal 775)"),
    "[RUSH stall] persistent stall latch must use GoalId 775",
  );

  assert.ok(
    sourceText.includes(
      "(set-goal bt-attack-result-goal bt-attack-result-none)\n    (set-goal bt-rush-stall-latch-goal 0)\n",
    ),
    "[RUSH stall] stall latch is not initialized to zero in the strategy/threat initialization rule",
  );

  const rushWriterIndices = rules
    .map((rule, index) => ({ rule, index }))
    .filter(({ rule }) => rule.includes("(set-goal strategy-goal bt-strategy-rush)"))
    .map(({ index }) => index);

  const latchClearIndex = rules.findIndex(
    (rule) =>
      rule.includes("(not (goal strategy-goal bt-strategy-rush))") &&
      rule.includes("(up-compare-goal bt-rush-stall-latch-goal != 0)") &&
      rule.includes("(set-goal bt-rush-stall-latch-goal 0)"),
  );
  assert.ok(latchClearIndex >= 0, "[RUSH stall] non-RUSH latch cleanup rule is missing");
  assert.ok(
    rushWriterIndices.length > 0 && latchClearIndex > Math.max(...rushWriterIndices),
    "[RUSH stall] latch cleanup must run after every RUSH strategy writer",
  );

  const resultNone = "(goal bt-attack-result-goal bt-attack-result-none)";
  const noDamage = "(up-compare-goal bt-attack-buildings-destroyed-goal <= 0)";
  const inferior = "(up-compare-goal bt-relative-force-goal < 0)";

  const secondStallIndex = rules.findIndex(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-rush)") &&
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal bt-rush-stall-latch-goal 1)") &&
      rule.includes("(goal attack-goal 0)") &&
      rule.includes(resultNone) &&
      rule.includes(noDamage) &&
      rule.includes(inferior) &&
      rule.includes("(set-goal strategy-goal bt-strategy-boom)") &&
      rule.includes("(set-goal bt-rush-stall-latch-goal 0)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)") &&
      rule.includes("(enable-timer bt-attack-timer 300)"),
  );
  assert.ok(secondStallIndex >= 0, "[RUSH stall] second consecutive inferior stall release is missing");

  const firstStallIndex = rules.findIndex(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-rush)") &&
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal bt-rush-stall-latch-goal 0)") &&
      rule.includes("(goal attack-goal 0)") &&
      rule.includes(resultNone) &&
      rule.includes(noDamage) &&
      rule.includes(inferior) &&
      rule.includes("(set-goal bt-rush-stall-latch-goal 1)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)") &&
      rule.includes("(enable-timer bt-attack-timer 300)"),
  );
  assert.ok(firstStallIndex >= 0, "[RUSH stall] first consecutive inferior stall latch is missing");

  const genericStallIndex = rules.findIndex(
    (rule) =>
      rule.includes(resultNone) &&
      rule.includes(noDamage) &&
      rule.includes(inferior) &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-stalled)") &&
      !rule.includes("(goal strategy-goal bt-strategy-rush)") &&
      !rule.includes("(set-goal bt-rush-stall-latch-goal 1)") &&
      !rule.includes("(set-goal strategy-goal bt-strategy-boom)"),
  );
  assert.ok(genericStallIndex >= 0, "[RUSH stall] generic stalled result consumer disappeared");

  const damagedIndex = rules.findIndex(
    (rule) =>
      rule.includes("(up-compare-goal bt-attack-buildings-destroyed-goal >= 1)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-damaged)") &&
      rule.includes("(set-goal bt-rush-stall-latch-goal 0)"),
  );
  assert.ok(damagedIndex >= 0, "[RUSH stall] structural damage must clear the latch");

  const reassessIndex = rules.findIndex(
    (rule) =>
      rule.includes("(up-compare-goal bt-attack-buildings-destroyed-goal <= 0)") &&
      rule.includes("(up-compare-goal bt-relative-force-goal >= 0)") &&
      rule.includes("(set-goal bt-attack-result-goal bt-attack-result-reassess)") &&
      rule.includes("(set-goal bt-rush-stall-latch-goal 0)"),
  );
  assert.ok(reassessIndex >= 0, "[RUSH stall] reassessment must clear the latch");

  assert.ok(
    secondStallIndex < firstStallIndex &&
      firstStallIndex < genericStallIndex &&
      genericStallIndex < reassessIndex,
    "[RUSH stall] result arbitration order is broken: second-stall release -> first-stall latch -> generic stall -> reassess expected",
  );

  assert.ok(
    firstStallIndex > damagedIndex,
    "[RUSH stall] first-stall latch must follow the damage result partition",
  );

  const attackResultRules = rules.filter(
    (rule) => rule.includes(resultNone) && rule.includes("(goal attack-goal 0)"),
  );
  assert.ok(
    attackResultRules.some((rule) => rule.includes("(set-goal strategy-goal bt-strategy-boom)")),
    "[RUSH stall] second-stall rule must be an explicit strategy transition, not a hidden result code",
  );

  const strategyConstants = [...sourceText.matchAll(/\(defconst\s+(bt-strategy-[A-Za-z0-9_-]+)\s+(-?\d+)\)/g)]
    .map((match) => match[1]);
  assert.deepEqual(
    new Set(strategyConstants),
    new Set([
      "bt-strategy-flush",
      "bt-strategy-rush",
      "bt-strategy-boom",
      "bt-strategy-castle-power",
    ]),
    "[RUSH stall] implementation introduced a fifth strategy state",
  );

  const policy = { strategy: "rush", feudal: true, latch: 0 };
  const measured = (result) => {
    if (result === "damage") {
      policy.latch = 0;
      return;
    }
    if (result === "reassess") {
      policy.latch = 0;
      return;
    }
    if (result === "stall") {
      if (policy.strategy === "rush" && policy.feudal && policy.latch === 1) {
        policy.strategy = "boom";
        policy.latch = 0;
      } else if (policy.strategy === "rush" && policy.feudal && policy.latch === 0) {
        policy.latch = 1;
      }
    }
  };

  measured("stall");
  assert.equal(policy.strategy, "rush", "[RUSH stall replay] first measured stall must preserve RUSH");
  assert.equal(policy.latch, 1, "[RUSH stall replay] first measured stall must arm the latch");

  measured("stall");
  assert.equal(policy.strategy, "boom", "[RUSH stall replay] second consecutive measured stall must release to BOOM");
  assert.equal(policy.latch, 0, "[RUSH stall replay] second stall must consume the latch");

  policy.strategy = "rush";
  measured("damage");
  measured("stall");
  assert.equal(policy.strategy, "rush", "[RUSH stall replay] damage must reset history before a later stall");

  policy.strategy = "rush";
  policy.latch = 1;
  measured("reassess");
  measured("stall");
  assert.equal(policy.strategy, "rush", "[RUSH stall replay] reassess must break consecutiveness before a later stall");
  assert.equal(policy.latch, 1, "[RUSH stall replay] post-reassess stall should arm, not release");

  policy.strategy = "rush";
  policy.latch = 1;
  measured("stall");
  assert.equal(policy.strategy, "boom", "[RUSH stall replay] a second consecutive stall after reassess-free history must release");

  policy.strategy = "rush";
  policy.latch = 1;
  policy.strategy = "flush";
  if (policy.strategy !== "rush") policy.latch = 0;
  assert.equal(policy.latch, 0, "[RUSH stall replay] leaving RUSH must clear stale history");
}

function validateAttackAllocationPolicy(rules) {
  const expected = new Map([
    [4, 72],
    [6, 63],
    [12, 46],
    [16, 39],
    [20, 34],
    [26, 28],
    [30, 25],
    [34, 23],
    [42, 20],
  ]);
  for (const [floor, percent] of expected) {
    assert.ok(
      rules.some((rule) =>
        rule.includes(`(up-compare-goal bt-standing-army-floor-goal == ${floor})`) &&
        rule.includes(`(set-strategic-number sn-percent-attack-soldiers ${percent})`),
      ),
      `[Attack allocation] standing floor ${floor} is missing its explicit ${percent}% attack allocation`,
    );
  }
}

function validateFeudalCastleEconomyContract(rules) {
  const castleThresholdIndex = rules.findIndex((rule) =>
    rule.includes("(defconst bt-castle-villagers 28)"),
  );
  assert.ok(
    castleThresholdIndex >= 0,
    "[Feudal economy] Castle transition threshold must be 28 villagers",
  );

  const boomFloorIndex = rules.findIndex((rule) =>
    rule.includes("(current-age == feudal-age)") &&
    rule.includes("(goal strategy-goal bt-strategy-boom)") &&
    rule.includes("(set-goal bt-standing-army-floor-goal bt-feudal-boom-army-floor)"),
  );
  assert.ok(
    boomFloorIndex >= 0,
    "[Feudal economy] BOOM Feudal floor must be normalized to the two-unit economic-defense floor",
  );

  const roleIndex = rules.findIndex((rule) =>
    rule.includes("(up-compare-goal bt-standing-army-floor-goal == bt-feudal-boom-army-floor)") &&
    rule.includes("(set-goal bt-standing-spear-target-goal bt-feudal-boom-spear-target)") &&
    rule.includes("(set-goal bt-standing-skirm-target-goal bt-feudal-boom-skirm-target)"),
  );
  assert.ok(
    roleIndex >= 0,
    "[Feudal economy] two-unit BOOM role targets are missing",
  );

  const attack = rules.find((rule) =>
    rule.includes("(attack-now)") &&
    rule.includes("(set-goal attack-goal 1)") &&
    rule.includes("(goal bt-castle-commitment-goal 0)"),
  );
  assert.ok(
    attack &&
      attack.includes("(goal strategy-goal bt-strategy-rush)") &&
      attack.includes("(goal strategy-goal bt-strategy-flush)") &&
      !attack.includes("(goal strategy-goal bt-strategy-boom)"),
    "[Feudal economy] Feudal attack authorization must be restricted to pressure postures and blocked during Castle commitment",
  );

  const floorWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(({ rule }) =>
      rule.includes("(set-goal bt-standing-army-floor-goal") &&
      rule.includes("(current-age == feudal-age)"),
    )
    .map(({ index }) => index);
  assert.ok(
    floorWriters.length > 0 && boomFloorIndex > Math.max(...floorWriters.filter((index) => index !== boomFloorIndex)),
    "[Feudal economy] BOOM floor normalization must execute after generic Feudal floor writers",
  );
}

function validateFeudalFarmTransitionBudget(rules, sourceText) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const nums = new Map(
    [...sourceText.matchAll(/\(defconst\s+([A-Za-z0-9_-]+)\s+(-?\d+)\)/g)]
      .map((m) => [m[1], Number(m[2])]),
  );
  assert.equal(
    nums.get("bt-feudal-farm-wood-floor"),
    385,
    "[Feudal farm budget] wood floor must preserve 150W Blacksmith + 175W Market + 60W Farm",
  );
  assert.equal(
    nums.get("bt-feudal-farm-reserve-villagers"),
    26,
    "[Feudal farm budget] reserve window must begin at 26 villagers",
  );
  assert.equal(
    nums.get("bt-feudal-farm-wood-hold-goal"),
    773,
    "[Feudal farm budget] hold goal must own its dedicated goal id",
  );

  const writer = rules.filter(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal strategy-goal bt-strategy-boom)") &&
      rule.includes("(unit-type-count villager >= bt-feudal-farm-reserve-villagers)") &&
      rule.includes("(unit-type-count villager < bt-castle-villagers)") &&
      rule.includes("(food-amount >= 350)") &&
      rule.includes("(not (can-research-with-escrow castle-age))") &&
      rule.includes("(wood-amount < bt-feudal-farm-wood-floor)") &&
      rule.includes("(set-goal bt-feudal-farm-wood-hold-goal 1)"),
  );
  assert.equal(
    writer.length,
    1,
    "[Feudal farm budget] BOOM farm-budget writer must be unique and complete",
  );

  const release = rules.filter(
    (rule) =>
      rule.includes("(goal bt-feudal-farm-wood-hold-goal 1)") &&
      rule.includes("(set-goal bt-feudal-farm-wood-hold-goal 0)") &&
      rule.includes("(current-age != feudal-age)") &&
      rule.includes("(unit-type-count villager >= bt-castle-villagers)") &&
      rule.includes("(wood-amount >= bt-feudal-farm-wood-floor)") &&
      rule.includes("(food-amount < 350)") &&
      rule.includes("(not (goal strategy-goal bt-strategy-boom))"),
  );
  assert.equal(
    release.length,
    1,
    "[Feudal farm budget] BOOM farm-budget release must be unique and retain all exit witnesses",
  );

  const feudalFarmExecutors = rules.filter(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(can-build-with-escrow farm)") &&
      rule.includes("(build farm)") &&
      rule.includes("(building-type-count-total farm < bt-farm-feudal-cap)"),
  );
  assert.equal(
    feudalFarmExecutors.length,
    1,
    "[Feudal farm budget] exactly one Feudal farm executor may exist so no pressure posture can bypass the BOOM wood hold",
  );
  const farmExecutorIndex = rules.indexOf(feudalFarmExecutors[0]);
  assert.ok(
    feudalFarmExecutors[0].includes("(goal bt-feudal-farm-wood-hold-goal 0)"),
    "[Feudal farm budget] Feudal farm executor must honor the BOOM wood hold",
  );

  const writerIndex = rules.indexOf(writer[0]);
  const releaseIndex = rules.indexOf(release[0]);
  assert.ok(
    writerIndex < releaseIndex && releaseIndex < farmExecutorIndex,
    "[Feudal farm budget] writer -> release -> Feudal farm executor source order is invalid",
  );

  const rawFarmGate = rules.find(
    (rule) =>
      rule.includes("(can-build-with-escrow farm)") &&
      rule.includes("(wood-amount >= bt-feudal-farm-wood-floor)"),
  );
  assert.equal(
    rawFarmGate,
    undefined,
    "[Feudal farm budget] escrow-aware farm executor must not duplicate the wood floor as a raw resource gate",
  );
}

function validateImperialSiegeAttackOrdering(rules) {
  const attackIndex = rules.findIndex(
    (rule) =>
      rule.includes("(timer-triggered bt-attack-timer)") &&
      rule.includes("(current-age >= feudal-age)") &&
      rule.includes("(players-building-count any-enemy > 0)") &&
      rule.includes("(set-goal attack-goal 1)") &&
      rule.includes("(attack-now)"),
  );
  const abortIndex = rules.findIndex(
    (rule) =>
      rule.includes("(goal bt-imperial-siege-package-goal 1)") &&
      rule.includes("(military-population < bt-imperial-siege-abort-army-floor)") &&
      rule.includes("(set-goal bt-imperial-siege-package-goal 0)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 1)"),
  );
  assert.ok(
    attackIndex >= 0,
    "[Imperial siege] attack opener not found for collapse-order validation",
  );
  assert.ok(
    abortIndex >= 0,
    "[Imperial siege] collapse rule not found for collapse-order validation",
  );
  assert.ok(
    abortIndex < attackIndex,
    "[Imperial siege] army-collapse abort must execute before attack authorization",
  );
}

function validateImperialSiegeExit(rules, sourceText) {
  const nums = new Map(
    [...sourceText.matchAll(/\(defconst\s+([A-Za-z0-9_-]+)\s+(-?\d+)\)/g)]
      .map((m) => [m[1], Number(m[2])]),
  );
  assert.equal(
    nums.get("bt-imperial-siege-army-floor"),
    30,
    "[Imperial siege] entry floor changed unexpectedly",
  );
  assert.equal(
    nums.get("bt-imperial-siege-abort-army-floor"),
    20,
    "[Imperial siege] abort floor must provide a 10-unit hysteresis band",
  );

  const entry = rules.find(
    (rule) =>
      rule.includes("(goal bt-imperial-siege-package-goal 0)") &&
      rule.includes("(current-age >= imperial-age)") &&
      rule.includes("(up-compare-goal bt-standing-army-floor-goal >= bt-imperial-siege-army-floor)") &&
      rule.includes("(set-goal bt-imperial-siege-package-goal 1)"),
  );
  assert.ok(entry, "[Imperial siege] package entry gate is missing");

  const abort = rules.find(
    (rule) =>
      rule.includes("(goal bt-imperial-siege-package-goal 1)") &&
      rule.includes("(military-population < bt-imperial-siege-abort-army-floor)") &&
      rule.includes("(set-goal bt-imperial-siege-package-goal 0)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 1)"),
  );
  assert.ok(abort, "[Imperial siege] military-collapse exit is missing");
  for (const demand of [
    "bt-research-siege-package-goal",
    "bt-trebuchet-demand-goal",
    "bt-trebuchet-target-goal",
    "bt-ram-demand-goal",
    "bt-bombard-cannon-demand-goal",
  ]) {
    assert.ok(
      abort.includes("(set-goal " + demand + " 0)"),
      "[Imperial siege] collapse exit must clear package-owned demand " + demand,
    );
  }

  for (const demand of [
    "bt-mangonel-demand-goal",
    "bt-onager-demand-goal",
    "bt-scorpion-demand-goal",
    "bt-scorpion-ballistics-demand-goal",
    "bt-siege-tower-demand-goal",
  ]) {
    assert.ok(
      !abort.includes("(set-goal " + demand + " 0)"),
      "[Imperial siege] collapse exit must not cancel generic independently-owned demand " + demand,
    );
  }
}

function validateTcScaledFarms(rules) {
  const twoTc = rules.filter(
    (rule) =>
      rule.includes("(building-type-count-total town-center >= 2)") &&
      rule.includes("(up-modify-goal bt-farm-transition-reserve-goal c:+ 2)") &&
      rule.includes("(up-modify-goal bt-farm-depleted-reserve-goal c:+ 3)"),
  );
  const threeTc = rules.filter(
    (rule) =>
      rule.includes("(building-type-count-total town-center >= 3)") &&
      rule.includes("(up-modify-goal bt-farm-transition-reserve-goal c:+ 2)") &&
      rule.includes("(up-modify-goal bt-farm-depleted-reserve-goal c:+ 3)"),
  );
  assert.equal(twoTc.length, 1, "[Farm capacity] missing unique 2-TC reserve correction");
  assert.equal(threeTc.length, 1, "[Farm capacity] missing unique 3-TC reserve correction");

  const baseWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(({ rule }) => rule.includes("(set-goal bt-farm-transition-reserve-goal"));
  const correctionIndices = rules
    .map((rule, index) => ({ rule, index }))
    .filter(({ rule }) =>
      rule.includes("(up-modify-goal bt-farm-transition-reserve-goal c:+ 2)"),
    )
    .map(({ index }) => index);
  const firstFarmExecutor = rules.findIndex(
    (rule) => rule.includes("(build farm)") && rule.includes("(can-build-with-escrow farm)"),
  );

  assert.ok(
    correctionIndices.length === 2 &&
      Math.min(...correctionIndices) > Math.max(...baseWriters.map(({ index }) => index)),
    "[Farm capacity] TC corrections must run after the age/population reserve model",
  );
  assert.ok(
    firstFarmExecutor > Math.max(...correctionIndices),
    "[Farm capacity] TC correction must precede farm execution",
  );
}

function validateNoDuplicateRules(rules) {
  const seen = new Map();
  const normalize = (rule) =>
    rule.replace(/;[^\n]*/g, "").replace(/\s+/g, " ").trim();
  for (const rule of rules) {
    const key = normalize(rule);
    seen.set(key, (seen.get(key) || 0) + 1);
  }
  const duplicates = [...seen.entries()].filter(([, count]) => count > 1);
  assert.equal(
    duplicates.length,
    0,
    "[Rule hygiene] exact executable defrule duplicates remain: " + duplicates.length,
  );
}

function validateBackoffTimerUniqueness(rules) {
  const expectedTimers = [
    "bt-research-town-center-failure-backoff-timer",
    "bt-research-mill-failure-backoff-timer",
    "bt-research-lumber-camp-failure-backoff-timer",
    "bt-research-mining-camp-failure-backoff-timer",
    "bt-research-blacksmith-failure-backoff-timer",
    "bt-research-university-failure-backoff-timer",
    "bt-research-castle-failure-backoff-timer",
    "bt-research-barracks-failure-backoff-timer",
    "bt-research-archery-range-failure-backoff-timer",
    "bt-research-stable-failure-backoff-timer",
    "bt-research-siege-workshop-failure-backoff-timer",
    "bt-research-monastery-failure-backoff-timer",
    "bt-research-age-failure-backoff-timer",
  ];
  const groups = new Map();
  for (const rule of rules) {
    const match = rule.match(
      /\(timer-triggered (bt-research-[A-Za-z0-9-]+-failure-backoff-timer)\)/,
    );
    if (!match) continue;
    const timer = match[1];
    const reset = /\(set-goal (bt-research-[A-Za-z0-9-]+-failure-backoff-goal) 0\)/.test(rule);
    if (!reset) continue;
    groups.set(timer, (groups.get(timer) || 0) + 1);
  }

  assert.equal(
    groups.size,
    expectedTimers.length,
    "[Retry fairness] expected exactly " + expectedTimers.length + " capability-local failure-backoff expiry owners; found " + groups.size,
  );
  for (const timer of expectedTimers) {
    assert.equal(
      groups.get(timer),
      1,
      "[Retry fairness] failure-backoff timer must have exactly one expiry owner: " + timer,
    );
  }
}

function validateBasiliskGoalNamespace(forms) {
  const numericGoals = new Map();
  for (const form of forms) {
    if (form.head !== "defconst") continue;
    const name = form.args[0]?.value;
    const value = form.args[1]?.value;
    if (!name || !/goal$/i.test(name) || !/^-?\d+$/.test(value ?? "")) continue;
    const id = Number(value);
    if (!numericGoals.has(id)) numericGoals.set(id, []);
    numericGoals.get(id).push(name);
  }

  for (const [id, names] of numericGoals.entries()) {
    assert.equal(
      names.length,
      1,
      "[Goal namespace] duplicate GoalId " + id + ": " + names.join(", "),
    );
  }

  for (const id of [730, 734, 769, 770, 771, 772, 775]) {
    assert.ok(
      numericGoals.has(id),
      "[Goal namespace] reserved high-range GoalId " + id + " is missing",
    );
  }

  assert.ok(
    forms.some(
      (form) =>
        form.head === "defconst" &&
        form.args[0]?.value === "bt-debug-last-strategy-goal" &&
        form.args[1]?.value === "768",
    ),
    "[Goal namespace] diagnostic strategy latch must use GoalId 768 after the historical 710 collision",
  );
}

function validateBasiliskPreemption(rules, sourceText, repoRootPath) {
  for (const symbol of [
    "bt-preempt-original-owner-goal",
    "bt-preempt-emergency-claim",
    "bt-preempt-defense-issued-goal",
  ]) {
    assert.ok(
      sourceText.includes(symbol),
      "[Preemption] missing required state: " + symbol,
    );
  }

  const forbiddenClaims = [
    "bt-castle-blacksmith-claim",
    "bt-castle-market-claim",
    "bt-castle-cataphract-claim",
    "bt-imperial-siege-claim",
    "bt-imperial-university-claim",
    "bt-monastery-claim",
    "bt-mill-claim",
    "bt-university-claim",
    "bt-bombard-university-claim",
    "bt-military-siege-workshop-claim",
  ];
  for (const claim of forbiddenClaims) {
    assert.ok(
      !rules.some(
        (rule) =>
          rule.includes("(town-under-attack)") &&
          rule.includes("(set-strategic-number sn-resource-control bt-preempt-emergency-claim)") &&
          rule.includes(claim),
      ),
      "[Preemption] protected claim is eligible for emergency displacement: " + claim,
    );
  }

  const beginClaims = ["bt-tc2-claim", "bt-tc3-claim"];
  for (const claim of beginClaims) {
    const begin = rules.find(
      (rule) =>
        rule.includes("(town-under-attack)") &&
        rule.includes("(goal bt-any-threat-goal 1)") &&
        rule.includes("(strategic-number sn-resource-control == " + claim + ")") &&
        rule.includes("(set-goal bt-preempt-original-owner-goal " + claim + ")") &&
        rule.includes("(set-strategic-number sn-resource-control bt-preempt-emergency-claim)"),
    );
    assert.ok(begin, "[Preemption] begin handshake missing for " + claim);

    const beginText = begin.replace(/\s+/g, " ");
    assert.ok(
      beginText.indexOf("(set-goal bt-preempt-original-owner-goal " + claim + ")") <
        beginText.indexOf("(set-strategic-number sn-resource-control bt-preempt-emergency-claim)"),
      "[Preemption] original owner must be snapshotted before emergency ownership for " + claim,
    );
    const resume = rules.find(
      (rule) =>
        rule.includes("(not (town-under-attack))") &&
        rule.includes("(goal bt-preempt-original-owner-goal " + claim + ")") &&
        rule.includes("(set-strategic-number sn-resource-control " + claim + ")"),
    );
    assert.ok(resume, "[Preemption] resume path missing for " + claim);
    assert.ok(
      !/\((?:disable|enable)-timer\s+bt-tc[23]-watchdog-timer\b/.test(resume),
      "[Preemption] resume path must not reset TC watchdog timer for " + claim,
    );

    const abort = rules.find(
      (rule) =>
        rule.includes("(not (town-under-attack))") &&
        rule.includes("(goal bt-preempt-original-owner-goal " + claim + ")") &&
        rule.includes("(set-strategic-number sn-resource-control 0)"),
    );
    assert.ok(abort, "[Preemption] abort path missing for " + claim);
    assert.ok(
      abort.includes("(set-goal bt-tc-stage-goal bt-tc-stage-demanded)"),
      "[Preemption] abort must return " + claim + " to persistent TC demand",
    );
  }

    
  for (const claim of beginClaims) {
    const completion = rules.find(
      (rule) =>
        rule.includes("(goal bt-preempt-original-owner-goal " + claim + ")") &&
        rule.includes("(building-type-count town-center") &&
        rule.includes("(strategic-number sn-resource-control == bt-preempt-emergency-claim)") &&
        rule.includes("(set-strategic-number sn-resource-control 0)"),
    );
    assert.ok(
      completion,
      "[Preemption] completion path must terminate emergency ownership for " + claim,
    );
  }

  const defenseRules = rules.filter(
    (rule) =>
      rule.includes("(strategic-number sn-resource-control == bt-preempt-emergency-claim)") &&
      /\(train (?:spearman-line|skirmisher-line)\)/.test(rule),
  );
  assert.equal(
    defenseRules.length,
    2,
    "[Preemption] expected exactly two bounded emergency counter rules",
  );
  for (const rule of defenseRules) {
    assert.ok(
      rule.includes("(can-train "),
      "[Preemption] emergency counter lacks engine-native feasibility",
    );
    assert.ok(
      /up-pending-objects c: (?:spearman-line|skirmisher-line)/.test(rule) ||
        /unit-type-count-total (?:spearman-line|skirmisher-line)/.test(rule),
      "[Preemption] emergency counter lacks queue/completed unit witness",
    );
  }

  const preemptionRules = rules.filter((rule) =>
    rule.includes("bt-preempt-"),
  );
  for (const rule of preemptionRules) {
    assert.ok(
      !rule.includes("(disable-timer bt-tc2-watchdog-timer)") &&
        !rule.includes("(enable-timer bt-tc2-watchdog-timer") &&
        !rule.includes("(disable-timer bt-tc3-watchdog-timer)") &&
        !rule.includes("(enable-timer bt-tc3-watchdog-timer"),
      "[Preemption] capability watchdog may not be reset by interruption logic",
    );
  }

  assert.equal(
    rules.filter((rule) =>
      rule.includes("(set-strategic-number sn-resource-control bt-preempt-emergency-claim)")
    ).length,
    2,
    "[Preemption] exactly two claim classes may acquire emergency ownership",
  );

}

function extractRawRules(text) {
  const rawRules = [];
  const sanitized = sanitizeStructure(text);
  let cursor = 0;
  while ((cursor = sanitized.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    assert.notEqual(
      end,
      -1,
      "[Missing closing parenthesis] raw defrule begins near source offset " + cursor,
    );
    rawRules.push(text.slice(cursor, end));
    cursor = end;
  }
  return rawRules;
}

function validateAgeNarrationLatches(sourceText, rules) {
  const latches = [
    "bt-debug-age-feudal-bank-goal",
    "bt-debug-age-feudal-start-goal",
    "bt-debug-age-feudal-complete-goal",
    "bt-debug-age-castle-bank-goal",
    "bt-debug-age-castle-start-goal",
    "bt-debug-age-castle-complete-goal",
    "bt-debug-age-imperial-bank-goal",
    "bt-debug-age-imperial-start-goal",
    "bt-debug-age-imperial-complete-goal",
  ];
  for (const latch of latches) {
    assert.ok(sourceText.includes(latch), "[Narration] missing independent age latch: " + latch);
  }
  const rawRules = extractRawRules(sourceText);
  const ageMessages = rawRules.filter(
    (rule) => rule.includes('(chat-local-to-self "BASILISK | AGE |') &&
      rule.includes("(set-goal bt-debug-age-"),
  );
  assert.ok(ageMessages.length >= 9, "[Narration] expected independent age latches");
  assert.ok(
    !ageMessages.some((rule) => rule.includes("(set-goal bt-debug-last-age-event-goal")),
    "[Narration] age lifecycle messages must not share the legacy last-event latch",
  );
}

function validateStrategicNarration(sourceText, rules) {
  for (const symbol of [
    "bt-debug-verbosity-goal",
    "bt-debug-last-opening-goal",
    "bt-debug-last-threat-goal",
    "bt-debug-last-resource-mode-goal",
    "bt-debug-last-unit-goal",
    "bt-debug-last-strategy-goal",
    "bt-debug-last-castle-block-goal",
    "bt-debug-last-eco-event-goal",
    "bt-debug-last-tc-stage-goal",
  ]) {
    assert.ok(
      sourceText.includes(symbol),
      "[Narration] missing diagnostic state: " + symbol,
    );
  }

  assert.ok(
    sourceText.includes("(set-goal bt-debug-verbosity-goal 1)"),
    "[Narration] default verbosity gate is not initialized to level 1",
  );

  const rawRules = extractRawRules(sourceText);
  const chatRules = rawRules.filter((rule) =>
    rule.includes('(chat-local-to-self "BASILISK |'),
  );
  const MIN_STRATEGIC_NARRATION_RULES = 79;
  assert.ok(
    chatRules.length >= MIN_STRATEGIC_NARRATION_RULES,
    "[Narration] expected a complete strategic narration layer after diagnostic-state cleanup",
  );

  for (const rule of chatRules) {
    assert.ok(
      rule.includes("(up-compare-goal bt-debug-verbosity-goal"),
      "[Narration] every diagnostic chat action must be verbosity-gated",
    );
    const edgeTriggered =
      rule.includes("(up-compare-goal bt-debug-last-") ||
      (
        rule.includes('(chat-local-to-self "BASILISK | AGE |') &&
        /\(goal bt-debug-age-[A-Za-z0-9-]+ 0\)/.test(rule)
      );
    assert.ok(
      edgeTriggered,
      "[Narration] every diagnostic chat action must be edge-triggered by diagnostic state",
    );
    assert.ok(
      !/\(set-goal (?:strategy-goal|unit-goal|bt-opening-plan-goal|bt-resource-mode-goal)/.test(rule),
      "[Narration] diagnostic rule must never write strategic state",
    );
  }

  const requiredMessages = [
    "BASILISK | OPENING | ARABIA-FAST-CASTLE",
    "BASILISK | OPENING | ANTI-RUSH",
    "BASILISK | STRATEGY | FLUSH",
    "BASILISK | STRATEGY | RUSH",
    "BASILISK | STRATEGY | BOOM",
    "BASILISK | STRATEGY | CASTLE-POWER: pressure survives the age-up.",
    "BASILISK | THREAT | confirmed pressure.",
    "BASILISK | RESOURCE | CASTLE-BANK",
    "BASILISK | COMPOSITION | CROSSBOW",
    "BASILISK | AGE | Castle blocked: engine feasibility.",
    "BASILISK | AGE | Castle ready to research.",
    "BASILISK | AGE | Castle complete.",
    "BASILISK | ECO | Horse Collar: research started.",
    "BASILISK | ECO | Horse Collar: complete.",
    "BASILISK | ECO | Heavy Plow: complete.",
    "BASILISK | TC | TC2 complete.",
  ];
  for (const message of requiredMessages) {
    assert.ok(
      sourceText.includes(message),
      "[Narration] missing canonical diagnostic message: " + message,
    );
  }

  const categories = [
    "OPENING",
    "THREAT",
    "STRATEGY",
    "RESOURCE",
    "COMPOSITION",
    "AGE",
    "ECO",
    "TC",
  ];
  for (const category of categories) {
    assert.ok(
      chatRules.some((rule) =>
        rule.includes('BASILISK | ' + category + ' |'),
      ),
      "[Narration] missing diagnostic category: " + category,
    );
  }

  function maxRuleIndex(predicate, label) {
    const indexes = rules
      .map((rule, index) => (predicate(rule) ? index : -1))
      .filter((index) => index >= 0);
    assert.ok(indexes.length > 0, "[Narration] missing source-order anchor: " + label);
    return Math.max(...indexes);
  }

  function firstNarrator(message) {
    const index = rawRules.findIndex((rule) =>
      rule.includes('(chat-local-to-self "' + message),
    );
    assert.ok(index >= 0, "[Narration] missing narrator: " + message);
    return index;
  }

  const firstOpeningWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal bt-opening-plan-goal"),
    "opening writer",
  );
  assert.ok(
    firstNarrator("BASILISK | OPENING | ARABIA-STANDARD") > firstOpeningWriter,
    "[Narration] opening narration must observe finalized opening state",
  );

  const firstThreatWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal bt-opening-threat-goal"),
    "threat writer",
  );
  assert.ok(
    firstNarrator("BASILISK | THREAT | confirmed pressure.") > firstThreatWriter,
    "[Narration] threat narration must observe finalized threat state",
  );

  const strategyNarratorIndex = firstNarrator("BASILISK | STRATEGY | FLUSH");
  const strategySelectionWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(
      ({ rule, index }) =>
        index < strategyNarratorIndex &&
        rule.includes("(set-goal strategy-goal bt-strategy-"),
    );
  assert.ok(
    strategySelectionWriters.length > 0,
    "[Narration] primary strategy-selection writers are missing before strategy narration",
  );
  const lastStrategySelectionWriter = Math.max(
    ...strategySelectionWriters.map(({ index }) => index),
  );
  assert.ok(
    strategyNarratorIndex > lastStrategySelectionWriter,
    "[Narration] strategy narration must observe finalized strategy-selection state",
  );

  const firstResourceWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal bt-resource-mode-goal"),
    "resource-mode writer",
  );
  assert.ok(
    firstNarrator("BASILISK | RESOURCE | DARK") > firstResourceWriter,
    "[Narration] resource-mode narration must observe finalized resource arbitration",
  );

  const firstUnitWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal unit-goal"),
    "unit-goal writer",
  );
  assert.ok(
    firstNarrator("BASILISK | COMPOSITION | MIX") > firstUnitWriter,
    "[Narration] composition narration must observe finalized unit-goal selection",
  );

  const firstAgeWriter = maxRuleIndex(
    (rule) =>
      rule.includes("(research feudal-age)") ||
      rule.includes("(research castle-age)") ||
      rule.includes("(research imperial-age)"),
    "age research writer",
  );
  assert.ok(
    firstNarrator("BASILISK | AGE | Castle complete.") > firstAgeWriter,
    "[Narration] age narration must observe age-transition execution",
  );

  const firstEcoWriter = maxRuleIndex(
    (rule) =>
      rule.includes("(research ri-horse-collar)") ||
      rule.includes("(research ri-double-bit-axe)") ||
      rule.includes("(research ri-gold-mining)") ||
      rule.includes("(research ri-wheel-barrow)") ||
      rule.includes("(research ri-hand-cart)") ||
      rule.includes("(research ri-bow-saw)") ||
      rule.includes("(research ri-heavy-plow)"),
    "eco research writer",
  );
  assert.ok(
    firstNarrator("BASILISK | ECO | Heavy Plow: complete.") > firstEcoWriter,
    "[Narration] eco narration must observe eco-tech execution",
  );

  const firstTcWriter = maxRuleIndex(
    (rule) =>
      rule.includes("(set-goal bt-tc-stage-goal") ||
      rule.includes("(set-goal bt-tc-project-goal"),
    "TC project writer",
  );
  assert.ok(
    firstNarrator("BASILISK | TC | TC2 complete.") > firstTcWriter,
    "[Narration] TC narration must observe the completed project",
  );

  const firstCastleCommitmentWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal bt-castle-commitment-goal 1)"),
    "Castle commitment writer",
  );
  assert.ok(
    firstNarrator("BASILISK | AGE | Castle ready to research.") > firstCastleCommitmentWriter,
    "[Narration] Castle gate diagnostics must observe commitment arbitration",
  );

  for (const rule of chatRules) {
    const messageMatch = rule.match(/chat-local-to-self "BASILISK \| ([A-Z-]+)/);
    const category = messageMatch?.[1];
    const categorySignal = {
      OPENING: "(goal bt-opening-plan-goal",
      THREAT: "(goal bt-opening-threat-goal",
      STRATEGY: "(goal strategy-goal bt-strategy-",
      RESOURCE: "(goal bt-resource-mode-goal",
      COMPOSITION: "(goal unit-goal",
      ECO: "(goal ",
      TC: "(goal bt-tc-stage-goal",
      AGE: "(current-age",
    }[category];
    if (category && categorySignal && !rule.includes(categorySignal)) {
      const castleGateException =
        category === "AGE" &&
        rule.includes("(goal bt-castle-commitment-goal 1)");
      const tcCompletionException =
        category === "TC" &&
        rule.includes("(building-type-count town-center");
      const ecoException =
        category === "ECO" &&
        rule.includes("(up-research-status c:");
      const varangianCompositionException =
        category === "COMPOSITION" &&
        rule.includes("(goal bt-varangian-demand-goal 1)");
      assert.ok(
        castleGateException ||
          tcCompletionException ||
          ecoException ||
          varangianCompositionException,
        "[Narration] message does not match the state witness for category " + category,
      );
    }
  }

  assert.ok(
    !chatRules.some((rule) =>
      rule.includes("(true)") &&
      rule.includes("(chat-local-to-self"),
    ),
    "[Narration] unconditional diagnostic chat rule would spam every evaluation pass",
  );
}

function validateBlacksmithResearchLifecycle(rules) {
  const blacksmithTechs = [
    "ri-scale-mail",
    "ri-chain-mail",
    "ri-forging",
    "ri-iron-casting",
    "ri-plate-mail",
    "ri-fletching",
    "ri-bodkin-arrow",
    "ri-padded-archer-armor",
    "ri-leather-archer-armor",
    "ri-ring-archer-armor",
    "ri-bracer",
  ];

  const executors = [];
  for (const tech of blacksmithTechs) {
    for (const rule of rules) {
      if (rule.includes("(research " + tech + ")")) executors.push([tech, rule]);
    }
  }
  assert.ok(executors.length >= blacksmithTechs.length, "[Blacksmith] expected one or more executors per core technology");

  for (const [tech, rule] of executors) {
    assert.ok(
      !rule.includes("(can-research-with-escrow castle-age)"),
      "[Blacksmith] " + tech + " executor cannot use Castle feasibility as a discretionary-tech veto",
    );
    assert.ok(
      !rule.includes("(can-research-with-escrow imperial-age)"),
      "[Blacksmith] " + tech + " executor cannot use Imperial feasibility as a discretionary-tech veto",
    );
    assert.ok(
      rule.includes("(building-type-count blacksmith >= 1)"),
      "[Blacksmith] " + tech + " executor must witness Blacksmith capability",
    );
    assert.ok(
      rule.includes("(can-research-with-escrow " + tech + ")"),
      "[Blacksmith] " + tech + " executor must remain engine-feasibility gated",
    );
  }

  const rangedWitness = rules.find(
    (rule) =>
      rule.includes("(set-goal bt-blacksmith-ranged-army-goal 1)") &&
      rule.includes("(unit-type-count-total archer-line >= 3)") &&
      rule.includes("(unit-type-count-total skirmisher-line >= 3)"),
  );
  assert.ok(
    rangedWitness,
    "[Blacksmith] friendly ranged composition witness is missing",
  );

  const infantryWitness = rules.find(
    (rule) =>
      rule.includes("(set-goal bt-blacksmith-infantry-army-goal 1)") &&
      rule.includes("(unit-type-count-total spearman-line >= 3)") &&
      rule.includes("(unit-type-count-total militiaman-line >= 3)"),
  );
  assert.ok(
    infantryWitness,
    "[Blacksmith] friendly infantry composition witness is missing",
  );

  requireRule(
    rules,
    "Blacksmith Fletching package",
    "(goal bt-research-ranged-counter-package-goal 0)",
    "(goal bt-blacksmith-ranged-army-goal 1)",
    "(set-goal bt-research-ranged-counter-package-goal ri-fletching)",
  );
  requireRule(
    rules,
    "Blacksmith Scale Mail package",
    "(goal bt-research-cavalry-counter-package-goal 0)",
    "(up-compare-goal bt-standing-spear-target-goal >= bt-spear-target-1)",
    "(unit-type-count-total spearman-line >= bt-spear-target-1)",
    "(set-goal bt-research-cavalry-counter-package-goal ri-scale-mail)",
  );
  const scalePackage = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-cavalry-counter-package-goal 0)") &&
      rule.includes("(set-goal bt-research-cavalry-counter-package-goal ri-scale-mail)"),
  );
  assert.ok(scalePackage, "[Blacksmith] Scale Mail package writer is missing");
  assert.ok(
    !scalePackage.includes("(goal bt-blacksmith-infantry-army-goal 1)"),
    "[Blacksmith] Scale Mail package writer must share the Spear feasibility witness",
  );
  const scaleExecutors = rules.filter((rule) =>
    rule.includes("(research ri-scale-mail)"),
  );
  assert.ok(
    scaleExecutors.length > 0,
    "[Blacksmith] Scale Mail research executor is missing",
  );
  for (const rule of scaleExecutors) {
    assert.ok(
      rule.includes("(up-compare-goal bt-standing-spear-target-goal >=") &&
        rule.includes("(unit-type-count-total spearman-line >="),
      "[Blacksmith] every Scale Mail executor must share the Spear feasibility witness",
    );
  }

  const feudalFletching = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(research ri-fletching)") &&
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-fletching)") &&
      rule.includes("(unit-type-count-total cavalry-archer-line >= 3)"),
  );
  assert.ok(
    feudalFletching,
    "[Blacksmith] Feudal Fletching executor must support Cavalry Archers",
  );

  const caFletchingToBodkin = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-fletching)") &&
      rule.includes("(up-research-status c: ri-fletching == research-complete)") &&
      rule.includes("(current-age >= castle-age)") &&
      rule.includes("(unit-type-count-total cavalry-archer-line >= 3)") &&
      rule.includes("(up-research-status c: ri-bodkin-arrow < research-complete)") &&
      rule.includes("(set-goal bt-research-ranged-counter-package-goal ri-bodkin-arrow)"),
  );
  assert.ok(
    caFletchingToBodkin,
    "[Blacksmith] CA Fletching -> Bodkin progression is missing",
  );

  const fletchingTerminal = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-fletching)") &&
      rule.includes("(up-research-status c: ri-fletching == research-complete)") &&
      rule.includes("(up-research-status c: ri-bodkin-arrow == research-complete)") &&
      rule.includes("(set-goal bt-research-ranged-counter-package-goal 0)"),
  );
  assert.ok(
    fletchingTerminal,
    "[Blacksmith] Fletching terminal package release is missing",
  );

  const caBodkinExecutor = rules.find(
    (rule) =>
      rule.includes("(research ri-bodkin-arrow)") &&
      rule.includes("(current-age >= castle-age)") &&
      rule.includes("(unit-type-count-total cavalry-archer-line >= 3)") &&
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-bodkin-arrow)") &&
      rule.includes("(can-research-with-escrow ri-bodkin-arrow)"),
  );
  assert.ok(
    caBodkinExecutor,
    "[Blacksmith] CA Bodkin executor is missing",
  );

  const rangedCancellation = rules.find(
    (rule) =>
      rule.includes("(goal bt-ranged-threat-goal 0)") &&
      rule.includes("(goal bt-blacksmith-ranged-army-goal 0)") &&
      rule.includes("(set-goal bt-research-ranged-counter-package-goal 0)"),
  );
  assert.ok(
    rangedCancellation,
    "[Blacksmith] ranged package must survive threat loss while friendly ranged mass remains",
  );

  const infantryCancellation = rules.find(
    (rule) =>
      rule.includes("(goal bt-cavalry-threat-goal 0)") &&
      rule.includes("(goal bt-blacksmith-infantry-army-goal 0)") &&
      rule.includes("(set-goal bt-research-cavalry-counter-package-goal 0)"),
  );
  assert.ok(
    infantryCancellation,
    "[Blacksmith] melee package must survive cavalry-threat loss while friendly infantry mass remains",
  );

  requireRule(
    rules,
    "Scale -> Feudal Forging",
    "(goal bt-research-cavalry-counter-package-goal ri-scale-mail)",
    "(current-age == feudal-age)",
    "(goal bt-blacksmith-infantry-army-goal 1)",
    "(set-goal bt-research-cavalry-counter-package-goal ri-forging)",
  );
  requireRule(
    rules,
    "Scale -> Castle Chain Mail",
    "(goal bt-research-cavalry-counter-package-goal ri-scale-mail)",
    "(current-age >= castle-age)",
    "(set-goal bt-research-cavalry-counter-package-goal ri-chain-mail)",
  );
  requireRule(
    rules,
    "Chain -> Iron Casting",
    "(goal bt-research-cavalry-counter-package-goal ri-chain-mail)",
    "(goal bt-blacksmith-infantry-army-goal 1)",
    "(up-compare-goal bt-cavalry-counter-level-goal < 1)",
    "(set-goal bt-research-cavalry-counter-package-goal ri-iron-casting)",
  );

  const pikeTerminal = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-cavalry-counter-package-goal ri-pikeman)") &&
      rule.includes("(up-research-status c: ri-pikeman == research-complete)") &&
      rule.includes("(goal bt-halberdier-demand-goal 0)") &&
      rule.includes("(set-goal bt-research-cavalry-counter-package-goal 0)"),
  );
  assert.ok(
    pikeTerminal,
    "[Blacksmith] completed Pike package must release when Halberdier demand is absent",
  );

  const halberdierTerminal = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-cavalry-counter-package-goal ri-halberdier)") &&
      rule.includes("(up-research-status c: ri-halberdier == research-complete)") &&
      rule.includes("(set-goal bt-research-cavalry-counter-package-goal 0)"),
  );
  assert.ok(
    halberdierTerminal,
    "[Blacksmith] completed Halberdier package must release when no Plate continuation fires",
  );
}
 
function validateEliteVarangianResearchCapability(rules) {
  const executor = rules.find(
    (rule) =>
      rule.includes("(research ri-elite-varangian-guard)") &&
      rule.includes("(goal bt-research-cataphract-package-goal ri-elite-varangian-guard)"),
  );
  assert.ok(
    executor,
    "[Elite Varangian] shared premium research executor is missing",
  );
  assert.ok(
    executor.includes("(building-type-count-total barracks >= 1)"),
    "[Elite Varangian] Imperial upgrade must use a Barracks capability witness",
  );
  assert.ok(
    executor.includes("(goal bt-research-barracks-claim-goal 0)"),
    "[Elite Varangian] research must use the Barracks claim",
  );
  assert.ok(
    executor.includes("(up-compare-goal bt-research-barracks-failure-backoff-goal != ri-elite-varangian-guard)"),
    "[Elite Varangian] research must use Barracks-local failure backoff",
  );
  assert.ok(
    executor.includes("(can-research-with-escrow ri-elite-varangian-guard)"),
    "[Elite Varangian] research must remain escrow-feasibility gated",
  );

  const eliteTargetWriter = rules.find(
    (rule) =>
      rule.includes("(current-age >= imperial-age)") &&
      rule.includes("(up-compare-goal bt-ranged-counter-level-goal < 2)") &&
      rule.includes("(players-unit-type-count any-enemy militiaman-line < bt-cataphract-enemy-threshold-2)") &&
      rule.includes("(goal bt-cataphract-demand-goal 0)") &&
      rule.includes("(up-research-status c: ri-logistica == research-complete)") &&
      rule.includes("(set-goal bt-varangian-target-goal bt-varangian-elite-target-level)"),
  );
  assert.ok(
    eliteTargetWriter,
    "[Elite Varangian] 12-Guard target writer is missing or disconnected from the elite gate",
  );

  const eliteProducer = rules.find(
    (rule) =>
      rule.includes("(train elite-varangian-guard)") &&
      rule.includes("(can-train-with-escrow elite-varangian-guard)") &&
      rule.includes("(up-research-status c: ri-elite-varangian-guard == research-complete)"),
  );
  assert.ok(
    eliteProducer,
    "[Elite Varangian] production must require the completed Elite research state",
  );

  const regularProducer = rules.find(
    (rule) =>
      rule.includes("(train varangian-guard)") &&
      rule.includes("(can-train-with-escrow varangian-guard)") &&
      rule.includes("(up-research-status c: ri-elite-varangian-guard < research-pending)"),
  );
  assert.ok(
    regularProducer,
    "[Elite Varangian] regular production must stop once Elite research is pending",
  );

  const completion = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-barracks-claim-goal ri-elite-varangian-guard)") &&
      rule.includes("(up-research-status c: ri-elite-varangian-guard == research-complete)") &&
      rule.includes("(set-goal bt-research-barracks-claim-goal 0)"),
  );
  assert.ok(
    completion,
    "[Elite Varangian] Barracks research claim completion reset is missing",
  );

  const watchdog = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-barracks-claim-goal ri-elite-varangian-guard)") &&
      rule.includes("(up-research-status c: ri-elite-varangian-guard <= research-available)") &&
      rule.includes("(set-goal bt-research-barracks-failure-backoff-goal ri-elite-varangian-guard)"),
  );
  assert.ok(
    watchdog,
    "[Elite Varangian] Barracks research watchdog is missing",
  );
}


function validateBarracksSquiresArsonLifecycle(rules) {
  const lifecycles = [
    ["Squires", "ri-squires"],
    ["Arson", "ri-arson"],
  ];

  for (const [label, tech] of lifecycles) {
    const executor = rules.find(
      (rule) =>
        rule.includes("(research " + tech + ")") &&
        rule.includes("(building-type-count barracks >= 1)") &&
        rule.includes("(goal bt-research-barracks-claim-goal 0)") &&
        rule.includes("(can-research-with-escrow " + tech + ")"),
    );
    assert.ok(
      executor,
      "[" + label + "] Barracks research executor is missing or does not use the shared claim/escrow contract",
    );
    assert.ok(
      executor.includes(
        "(up-compare-goal bt-research-barracks-failure-backoff-goal != " + tech + ")",
      ),
      "[" + label + "] executor is missing Barracks-local failure backoff",
    );

    const completion = rules.find(
      (rule) =>
        rule.includes(
          "(goal bt-research-barracks-claim-goal " + tech + ")",
        ) &&
        rule.includes(
          "(up-research-status c: " + tech + " == research-complete)",
        ) &&
        rule.includes("(set-goal bt-research-barracks-claim-goal 0)"),
    );
    assert.ok(
      completion,
      "[" + label + "] Barracks claim completion release is missing",
    );

    const watchdog = rules.find(
      (rule) =>
        rule.includes(
          "(goal bt-research-barracks-claim-goal " + tech + ")",
        ) &&
        rule.includes(
          "(up-research-status c: " + tech + " <= research-available)",
        ) &&
        rule.includes(
          "(set-goal bt-research-barracks-failure-backoff-goal " + tech + ")",
        ) &&
        rule.includes(
          "(enable-timer bt-research-barracks-failure-backoff-timer bt-research-failure-backoff-seconds)",
        ) &&
        rule.includes("(set-goal bt-research-barracks-claim-goal 0)"),
    );
    assert.ok(
      watchdog,
      "[" + label + "] failed research must arm Barracks backoff and release the shared claim",
    );
  }
}

function validatePikemanLifecycle(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");
  const executor = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-cavalry-counter-package-goal ri-pikeman)") &&
      rule.includes("(research ri-pikeman)") &&
      rule.includes("(can-research-with-escrow ri-pikeman)") &&
      rule.includes("(set-goal bt-research-barracks-claim-goal ri-pikeman)"),
  );
  assert.ok(executor, "[Pikeman] research executor is missing");
  const text = normalize(executor);
  assert.ok(
    text.includes("(up-compare-goal bt-cavalry-counter-level-goal >= 1)") &&
      text.includes("(up-compare-goal bt-standing-spear-target-goal >= bt-spear-target-2)") &&
      text.includes("(unit-type-count-total spearman-line >= bt-spear-target-2)"),
    "[Pikeman] action boundary must re-check the package capability witness",
  );
  const completion = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-barracks-claim-goal ri-pikeman)") &&
      rule.includes("(up-research-status c: ri-pikeman == research-complete)") &&
      rule.includes("(set-goal bt-research-barracks-claim-goal 0)"),
  );
  assert.ok(completion, "[Pikeman] research claim completion reset is missing");
  const watchdog = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-barracks-claim-goal ri-pikeman)") &&
      rule.includes("(up-research-status c: ri-pikeman <= research-available)") &&
      rule.includes("(set-goal bt-research-barracks-failure-backoff-goal ri-pikeman)"),
  );
  assert.ok(watchdog, "[Pikeman] Barracks research watchdog is missing");
}

function validateRangedCounterLifecycle(rules) {
  const normalize = (rule) => rule.replace(/\\s+/g, " ");

  const crossbow = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-crossbow)") &&
      rule.includes("(research ri-crossbow)") &&
      rule.includes("(can-research-with-escrow ri-crossbow)") &&
      rule.includes("(set-goal bt-research-archery-range-claim-goal ri-crossbow)"),
  );
  assert.ok(crossbow, "[Ranged] Crossbow research executor is missing");
  const crossbowText = normalize(crossbow);
  assert.ok(
    crossbowText.includes("(goal bt-crossbow-demand-goal 1)") &&
      crossbowText.includes("(goal bt-arbalest-demand-goal 0)") &&
      crossbowText.includes("(up-compare-goal bt-standing-crossbow-target-goal > 0)"),
    "[Ranged] Crossbow action boundary must re-check its live role demand",
  );

  const ringExecutors = rules.filter(
    (rule) =>
      rule.includes("(goal bt-research-ranged-counter-package-goal ri-ring-archer-armor)") &&
      rule.includes("(research ri-ring-archer-armor)") &&
      rule.includes("(can-research-with-escrow ri-ring-archer-armor)") &&
      rule.includes("(set-goal bt-research-blacksmith-claim-goal ri-ring-archer-armor)"),
  );
  assert.equal(
    ringExecutors.length,
    2,
    "[Ranged] Ring Mail must retain two composition-specific research executors",
  );

  const ringCrossbow = ringExecutors.find((rule) =>
    rule.includes("(goal unit-goal crossbowman)"),
  );
  const ringAlt = ringExecutors.find((rule) =>
    rule.includes("(goal bt-standing-skirm-target-goal >= bt-skirm-target-2)") ||
    rule.includes("(unit-type-count-total cavalry-archer >= 6)"),
  );
  assert.ok(
    ringCrossbow,
    "[Ranged] Ring Mail Crossbow branch is missing",
  );
  assert.ok(
    ringAlt,
    "[Ranged] Ring Mail Skirmisher/Cavalry-Archer branch is missing",
  );

  const ringCrossbowText = normalize(ringCrossbow);
  assert.ok(
    ringCrossbowText.includes("(unit-type-count-total arbalest >= bt-crossbow-target-mature)"),
    "[Ranged] Ring Mail Crossbow action boundary must re-check a live mature ranged army witness",
  );

  const ringAltText = normalize(ringAlt);
  assert.ok(
    (
      ringAltText.includes("(up-compare-goal bt-standing-skirm-target-goal >= bt-skirm-target-2)") &&
      ringAltText.includes("(unit-type-count-total skirmisher-line >= bt-skirm-target-2)")
    ) ||
      ringAltText.includes("(unit-type-count-total cavalry-archer >= 6)"),
    "[Ranged] Ring Mail alternate action boundary must re-check a live mature ranged army witness",
  );

  for (const tech of ["ri-crossbow", "ri-ring-archer-armor"]) {
    const claimGoal =
      tech === "ri-crossbow"
        ? "bt-research-archery-range-claim-goal"
        : "bt-research-blacksmith-claim-goal";
    const backoffGoal =
      tech === "ri-crossbow"
        ? "bt-research-archery-range-failure-backoff-goal"
        : "bt-research-blacksmith-failure-backoff-goal";
    const completion = rules.find(
      (rule) =>
        rule.includes(`(goal ${claimGoal} ${tech})`) &&
        rule.includes(`(up-research-status c: ${tech} == research-complete)`) &&
        rule.includes(`(set-goal ${claimGoal} 0)`),
    );
    assert.ok(completion, `[Ranged] ${tech} claim completion reset is missing`);
    const watchdog = rules.find(
      (rule) =>
        rule.includes(`(goal ${claimGoal} ${tech})`) &&
        rule.includes(`(up-research-status c: ${tech} <= research-available)`) &&
        rule.includes(`(set-goal ${backoffGoal} ${tech})`),
    );
    assert.ok(watchdog, `[Ranged] ${tech} failure watchdog is missing`);
  }
}

function validateCataphractResearchLifecycle(rules) {
  const findResearch = (tech) =>
    rules.find(
      (rule) =>
        rule.includes("(research " + tech + ")") &&
        rule.includes("(goal bt-research-cataphract-package-goal " + tech + ")") &&
        rule.includes("(can-research-with-escrow " + tech + ")") &&
        rule.includes("(goal bt-research-castle-claim-goal 0)"),
    );

  const logistica = findResearch("ri-logistica");
  assert.ok(logistica, "[Cataphract] Logistica research executor is missing");
  assert.ok(
    logistica.includes("(goal bt-cataphract-demand-goal 1)") ||
      logistica.includes("(goal bt-varangian-demand-goal 1)"),
    "[Cataphract] Logistica action boundary must retain a live premium-demand witness",
  );
  assert.ok(
    logistica.includes("(players-unit-type-count any-enemy militiaman-line >= bt-cataphract-enemy-threshold-2)") &&
      logistica.includes("(unit-type-count cataphract-line >= bt-cataphract-target-1)"),
    "[Cataphract] Logistica action boundary must re-check the tier-2 capability witness",
  );

  const elite = findResearch("ri-elite-cataphract");
  assert.ok(elite, "[Cataphract] Elite Cataphract research executor is missing");
  assert.ok(
    elite.includes("(goal bt-cataphract-demand-goal 1)") &&
      elite.includes("(players-unit-type-count any-enemy militiaman-line >= bt-cataphract-enemy-threshold-3)") &&
      elite.includes("(unit-type-count cataphract-line >= bt-cataphract-target-2)") &&
      elite.includes("(up-research-status c: ri-logistica == research-complete)"),
    "[Cataphract] Elite action boundary must re-check the live tier-3 witness",
  );

  for (const tech of ["ri-logistica", "ri-elite-cataphract"]) {
    const completion = rules.find(
      (rule) =>
        rule.includes("(goal bt-research-castle-claim-goal " + tech + ")") &&
        rule.includes("(up-research-status c: " + tech + " == research-complete)") &&
        rule.includes("(set-goal bt-research-castle-claim-goal 0)"),
    );
    assert.ok(completion, "[Cataphract] " + tech + " Castle claim completion reset is missing");

    const watchdog = rules.find(
      (rule) =>
        rule.includes("(goal bt-research-castle-claim-goal " + tech + ")") &&
        rule.includes("(up-research-status c: " + tech + " <= research-available)") &&
        rule.includes("(set-goal bt-research-castle-failure-backoff-goal " + tech + ")") &&
        rule.includes("(enable-timer bt-research-castle-failure-backoff-timer bt-research-failure-backoff-seconds)") &&
        rule.includes("(set-goal bt-research-castle-claim-goal 0)"),
    );
    assert.ok(watchdog, "[Cataphract] " + tech + " Castle failure watchdog is missing");
  }

  for (const tech of ["ri-logistica", "ri-elite-cataphract"]) {
    const lossRecovery = rules.find(
      (rule) =>
        rule.includes("(goal bt-research-castle-claim-goal " + tech + ")") &&
        rule.includes("(building-type-count castle == 0)") &&
        rule.includes("(up-research-status c: " + tech + " <= research-available)") &&
        rule.includes("(set-goal bt-research-castle-failure-backoff-goal " + tech + ")") &&
        rule.includes("(set-goal bt-research-castle-claim-goal 0)"),
    );
    assert.ok(
      lossRecovery,
      "[Cataphract] " + tech + " Castle-loss path must record backoff before releasing the claim",
    );
  }

  const release = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-cataphract-package-goal ri-logistica)") &&
      rule.includes("(up-research-status c: ri-logistica == research-complete)") &&
      rule.includes("(players-unit-type-count any-enemy militiaman-line < bt-cataphract-enemy-threshold-3)") &&
      rule.includes("(set-goal bt-research-cataphract-package-goal 0)"),
  );
  assert.ok(
    release,
    "[Cataphract] completed Logistica cursor must release when Elite tier is not live",
  );
}

function validateCastleStoneLifecycle(rules) {
  const stoneModeRelease = rules.find(
    (rule) =>
      rule.includes("(goal bt-resource-mode-goal bt-resource-mode-castle-stone)") &&
      rule.includes("(goal bt-resource-mode-goal bt-resource-mode-castle-stone-premium)") &&
      rule.includes("(stone-amount >= 650)") &&
      rule.includes("(building-type-count-total castle >= 1)") &&
      rule.includes("(goal bt-castle-cataphract-demand-goal 0)") &&
      rule.includes("(set-goal bt-resource-mode-goal 0)"),
  );
  assert.ok(
    stoneModeRelease,
    "[Castle Stone] stone allocation must have a terminal release witness",
  );

  const stoneModeDemand = rules.find(
    (rule) =>
      rule.includes("(goal bt-resource-mode-goal 0)") &&
      rule.includes("(current-age >= castle-age)") &&
      rule.includes("(building-type-count-total castle < 1)") &&
      rule.includes("(stone-amount < 650)") &&
      rule.includes("(goal bt-castle-cataphract-demand-goal 1)") &&
      rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-castle-stone)"),
  );
  assert.ok(
    stoneModeDemand,
    "[Castle Stone] stone mode must be driven by a live Castle demand and 650-stone deficit",
  );
}

function validateBoomEconomicLifecycle(rules, sourceText) {
  for (const [symbol, value] of [
    ["bt-castle-boom-army-floor-tc1", "4"],
    ["bt-castle-boom-army-floor-tc2", "6"],
    ["bt-castle-boom-army-floor-tc3", "8"],
  ]) {
    assert.ok(
      sourceText.includes("(defconst " + symbol + " " + value + ")"),
      "[BOOM] missing canonical " + symbol + "=" + value,
    );
  }

  const boomFloors = [
    {
      label: "TC1",
      facts: [
        "(current-age == castle-age)",
        "(goal strategy-goal bt-strategy-boom)",
        "(building-type-count town-center < 2)",
      ],
      value: "bt-castle-boom-army-floor-tc1",
    },
    {
      label: "TC2",
      facts: [
        "(current-age == castle-age)",
        "(goal strategy-goal bt-strategy-boom)",
        "(building-type-count town-center >= 2)",
        "(building-type-count town-center < 3)",
      ],
      value: "bt-castle-boom-army-floor-tc2",
    },
    {
      label: "TC3",
      facts: [
        "(current-age == castle-age)",
        "(goal strategy-goal bt-strategy-boom)",
        "(building-type-count town-center >= 3)",
      ],
      value: "bt-castle-boom-army-floor-tc3",
    },
  ];

  for (const entry of boomFloors) {
    const matches = rules.filter(
      (rule) =>
        entry.facts.every((fact) => rule.includes(fact)) &&
        rule.includes(
          "(set-goal bt-standing-army-floor-goal " + entry.value + ")",
        ),
    );
    assert.equal(
      matches.length,
      1,
      "[BOOM] " + entry.label + " standing-floor writer must exist exactly once",
    );
  }

  for (const value of ["12", "16", "20"]) {
    assert.equal(
      rules.filter(
        (rule) =>
          rule.includes("(current-age == castle-age)") &&
          rule.includes("(goal strategy-goal bt-strategy-boom)") &&
          rule.includes(
            "(set-goal bt-standing-army-floor-goal " + value + ")",
          ),
      ).length,
      0,
      "[BOOM] Castle BOOM must not use pressure floor " + value,
    );

    assert.ok(
      rules.some(
        (rule) =>
          rule.includes("(current-age == castle-age)") &&
          rule.includes("(goal strategy-goal bt-strategy-castle-power)") &&
          rule.includes(
            "(set-goal bt-standing-army-floor-goal " + value + ")",
          ),
      ),
      "[BOOM] Castle-Power must retain Castle pressure floor " + value,
    );
  }

  const standingTrainRules = rules.filter(
    (rule) =>
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(can-train ") &&
      rule.includes("(goal bt-castle-commitment-goal 0)"),
  );
  assert.equal(
    standingTrainRules.length,
    0,
    "[BOOM] standing-role train rules must use the FLUSH-aware Castle-bank gate",
  );

  const flushAwareStandingTrainRules = rules.filter(
    (rule) =>
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(can-train ") &&
      rule.includes("(goal strategy-goal bt-strategy-flush)") &&
      rule.includes("(goal bt-castle-commitment-goal 0)"),
  );
  assert.equal(
    flushAwareStandingTrainRules.length,
    3,
    "[BOOM] expected Spear/Skirm/Archer standing train rules to carry the FLUSH bank override",
  );

  const tcArbitration = rules.find(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-boom)") &&
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(goal bt-tc-project-goal 2)") &&
      rule.includes("(goal bt-tc-project-goal 3)") &&
      rule.includes("(goal bt-tc-stage-goal bt-tc-stage-demanded)") &&
      rule.includes("(goal bt-tc-stage-goal bt-tc-stage-resource-claimed)") &&
      rule.includes("(goal bt-tc-stage-goal bt-tc-stage-placement-pending)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 0)"),
  );
  assert.ok(
    tcArbitration,
    "[BOOM] active TC2/TC3 project must suppress discretionary standing demand",
  );

  const knightSelector = rules.find(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-boom)") &&
      rule.includes("(set-goal unit-goal knight-line)") &&
      rule.includes("(unit-type-count-total archer-line < 4)"),
  );
  assert.ok(
    knightSelector?.includes("(building-type-count town-center >= 2)"),
    "[BOOM] generic Knight selection must wait for TC2",
  );

  const knightWriter = rules.find(
    (rule) =>
      rule.includes("(goal bt-knight-demand-goal 0)") &&
      rule.includes("(set-goal bt-knight-demand-goal 1)"),
  );
  assert.ok(
    knightWriter &&
      knightWriter.includes("(goal bt-tc-project-goal 2)") &&
      knightWriter.includes("(goal bt-tc-project-goal 3)"),
    "[BOOM] Knight demand writer must yield during an active TC project",
  );

  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-knight-demand-goal 1)") &&
        rule.includes("(set-goal bt-knight-demand-goal 0)") &&
        rule.includes("(goal bt-tc-project-goal 2)") &&
        rule.includes("(goal bt-tc-project-goal 3)"),
    ),
    "[BOOM] active Knight demand must cancel when BOOM TC2/TC3 project begins",
  );

  const crossbowWriter = rules.find(
    (rule) =>
      rule.includes("(goal bt-crossbow-demand-goal 0)") &&
      rule.includes("(set-goal bt-crossbow-demand-goal 1)"),
  );
  assert.ok(
    crossbowWriter &&
      crossbowWriter.includes("(goal strategy-goal bt-strategy-castle-power)") &&
      crossbowWriter.includes("(goal bt-tc-project-goal 0)"),
    "[BOOM] Crossbow demand writer must yield during a BOOM TC project while preserving Castle-Power",
  );

  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-crossbow-demand-goal 1)") &&
        rule.includes("(set-goal bt-crossbow-demand-goal 0)") &&
        rule.includes("(goal bt-tc-project-goal 2)") &&
        rule.includes("(goal bt-tc-project-goal 3)"),
    ),
    "[BOOM] active Crossbow demand must cancel when BOOM TC2/TC3 project begins",
  );

  for (const unit of ["knight-line", "crossbowman"]) {
    const demand = unit === "knight-line" ? "bt-knight-demand-goal" : "bt-crossbow-demand-goal";
    const trainRule = rules.find(
      (rule) =>
        rule.includes("(train " + unit + ")") &&
        rule.includes("(goal " + demand + " 1)") &&
        rule.includes("(goal bt-resource-mode-goal bt-resource-mode-castle-boom)"),
    );
    assert.ok(
      trainRule &&
        trainRule.includes("(goal strategy-goal bt-strategy-castle-power)") &&
        trainRule.includes("(goal bt-tc-project-goal 0)"),
      "[BOOM] " + unit + " train boundary must yield during an active BOOM TC project",
    );
  }

  const capabilityRules = rules.filter(
    (rule) =>
      /\(build (?:barracks|archery-range|stable)\)/.test(rule) &&
      /bt-standing-(?:army-demand|spear-target|skirm-target|archer-target|knight-target|crossbow-target|camel-target)-goal/.test(rule) &&
      !rule.includes("(goal bt-scout-pressure-demand-goal 1)") &&
      !(
        rule.includes("(goal strategy-goal bt-strategy-flush)") &&
        !rule.includes("(goal bt-castle-commitment-goal 0)")
      ),
  );
  assert.equal(
    capabilityRules.length,
    18,
    "[BOOM] expected the complete 18-rule standing capability family",
  );
  assert.ok(
    capabilityRules.every(
      (rule) =>
        rule.includes("(goal bt-castle-commitment-goal 0)") &&
        rule.includes("(goal strategy-goal bt-strategy-flush)"),
    ),
    "[BOOM] every standing military capability rule must carry the FLUSH-aware Castle-bank gate",
  );

  const stableCapabilityRules = capabilityRules.filter((rule) =>
    rule.includes("(build stable)"),
  );
  assert.equal(
    stableCapabilityRules.length,
    3,
    "[BOOM] expected three Castle Stable capability rules",
  );
  assert.ok(
    stableCapabilityRules.every(
      (rule) =>
        rule.includes("(goal bt-tc-project-goal 2)") &&
        rule.includes("(goal bt-tc-project-goal 3)"),
    ),
    "[BOOM] Stable capability must yield during an active BOOM TC project",
  );

  const tcArbitrationIndex = rules.indexOf(tcArbitration);
  const militarySectionFirstTrainIndex = rules.findIndex(
    (rule) =>
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(train spearman-line)"),
  );
  assert.ok(
    tcArbitrationIndex > -1 &&
      militarySectionFirstTrainIndex > -1 &&
      tcArbitrationIndex < militarySectionFirstTrainIndex,
    "[BOOM] capital arbitration must precede military production",
  );

  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-tc-project-goal 0)") &&
        rule.includes("(set-goal bt-tc-project-goal 2)"),
    ),
    "[BOOM] TC2 project demand writer is missing",
  );
  const tcDemandWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(
      ({ rule }) =>
        rule.includes("(current-age >= castle-age)") &&
        rule.includes("(goal bt-tc-project-goal 0)") &&
        (rule.includes("(set-goal bt-tc-project-goal 2)") ||
          rule.includes("(set-goal bt-tc-project-goal 3)")),
    );
  assert.equal(
    tcDemandWriters.length,
    2,
    "[BOOM source order] TC2/TC3 demand writers must remain exactly two",
  );

  const tcClaimWriters = rules
    .map((rule, index) => ({ rule, index }))
    .filter(
      ({ rule }) =>
        rule.includes("(goal bt-tc-stage-goal bt-tc-stage-demanded)") &&
        rule.includes("(strategic-number sn-resource-control == 0)") &&
        rule.includes("(can-build-with-escrow town-center)") &&
        (rule.includes(
          "(set-strategic-number sn-resource-control bt-tc2-claim)",
        ) ||
          rule.includes(
            "(set-strategic-number sn-resource-control bt-tc3-claim)",
          )),
    );
  assert.equal(
    tcClaimWriters.length,
    2,
    "[BOOM source order] TC2/TC3 resource-claim providers must remain exactly two",
  );

  const tcPreemptionBegins = rules
    .map((rule, index) => ({ rule, index }))
    .filter(
      ({ rule }) =>
        rule.includes("(town-under-attack)") &&
        (rule.includes(
          "(set-goal bt-preempt-original-owner-goal bt-tc2-claim)",
        ) ||
          rule.includes(
            "(set-goal bt-preempt-original-owner-goal bt-tc3-claim)",
          )) &&
        rule.includes(
          "(set-strategic-number sn-resource-control bt-preempt-emergency-claim)",
        ),
    );
  assert.equal(
    tcPreemptionBegins.length,
    2,
    "[BOOM source order] TC2/TC3 preemption openers must remain exactly two",
  );

  const firstCapacityConsumer = rules.findIndex(
    (rule) =>
      /\\(build (?:barracks|archery-range|stable)\\)/.test(rule) &&
      rule.includes("(goal bt-tc-project-goal 2)") &&
      rule.includes("(goal bt-tc-project-goal 3)"),
  );
  assert.ok(
    firstCapacityConsumer >= 0,
    "[BOOM source order] no TC-aware production-capability consumer found",
  );

  const firstMilitaryArbitrationConsumer = rules.findIndex(
    (rule) =>
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(train spearman-line)"),
  );
  assert.ok(
    firstMilitaryArbitrationConsumer >= 0,
    "[BOOM source order] no standing-army military executor found",
  );

  const lastResourceModeWriter = maxRuleIndex(
    (rule) => rule.includes("(set-goal bt-resource-mode-goal "),
    "resource-mode writer",
  );

  const firstTcDemandWriter = Math.min(...tcDemandWriters.map(({ index }) => index));
  const lastTcDemandWriter = Math.max(...tcDemandWriters.map(({ index }) => index));
  const firstTcClaimWriter = Math.min(...tcClaimWriters.map(({ index }) => index));
  const lastTcClaimWriter = Math.max(...tcClaimWriters.map(({ index }) => index));
  const firstPreemptionBegin = Math.min(
    ...tcPreemptionBegins.map(({ index }) => index),
  );
  const lastPreemptionBegin = Math.max(
    ...tcPreemptionBegins.map(({ index }) => index),
  );

  assert.ok(
    lastResourceModeWriter < firstTcDemandWriter,
    "[BOOM source order] TC demand must observe completed resource-mode arbitration",
  );
  assert.ok(
    lastTcDemandWriter < firstTcClaimWriter,
    "[BOOM source order] TC resource claims must follow persistent TC demand",
  );
  assert.ok(
    lastTcClaimWriter < firstPreemptionBegin,
    "[BOOM source order] TC preemption must be able to see a claim created in the same pass",
  );
  assert.ok(
    lastPreemptionBegin < firstCapacityConsumer,
    "[BOOM source order] TC preemption must run before TC-aware production capability",
  );
  assert.ok(
    firstCapacityConsumer < tcArbitrationIndex,
    "[BOOM source order] TC-aware production capability must run before standing-demand arbitration",
  );
  assert.ok(
    tcArbitrationIndex < firstMilitaryArbitrationConsumer,
    "[BOOM source order] capital arbitration must run before standing military production",
  );

  for (const deadState of [
    "bt-debug-last-age-event-goal",
    "bt-debug-last-tc-project-goal",
  ]) {
    assert.equal(
      sourceText.includes(deadState),
      false,
      "[State hygiene] dead debug state must not return: " + deadState,
    );
  }

}


function validateBoomTcMilitaryExceptions(rules, sourceText) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");

  const tcGate = [
    "(goal bt-tc-project-goal 0)",
  ];

  const reactiveExecutors = [
    {
      label: "Monk",
      action: "(train monk)",
      demand: "(goal bt-monk-demand-goal 1)",
      witness: "(building-type-count monastery >= 1)",
    },
    {
      label: "Mangonel",
      action: "(train mangonel-line)",
      demand: "(goal bt-mangonel-demand-goal 1)",
      witness: "(building-type-count siege-workshop >= 1)",
    },
    {
      label: "Scorpion",
      action: "(train scorpion-line)",
      demand: "(goal bt-scorpion-demand-goal 1)",
      witness: "(players-unit-type-count target-player militiaman-line >= bt-scorpion-trigger-infantry)",
    },
  ];

  for (const entry of reactiveExecutors) {
    const executor = rules.find(
      (rule) =>
        rule.includes(entry.action) &&
        rule.includes(entry.demand),
    );
    assert.ok(
      executor,
      "[BOOM TC military] reactive exception executor is missing: " + entry.label,
    );
    const text = normalize(executor);
    assert.ok(
      text.includes(entry.witness),
      "[BOOM TC military] reactive exception lost its capability/target witness: " + entry.label,
    );
    assert.ok(
      !text.includes("(goal bt-tc-project-goal 0)"),
      "[BOOM TC military] " + entry.label + " is incorrectly blocked by the TC project gate",
    );
  }

  const camel = rules.find(
    (rule) =>
      rule.includes("(train camel)") &&
      rule.includes("(up-compare-goal bt-standing-camel-target-goal > 0)"),
  );
  assert.ok(
    camel,
    "[BOOM TC military] Camel reactive executor is missing",
  );
  assert.ok(
    !camel.includes("(goal bt-tc-project-goal 0)"),
    "[BOOM TC military] Camel reactive executor must remain available during a pending TC project",
  );
  assert.ok(
    sourceText.includes("(players-unit-type-count any-enemy knight-line >= 6)") &&
      sourceText.includes("(players-unit-type-count any-enemy war-elephant-line >= 3)") &&
      sourceText.includes("(players-unit-type-count any-enemy scout-cavalry-line >= 10)"),
    "[BOOM TC military] Camel exception must retain direct enemy-cavalry/equivalent witnesses",
  );

  const protectedExecutors = [
    {
      label: "Knight",
      action: "(train knight-line)",
      demand: "(goal bt-knight-demand-goal 1)",
    },
    {
      label: "Crossbow",
      action: "(train crossbowman)",
      demand: "(goal bt-crossbow-demand-goal 1)",
    },
    {
      label: "Ram",
      action: "(train battering-ram-line)",
      demand: "(goal bt-ram-demand-goal 1)",
    },
    {
      label: "Siege Tower",
      action: "(train siege-tower)",
      demand: "(goal bt-siege-tower-demand-goal 1)",
    },
  ];

  for (const entry of protectedExecutors) {
    const executor = rules.find(
      (rule) =>
        rule.includes(entry.action) &&
        rule.includes(entry.demand),
    );
    assert.ok(
      executor,
      "[BOOM TC military] protected executor is missing: " + entry.label,
    );
    const text = normalize(executor);
    for (const gate of tcGate) {
      assert.ok(
        text.includes(gate),
        "[BOOM TC military] " + entry.label + " executor lacks the active-TC capital boundary: " + gate,
      );
    }
  }

  const protectedDemandWriters = [
    {
      label: "Ram",
      action: "(set-goal bt-ram-demand-goal 1)",
      witness: "(goal attack-goal 1)",
    },
    {
      label: "Siege Tower",
      action: "(set-goal bt-siege-tower-demand-goal 1)",
      witness: "(goal attack-goal 1)",
    },
  ];

  for (const entry of protectedDemandWriters) {
    const writer = rules.find(
      (rule) =>
        rule.includes(entry.action) &&
        rule.includes(entry.witness),
    );
    assert.ok(
      writer,
      "[BOOM TC military] protected demand writer is missing: " + entry.label,
    );
    const text = normalize(writer);
    for (const gate of tcGate) {
      assert.ok(
        text.includes(gate),
        "[BOOM TC military] " + entry.label + " demand writer can arm during a pending TC project: " + gate,
      );
    }
  }

  const tcArbitration = rules.find(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-boom)") &&
      rule.includes("(goal bt-standing-army-demand-goal 1)") &&
      rule.includes("(goal bt-tc-project-goal 2)") &&
      rule.includes("(goal bt-tc-project-goal 3)") &&
      rule.includes("(set-goal bt-standing-army-demand-goal 0)"),
  );
  assert.ok(
    tcArbitration,
    "[BOOM TC military] TC arbitration rule is missing",
  );

  for (const demand of [
    "bt-monk-demand-goal",
    "bt-mangonel-demand-goal",
    "bt-scorpion-demand-goal",
  ]) {
    assert.ok(
      !tcArbitration.includes("(set-goal " + demand + " 0)"),
      "[BOOM TC military] capital arbitration must not cancel reactive demand: " + demand,
    );
  }

  assert.ok(
    !tcArbitration.includes("(set-goal bt-ram-demand-goal 0)"),
    "[BOOM TC military] capital arbitration must not pretend queued Ram production can be unspent",
  );
  assert.ok(
    !tcArbitration.includes("(set-goal bt-siege-tower-demand-goal 0)"),
    "[BOOM TC military] capital arbitration must not tear down an already-active Siege Tower state machine",
  );
}

function validateBoomPaperReplay(rules, sourceText) {
  const policy = {
    strategy: "boom",
    age: "castle",
    tc: 1,
    tcProject: 0,
    tcStage: "idle",
    floor: 4,
    standingDemand: 1,
    castleCommitment: 0,
    threat: false,
    knightUnitGoal: false,
    knightDemand: 0,
    crossbowDemand: 0,
  };

  const recomputeFloor = () => {
    if (policy.age !== "castle" || policy.strategy !== "boom") return;
    if (policy.tc < 2) policy.floor = 4;
    else if (policy.tc < 3) policy.floor = 6;
    else policy.floor = 8;
  };

  const capitalArbitration = () => {
    if (
      policy.strategy === "boom" &&
      (policy.tcProject === 2 || policy.tcProject === 3) &&
      ["demanded", "resource-claimed", "placement-pending"].includes(policy.tcStage)
    ) {
      policy.standingDemand = 0;
      policy.knightDemand = 0;
      policy.crossbowDemand = 0;
    }
  };

  const demandStanding = () => {
    if (policy.strategy === "boom" && policy.age === "castle") {
      policy.standingDemand = 1;
    }
    capitalArbitration();
  };

  const startTc2 = () => {
    policy.tcProject = 2;
    policy.tcStage = "demanded";
    capitalArbitration();
  };

  const startTc3 = () => {
    policy.tcProject = 3;
    policy.tcStage = "demanded";
    capitalArbitration();
  };

  const completeTc = (count) => {
    policy.tc = count;
    policy.tcProject = 0;
    policy.tcStage = "idle";
    recomputeFloor();
    demandStanding();
  };

  recomputeFloor();
  assert.equal(policy.floor, 4, "[BOOM replay] Castle BOOM at one TC must use floor 4");

  policy.tc = 1;
  policy.knightUnitGoal = true;
  assert.equal(
    policy.tc >= 2,
    false,
    "[BOOM replay] generic Knight posture must not qualify at one TC",
  );

  startTc2();
  assert.equal(policy.tcProject, 2, "[BOOM replay] TC2 demand did not persist");
  assert.equal(policy.tcStage, "demanded", "[BOOM replay] TC2 did not enter demanded stage");
  assert.equal(
    policy.standingDemand,
    0,
    "[BOOM replay] active TC2 demand did not suppress standing military demand",
  );

  policy.tcStage = "resource-claimed";
  capitalArbitration();
  assert.equal(
    policy.standingDemand,
    0,
    "[BOOM replay] TC resource claim did not retain capital priority",
  );

  policy.tcStage = "placement-pending";
  capitalArbitration();
  assert.equal(
    policy.standingDemand,
    0,
    "[BOOM replay] TC placement pending did not retain capital priority",
  );

  policy.tcStage = "foundation-active";
  demandStanding();
  assert.equal(
    policy.standingDemand,
    1,
    "[BOOM replay] foundation-active TC incorrectly retained pre-foundation military suppression",
  );
  assert.equal(
    policy.floor,
    4,
    "[BOOM replay] standing floor must remain TC1 until TC2 actually completes",
  );

  completeTc(2);
  assert.equal(policy.floor, 6, "[BOOM replay] TC2 completion did not raise BOOM floor to 6");
  assert.equal(
    policy.standingDemand,
    1,
    "[BOOM replay] TC2 completion did not restore normal standing-demand evaluation",
  );
  assert.equal(
    policy.tc >= 2,
    true,
    "[BOOM replay] Knight eligibility witness did not become true after TC2",
  );

  startTc3();
  assert.equal(policy.tcProject, 3, "[BOOM replay] TC3 demand did not persist");
  assert.equal(
    policy.standingDemand,
    0,
    "[BOOM replay] active TC3 demand did not suppress standing military demand",
  );

  completeTc(3);
  assert.equal(policy.floor, 8, "[BOOM replay] TC3 completion did not raise BOOM floor to 8");
  assert.equal(
    policy.standingDemand,
    1,
    "[BOOM replay] TC3 completion did not restore normal standing-demand evaluation",
  );

  policy.castleCommitment = 1;
  assert.equal(
    policy.strategy === "flush" || policy.castleCommitment === 0,
    false,
    "[BOOM replay] Castle commitment unexpectedly allowed normal standing production",
  );
  policy.strategy = "flush";
  assert.equal(
    policy.strategy === "flush",
    true,
    "[BOOM replay] FLUSH emergency override did not activate",
  );

  policy.strategy = "boom";
  policy.castleCommitment = 0;
  policy.tc = 1;
  policy.knightUnitGoal = false;
  assert.equal(
    policy.knightUnitGoal && policy.tc >= 2,
    false,
    "[BOOM replay] generic Knight posture incorrectly activated before TC2",
  );
  policy.tc = 2;
  policy.knightUnitGoal = true;
  assert.equal(
    policy.knightUnitGoal && policy.tc >= 2,
    true,
    "[BOOM replay] generic Knight posture failed its TC2 maturity witness",
  );

  assert.ok(
    sourceText.includes("(set-goal bt-standing-army-floor-goal bt-castle-boom-army-floor-tc1)"),
    "[BOOM replay] TC1 floor writer missing",
  );
  assert.ok(
    sourceText.includes("(set-goal bt-standing-army-floor-goal bt-castle-boom-army-floor-tc2)"),
    "[BOOM replay] TC2 floor writer missing",
  );
  assert.ok(
    sourceText.includes("(set-goal bt-standing-army-floor-goal bt-castle-boom-army-floor-tc3)"),
    "[BOOM replay] TC3 floor writer missing",
  );

  const farmScale2 = rules.find(
    (rule) =>
      rule.includes("(building-type-count-total town-center >= 2)") &&
      rule.includes("(up-modify-goal bt-farm-transition-reserve-goal c:+ 2)") &&
      rule.includes("(up-modify-goal bt-farm-depleted-reserve-goal c:+ 3)"),
  );
  const farmScale3 = rules.find(
    (rule) =>
      rule.includes("(building-type-count-total town-center >= 3)") &&
      rule.includes("(up-modify-goal bt-farm-transition-reserve-goal c:+ 2)") &&
      rule.includes("(up-modify-goal bt-farm-depleted-reserve-goal c:+ 3)"),
  );
  assert.ok(farmScale2, "[BOOM replay] 2-TC farm scaling witness missing");
  assert.ok(farmScale3, "[BOOM replay] 3-TC farm scaling witness missing");

  for (const tech of ["ri-wheel-barrow", "ri-hand-cart", "ri-bow-saw", "ri-gold-shaft-mining"]) {
    assert.ok(
      rules.some(
        (rule) =>
          rule.includes("(goal strategy-goal bt-strategy-boom)") &&
          rule.includes(tech) &&
          rule.includes("(can-research-with-escrow " + tech + ")"),
      ),
      "[BOOM replay] BOOM eco-research lifecycle missing engine-feasibility witness for " + tech,
    );
  }

  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-tc-project-goal 2)") &&
        rule.includes("(goal bt-resource-mode-goal bt-resource-mode-tc-stone)"),
    ),
    "[BOOM replay] TC2 stone resource-mode handoff missing",
  );
  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-tc-project-goal 3)") &&
        rule.includes("(goal bt-resource-mode-goal bt-resource-mode-tc-stone)"),
    ),
    "[BOOM replay] TC3 stone resource-mode handoff missing",
  );
}

function validateOnagerLifecycle(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");

  const executor = rules.find(
    (rule) =>
      rule.includes("(goal bt-onager-demand-goal 1)") &&
      rule.includes("(up-research-status c: ri-onager == research-complete)") &&
      rule.includes("(train onager)") &&
      rule.includes("(can-train onager)"),
  );
  assert.ok(executor, "[Onager] research-complete train executor is missing");
  const executorText = normalize(executor);
  assert.ok(
    executorText.includes("(unit-type-count-total onager < bt-onager-response-target)"),
    "[Onager] production cap must count queued/current Onagers",
  );
  assert.ok(
    !executorText.includes("(unit-type-count-total mangonel-line < bt-onager-response-target)"),
    "[Onager] production cap must not use the Mangonel line",
  );

  const invalidator = rules.find(
    (rule) =>
      rule.includes("(goal bt-onager-demand-goal 1)") &&
      rule.includes("(set-goal bt-onager-demand-goal 0)") &&
      rule.includes("(strategic-number sn-resource-control != ri-onager)"),
  );
  assert.ok(invalidator, "[Onager] demand invalidator is missing");
  const invalidatorText = normalize(invalidator);
  assert.ok(
    invalidatorText.includes("(goal bt-research-siege-workshop-claim-goal 0)"),
    "[Onager] active research claim must protect demand invalidation",
  );
  assert.ok(
    !invalidatorText.includes("(not (up-research-status c: ri-onager == research-available))"),
    "[Onager] demand invalidator must not treat research-pending/complete as failure",
  );

  const researchExecutor = rules.find(
    (rule) =>
      rule.includes("(research ri-onager)") &&
      rule.includes("(can-research-with-escrow ri-onager)") &&
      rule.includes("(set-goal bt-research-siege-workshop-claim-goal ri-onager)"),
  );
  assert.ok(
    researchExecutor,
    "[Onager] research executor must pair feasibility, action, and persistent claim",
  );

  const completion = rules.find(
    (rule) =>
      rule.includes("(goal bt-onager-demand-goal 1)") &&
      rule.includes("(up-research-status c: ri-onager == research-complete)") &&
      rule.includes("(unit-type-count onager >= bt-onager-response-target)") &&
      rule.includes("(set-goal bt-onager-demand-goal 0)"),
  );
  assert.ok(
    completion,
    "[Onager] demand completion must use actual completed Onagers",
  );
}

function validateLifecycleAnchors(sourceText, rules) {
  for (const symbol of [
    "bt-strategy-boom",
    "bt-strategy-rush",
    "bt-strategy-flush",
    "bt-strategy-castle-power",
    "bt-resource-mode-goal",
    "bt-standing-army-demand-goal",
    "bt-attack-timer",
    "bt-rush-attack-archer-witness",
    "bt-rush-stall-latch-goal",
  ]) {
    assert.ok(sourceText.includes(symbol), `[Lifecycle] missing canonical state symbol: ${symbol}`);
  }

  requireRule(
    rules,
    "RUSH -> Castle-power",
    "(goal strategy-goal bt-strategy-rush)",
    "(current-age >= castle-age)",
    "(players-building-count target-player > 0)",
    "(unit-type-count archer-line >= 4)",
    "(set-goal strategy-goal bt-strategy-castle-power)",
  );
  requireRule(
    rules,
    "RUSH -> BOOM fallback",
    "(goal strategy-goal bt-strategy-rush)",
    "(current-age >= castle-age)",
    "(set-goal strategy-goal bt-strategy-boom)",
  );
  requireRule(
    rules,
    "Feudal RUSH objective-loss release",
    "(goal strategy-goal bt-strategy-rush)",
    "(current-age == feudal-age)",
    "(players-building-count target-player <= 0)",
    "(not (town-under-attack))",
    "(not (goal bt-any-threat-goal 1))",
    "(set-goal strategy-goal bt-strategy-boom)",
  );

  const rushWriterIndices = rules
    .map((rule, index) => ({ rule, index }))
    .filter(({ rule }) => rule.includes("(set-goal strategy-goal bt-strategy-rush)"))
    .map(({ index }) => index);
  const rushReleaseIndex = rules.findIndex(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-rush)") &&
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(players-building-count target-player <= 0)") &&
      rule.includes("(set-goal strategy-goal bt-strategy-boom)"),
  );
  assert.ok(
    rushReleaseIndex >= 0,
    "[Lifecycle] Feudal RUSH objective-loss release rule cannot be located",
  );
  assert.ok(
    rushWriterIndices.length > 0 && rushReleaseIndex > Math.max(...rushWriterIndices),
    "[Lifecycle] Feudal RUSH objective-loss release must occur after every RUSH writer",
  );
  requireRule(
    rules,
    "Castle-power expiry",
    "(goal strategy-goal bt-strategy-castle-power)",
    "(current-age >= imperial-age)",
    "(set-goal strategy-goal bt-strategy-boom)",
  );
}

function validateLineHygiene(text) {
  const lines = text.split("\n");
  const maxLength = Math.max(...lines.map((line) => line.length));
  assert.ok(
    maxLength <= 255,
    `[Hygiene] controller line exceeds 255 characters (max observed: ${maxLength})`,
  );
  assert.ok(
    !/\t/.test(text),
    "[Hygiene] tab characters are not permitted in Basilisk.per",
  );
  return maxLength;
}

function validateRetryDoctrine(sourceText) {
  const forbidden = [
    "bt-research-barracks-max-retries",
    "bt-stable-research-max-retries",
    "bt-siege-research-max-retries",
    "bt-economic-research-max-retries",
    "bt-research-mining-camp-gold-shaft-mining-retry-goal",
    "bt-research-barracks-pikeman-retry-goal",
    "bt-research-stable-cavalier-retry-goal",
    "bt-research-stable-paladin-retry-goal",
    "bt-research-stable-heavy-camel-retry-goal",
    "bt-research-siege-capped-ram-retry-goal",
    "bt-research-siege-ram-retry-goal",
    "bt-military-siege-workshop-retry-goal",
  ];
  for (const symbol of forbidden) {
    assert.ok(
      !sourceText.includes(symbol),
      `[Retry doctrine] stale terminal-retry symbol remains: ${symbol}`,
    );
  }
  assert.ok(
    sourceText.includes("(defconst bt-research-failure-backoff-seconds 30)"),
    "[Retry doctrine] shared bounded research backoff constant is missing",
  );
}

function ruleIndex(rules, ...needles) {
  const index = rules.findIndex((rule) =>
    needles.every((needle) => renderRule(rule).includes(needle)),
  );
  assert.notEqual(index, -1, "[Source order] rule not found: " + needles.join(" | "));
  return index;
}

function requireRule(rules, label, ...needles) {
  ruleIndex(rules, ...needles);
  return label;
}

function validateCastleCataphractImperialHandoff(rules) {
  const writerIndex = ruleIndex(
    rules,
    "(current-age == castle-age)",
    "(goal bt-castle-cataphract-demand-goal 0)",
    "(set-goal bt-castle-cataphract-demand-goal 1)",
  );
  const writer = rules[writerIndex];
  assert.ok(
    writer.includes("(not (can-research-with-escrow imperial-age))"),
    "[Castle-Cataphract/Imperial handoff] pre-Imperial Castle-Cataphract demand writer must refuse to create demand when Imperial is already research-feasible",
  );
}

function validateAgeTransitionQueueGates(rules) {
  const castleStop = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(unit-type-count villager >= bt-castle-villagers)") &&
      rule.includes("(goal bt-castle-commitment-goal 1)") &&
      rule.includes("(set-goal train-civ-goal -1)"),
  );
  assert.ok(
    castleStop,
    "[Age transition] Castle villager stop gate is missing",
  );
  assert.ok(
    !castleStop.includes("(can-research-with-escrow castle-age)"),
    "[Age transition] Castle villager stop gate must not depend on research queue availability",
  );

  const castleExecutor = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal bt-castle-commitment-goal 1)") &&
      rule.includes("(research castle-age)"),
  );
  assert.ok(
    castleExecutor,
    "[Age transition] Castle research executor is missing",
  );
  assert.ok(
    castleExecutor.includes("(can-research-with-escrow castle-age)"),
    "[Age transition] Castle research executor lost its engine feasibility guard",
  );

  const castleBankMilitaryProducers = [
    "(train spearman-line)",
    "(train skirmisher-line)",
    "(train archer-line)",
  ];
  for (const action of castleBankMilitaryProducers) {
    const producer = rules.find(
      (rule) =>
        rule.includes("(current-age >= feudal-age)") &&
        rule.includes("(goal bt-standing-army-demand-goal 1)") &&
        rule.includes("(goal bt-castle-commitment-goal 0)") &&
        rule.includes(action),
    );
    assert.ok(
      producer,
      "[Age transition] Feudal standing military producer must yield to Castle commitment: " +
        action,
    );
  }

  const rushArcherProducer = rules.find(
    (rule) =>
      rule.includes("(goal strategy-goal bt-strategy-rush)") &&
      rule.includes("(goal unit-goal archer-line)") &&
      rule.includes("(goal bt-castle-commitment-goal 0)") &&
      rule.includes("(train archer-line)"),
  );
  assert.ok(
    rushArcherProducer,
    "[Age transition] RUSH archer producer must yield to Castle commitment",
  );

  const imperialStop = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(unit-type-count villager >= bt-imperial-villagers)") &&
      rule.includes("(goal bt-imperial-commitment-goal 1)") &&
      rule.includes("(set-goal train-civ-goal -1)"),
  );
  assert.ok(
    imperialStop,
    "[Age transition] Imperial villager stop gate is missing",
  );
  assert.ok(
    !imperialStop.includes("(can-research-with-escrow imperial-age)"),
    "[Age transition] Imperial villager stop gate must not depend on research queue availability",
  );
  assert.ok(
    !imperialStop.includes("(goal bt-castle-cataphract-demand-goal 0)"),
    "[Age transition] Imperial villager stop gate must not depend on Castle Cataphract demand",
  );

  const imperialExecutor = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(goal bt-imperial-commitment-goal 1)") &&
      rule.includes("(research imperial-age)"),
  );
  assert.ok(
    imperialExecutor,
    "[Age transition] Imperial research executor is missing",
  );
  assert.ok(
    imperialExecutor.includes("(can-research-with-escrow imperial-age)"),
    "[Age transition] Imperial research executor lost its engine feasibility guard",
  );
  assert.ok(
    !imperialExecutor.includes("(goal bt-castle-cataphract-demand-goal 0)"),
    "[Age transition] Imperial research executor must not depend on Castle Cataphract demand",
  );
}

function validateImperialPrerequisiteProviders(rules) {
  const fundingMode = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)") &&
      rule.includes("(not (can-research-with-escrow imperial-age))"),
  );
  assert.ok(
    fundingMode,
    "[Imperial prerequisites] direct second-provider funding-mode selector is missing",
  );
  assert.ok(
    fundingMode.includes("(building-type-count-total monastery >= 1)") &&
      fundingMode.includes("(building-type-count-total university >= 1)") &&
      fundingMode.includes("(building-type-count-total siege-workshop >= 1)"),
    "[Imperial prerequisites] funding-mode selector must recognize Monastery, University, or Siege Workshop as the existing qualifying provider",
  );
  for (const crisis of [
    "bt-resource-mode-food-crisis",
    "bt-resource-mode-gold-crisis",
    "bt-resource-mode-wood-crisis",
  ]) {
    assert.ok(
      fundingMode.includes(`(not (goal bt-resource-mode-goal ${crisis}))`),
      "[Imperial prerequisites] funding mode must yield to " + crisis,
    );
  }

  const fundingAllocation = rules.find(
    (rule) =>
      rule.includes("(goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)") &&
      rule.includes("(set-strategic-number sn-wood-gatherer-percentage 40)"),
  );
  assert.ok(
    fundingAllocation,
    "[Imperial prerequisites] temporary wood-priority funding allocation is missing",
  );
  assert.ok(
    fundingAllocation.includes("(set-strategic-number sn-food-gatherer-percentage 45)") &&
      fundingAllocation.includes("(set-strategic-number sn-gold-gatherer-percentage 15)") &&
      fundingAllocation.includes("(set-strategic-number sn-stone-gatherer-percentage 0)"),
    "[Imperial prerequisites] funding allocation percentages are incomplete",
  );

  const siegeBuilder = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(goal bt-imperial-prereq-backoff-goal 0)") &&
      rule.includes("(building-type-count-total castle < 1)") &&
      rule.includes("(building-type-count-total siege-workshop < 1)") &&
      rule.includes("(up-pending-objects c: siege-workshop == 0)") &&
      rule.includes("(strategic-number sn-resource-control == 0)") &&
      rule.includes("(can-build-with-escrow siege-workshop)") &&
      rule.includes("(build siege-workshop)"),
  );
  assert.ok(
    siegeBuilder,
    "[Imperial prerequisites] direct Siege Workshop capability provider is missing",
  );
  assert.ok(
    siegeBuilder.includes("(building-type-count-total monastery >= 1)") &&
      siegeBuilder.includes("(building-type-count-total university >= 1)") &&
      siegeBuilder.includes("(not (can-research-with-escrow imperial-age)"),
    "[Imperial prerequisites] Siege Workshop provider must require an existing qualifying provider and unfinished Imperial Age",
  );
  assert.ok(
    siegeBuilder.includes("(set-strategic-number sn-resource-control bt-imperial-siege-claim)"),
    "[Imperial prerequisites] Siege Workshop provider must claim the shared resource mutex",
  );
  assert.ok(
    !siegeBuilder.includes("(goal bt-castle-cataphract-demand-goal"),
    "[Imperial prerequisites] Siege Workshop provider must not depend on Castle Cataphract demand",
  );

  const universityBuilder = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(goal bt-imperial-prereq-backoff-goal 0)") &&
      rule.includes("(building-type-count-total castle < 1)") &&
      rule.includes("(building-type-count-total university < 1)") &&
      rule.includes("(up-pending-objects c: university == 0)") &&
      rule.includes("(strategic-number sn-resource-control == 0)") &&
      rule.includes("(can-build-with-escrow university)") &&
      rule.includes("(build university)"),
  );
  assert.ok(
    universityBuilder,
    "[Imperial prerequisites] direct University fallback capability provider is missing",
  );
  assert.ok(
    universityBuilder.includes("(building-type-count-total monastery >= 1)") &&
      universityBuilder.includes("(building-type-count-total siege-workshop >= 1)") &&
      universityBuilder.includes("(not (can-research-with-escrow imperial-age)"),
    "[Imperial prerequisites] University provider must require an existing qualifying provider and unfinished Imperial Age",
  );
  assert.ok(
    universityBuilder.includes("(set-strategic-number sn-resource-control bt-imperial-university-claim)"),
    "[Imperial prerequisites] University provider must claim the shared resource mutex",
  );
  assert.ok(
    !universityBuilder.includes("(goal bt-castle-cataphract-demand-goal"),
    "[Imperial prerequisites] University provider must not depend on Castle Cataphract demand",
  );

  for (const [claim, building] of [
    ["bt-imperial-siege-claim", "siege-workshop"],
    ["bt-imperial-university-claim", "university"],
  ]) {
    const completion = rules.find(
      (rule) =>
        rule.includes(`(strategic-number sn-resource-control == ${claim})`) &&
        rule.includes(`(building-type-count ${building} >= 1)`) &&
        rule.includes("(set-goal bt-imperial-prereq-backoff-goal 0)") &&
        rule.includes("(set-strategic-number sn-resource-control 0)"),
    );
    assert.ok(
      completion,
      "[Imperial prerequisites] " + building + " completion must release the shared claim and clear backoff",
    );

    const watchdog = rules.find(
      (rule) =>
        rule.includes(`(strategic-number sn-resource-control == ${claim})`) &&
        rule.includes("(timer-triggered bt-imperial-prereq-watchdog-timer)") &&
        rule.includes("(up-pending-objects c: " + building + " > 0)"),
    );
    assert.ok(
      watchdog,
      "[Imperial prerequisites] " + building + " watchdog support is missing",
    );

    const failure = rules.find(
      (rule) =>
        rule.includes(`(strategic-number sn-resource-control == ${claim})`) &&
        rule.includes("(timer-triggered bt-imperial-prereq-watchdog-timer)") &&
        rule.includes("(up-pending-objects c: " + building + " == 0)") &&
        rule.includes("(set-goal bt-imperial-prereq-backoff-goal 1)") &&
        rule.includes("(set-strategic-number sn-resource-control 0)"),
    );
    assert.ok(
      failure,
      "[Imperial prerequisites] " + building + " watchdog failure must release ownership and arm bounded backoff",
    );
  }

  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(goal bt-imperial-prereq-backoff-goal 1)") &&
        rule.includes("(timer-triggered bt-imperial-prereq-backoff-timer)") &&
        rule.includes("(set-goal bt-imperial-prereq-backoff-goal 0)"),
    ),
    "[Imperial prerequisites] bounded backoff release is missing",
  );
  assert.ok(
    !rules.some((rule) => rule.includes("bt-imperial-prereq-demand-goal")),
    "[Imperial prerequisites] obsolete persistent prerequisite demand goal must remain removed",
  );
}

function validateAgeBankPriority(rules) {
  const castleBank = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(unit-type-count villager >= bt-castle-villagers)") &&
      rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-castle-bank)") &&
      rule.includes("(set-goal bt-castle-commitment-goal 1)") &&
      rule.includes("(set-goal train-civ-goal -1)"),
  );
  assert.ok(
    castleBank,
    "[Age banking] Castle bank priority rule is missing",
  );
  assert.ok(
    !castleBank.includes("(goal bt-castle-cataphract-demand-goal"),
    "[Age banking] Castle bank must not be gated by military/Cataphract demand",
  );
  assert.ok(
    !castleBank.includes("(goal bt-castle-commitment-goal 0)"),
    "[Age banking] Castle bank must not require a prior commitment state",
  );
  assert.ok(
    castleBank.includes("(goal bt-resource-mode-goal 0)"),
    "[Age banking] Castle bank must only claim the bank when no P0 crisis is active",
  );

  const imperialBank = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(unit-type-count villager >= bt-imperial-villagers)") &&
      rule.includes("(set-goal bt-resource-mode-goal bt-resource-mode-imperial-bank-prep)") &&
      rule.includes("(set-goal bt-imperial-commitment-goal 1)") &&
      rule.includes("(set-goal train-civ-goal -1)"),
  );
  assert.ok(
    imperialBank,
    "[Age banking] Imperial bank priority rule is missing",
  );
  assert.ok(
    imperialBank.includes("(goal bt-resource-mode-goal 0)"),
    "[Age banking] Imperial bank must only claim the bank when no P0 crisis is active",
  );
  assert.ok(
    !imperialBank.includes("(goal bt-castle-cataphract-demand-goal"),
    "[Age banking] Imperial bank must not be gated by Castle Cataphract demand",
  );
}

function validateFeudalEcoResearchPriority(rules, sourceText) {
  const forbidden = [
    "(goal bt-research-cavalry-counter-package-goal 0)",
    "(goal bt-research-ranged-counter-package-goal 0)",
    "(goal bt-research-cataphract-package-goal 0)",
    "(goal bt-research-siege-package-goal 0)",
    "(goal bt-research-monk-package-goal 0)",
  ];

  const horseExecutor = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(up-research-status c: ri-horse-collar == research-available)") &&
      rule.includes("(building-type-count mill >= 1)") &&
      rule.includes("(can-research-with-escrow ri-horse-collar)") &&
      rule.includes("(research ri-horse-collar)") &&
      rule.includes("(goal bt-research-mill-claim-goal 0)"),
  );
  assert.ok(
    horseExecutor,
    "[Feudal eco] Horse Collar direct-feasibility executor is missing",
  );
  assert.ok(
    horseExecutor.includes("(not (goal bt-castle-commitment-goal 1))") &&
      horseExecutor.includes("(strategic-number sn-resource-control == 0)"),
    "[Feudal eco] Horse Collar executor must yield to Castle commitment and shared resource ownership",
  );
  for (const veto of forbidden) {
    assert.ok(
      !horseExecutor.includes(veto),
      "[Feudal eco] Horse Collar executor still contains unrelated military package veto: " + veto,
    );
  }

  const doubleBitAxeExecutor = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(up-research-status c: ri-double-bit-axe == research-available)") &&
      rule.includes("(can-research-with-escrow ri-double-bit-axe)") &&
      rule.includes("(research ri-double-bit-axe)") &&
      rule.includes("(goal bt-research-lumber-camp-claim-goal 0)"),
  );
  assert.ok(
    doubleBitAxeExecutor,
    "[Feudal eco] Double-Bit Axe direct-feasibility executor is missing",
  );
  assert.ok(
    doubleBitAxeExecutor.includes("(not (goal bt-castle-commitment-goal 1))"),
    "[Feudal eco] Double-Bit Axe executor must yield to Castle commitment",
  );
  for (const veto of forbidden) {
    assert.ok(
      !doubleBitAxeExecutor.includes(veto),
      "[Feudal eco] Double-Bit Axe executor still contains unrelated military package veto: " + veto,
    );
  }

  for (const obsoleteState of [
    "bt-horse-collar-demand-goal",
    "bt-double-bit-axe-demand-goal",
    "bt-feudal-eco-hold-goal",
  ]) {
    assert.equal(
      sourceText.includes(obsoleteState),
      false,
      "[Feudal eco] obsolete cached eco state must remain removed: " + obsoleteState,
    );
  }
}


function validateEconomicResearchPackageIsolation(rules, sourceText) {
  const forbidden = [
    "(goal bt-research-cavalry-counter-package-goal 0)",
    "(goal bt-research-ranged-counter-package-goal 0)",
    "(goal bt-research-cataphract-package-goal 0)",
    "(goal bt-research-siege-package-goal 0)",
    "(goal bt-research-monk-package-goal 0)",
  ];

  const executors = [
    ["ri-heavy-plow", "bt-research-mill-claim-goal"],
    ["ri-gold-mining", "bt-research-mining-camp-claim-goal"],
    ["ri-wheel-barrow", "bt-research-town-center-claim-goal"],
    ["ri-hand-cart", "bt-research-town-center-claim-goal"],
    ["ri-bow-saw", "bt-research-lumber-camp-claim-goal"],
    ["ri-gold-shaft-mining", "bt-research-mining-camp-claim-goal"],
  ];

  for (const [tech, claimGoal] of executors) {
    const executor = rules.find(
      (rule) =>
        rule.includes("(research " + tech + ")") &&
        rule.includes("(can-research-with-escrow " + tech + ")") &&
        rule.includes("(goal " + claimGoal + " 0)") &&
        rule.includes("(set-goal " + claimGoal + " " + tech + ")"),
    );
    assert.ok(
      executor,
      "[Castle eco] direct research executor is missing for " + tech,
    );
    for (const veto of forbidden) {
      assert.ok(
        !executor.includes(veto),
        "[Castle eco] " + tech + " executor still depends on unrelated military package veto: " + veto,
      );
    }
  }

  for (const obsoleteState of [
    "bt-heavy-plow-demand-goal",
    "bt-gold-mining-demand-goal",
    "bt-wheelbarrow-demand-goal",
    "bt-hand-cart-demand-goal",
    "bt-bow-saw-demand-goal",
    "bt-gold-shaft-mining-demand-goal",
  ]) {
    assert.equal(
      sourceText.includes(obsoleteState),
      false,
      "[Castle eco] obsolete cached eco demand state must remain removed: " + obsoleteState,
    );
  }
}

function validateMillPlacement(sourceText, rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");

  for (const [name, value] of [
    ["bt-mill-placement-zone-size", "6"],
    ["bt-mill-placement-separation-distance", "10"],
  ]) {
    assert.ok(
      sourceText.includes("(defconst " + name + " " + value + ")"),
      "[Mill placement] missing placement constant: " + name,
    );
  }

  const laterMillExecutor = rules.find(
    (rule) =>
      rule.includes("(up-compare-goal bt-mill-project-goal >= 2)") &&
      rule.includes("(current-age >= feudal-age)") &&
      rule.includes("(building-type-count farm >= 1)") &&
      rule.includes("(up-set-placement-data my-player-number farm c: 0)") &&
      rule.includes("(up-build place-control 0 c: mill)"),
  );
  assert.ok(
    laterMillExecutor,
    "[Mill placement] later-Mill executor must use farm-anchored controlled placement",
  );

  const laterMillText = normalize(laterMillExecutor);
  for (const witness of [
    "(set-strategic-number sn-placement-zone-size bt-mill-placement-zone-size)",
    "(set-strategic-number sn-dropsite-separation-distance bt-mill-placement-separation-distance)",
  ]) {
    assert.ok(
      laterMillText.includes(witness),
      "[Mill placement] executor missing placement hygiene: " + witness,
    );
  }

  const secondMillFarmGate = rules.filter(
    (rule) =>
      rule.includes("(goal bt-mill-project-goal 0)") &&
      rule.includes("(building-type-count mill >= 1)") &&
      rule.includes("(set-goal bt-mill-project-goal 2)"),
  );
  assert.equal(
    secondMillFarmGate.length,
    2,
    "[Mill lifecycle] expected separate 1-TC and 2+-TC farm-density gates for the second Mill",
  );
  for (const rule of secondMillFarmGate) {
    assert.ok(
      rule.includes("(building-type-count-total farm >= bt-mill-second-farm-threshold-"),
      "[Mill lifecycle] second-Mill demand must remain farm-density gated",
    );
  }
}

function validateStateCoverage(rules) {
  for (const state of [
    "strategy-goal",
    "unit-goal",
    "bt-resource-mode-goal",
    "attack-goal",
  ]) {
    const writerIndices = rules
      .map((rule, index) =>
        rule.includes(`(set-goal ${state}`) ? index : -1,
      )
      .filter((index) => index >= 0);
    const readerIndices = rules
      .map((rule, index) =>
        rule.includes(`(goal ${state}`) ||
        rule.includes(`(not (goal ${state}`) ? index : -1,
      )
      .filter((index) => index >= 0);
    const actionReaderIndices = rules
      .map((rule, index) =>
        (
          rule.includes(`(goal ${state}`) ||
          rule.includes(`(not (goal ${state}`)
        ) && /\((build|train|research|attack-now)\b/.test(rule)
          ? index
          : -1,
      )
      .filter((index) => index >= 0);

    assert.ok(
      writerIndices.length > 0,
      `[State coverage] no writer exists for ${state}`,
    );
    assert.ok(
      readerIndices.length > 0,
      `[State coverage] no reader exists for ${state}`,
    );
    assert.ok(
      actionReaderIndices.some((index) => index > writerIndices[0]),
      `[State coverage] no engine-action consumer exists downstream of ${state}'s first writer`,
    );
  }
}

function validatePreemptionReplay(repoRootPath) {
  const replayPath = path.join(
    repoRootPath,
    "validation",
    "preemption-telemetry-replay.js",
  );
  assert.ok(
    fs.existsSync(replayPath),
    "[Preemption replay] deterministic replay harness is missing",
  );

  const result = spawnSync(
    process.execPath,
    [replayPath],
    {
      stdio: "inherit",
      cwd: repoRootPath,
    },
  );

  assert.equal(
    result.status,
    0,
    "[Preemption replay] deterministic lifecycle replay failed with exit code " +
      result.status,
  );
}

function validateSourceOrder(rules) {
  const firstStrategyWriterIndex = ruleIndex(rules, "(set-goal strategy-goal");
  const firstResourceModeWriterIndex = rules.findIndex(
    (rule, index) =>
      index > firstStrategyWriterIndex &&
      rule.includes("(set-goal bt-resource-mode-goal ") &&
      !rule.includes("(true)"),
  );
  assert.ok(
    firstResourceModeWriterIndex > firstStrategyWriterIndex,
    "[Source order] resource-mode arbitration writer must exist after primary strategy selection",
  );

  const strategySelectionWriterIndices = rules
    .map((rule, index) =>
      index < firstResourceModeWriterIndex &&
      rule.includes("(set-goal strategy-goal")
        ? index
        : -1,
    )
    .filter((index) => index >= 0);

  assert.ok(
    strategySelectionWriterIndices.length > 0,
    "[Source order] primary strategy-selection writers are missing",
  );

  const finalStrategySelectionWriterIndex = Math.max(
    ...strategySelectionWriterIndices,
  );

  const firstProductionIndex = ruleIndex(
    rules,
    "(goal bt-standing-army-demand-goal 1)",
    "(strategic-number sn-resource-control == 0)",
    "(can-build barracks)",
    "(build barracks)",
  );
  const attackIndex = ruleIndex(
    rules,
    "(timer-triggered bt-attack-timer)",
    "(goal attack-goal 0)",
    "(attack-now)",
  );

  for (let index = 0; index < finalStrategySelectionWriterIndex; index += 1) {
    const rule = rules[index];
    if (
      !rule.includes("(goal strategy-goal") &&
      !rule.includes("(not (goal strategy-goal")
    ) {
      continue;
    }
    assert.ok(
      !/(^|\s)\((build|train|research|attack-now)\b/.test(rule),
      "[One-pass latency] strategy reader before final strategy-selection writer issues an engine action",
    );
  }

  assert.ok(
    finalStrategySelectionWriterIndex >= firstStrategyWriterIndex,
    "[Source order] final strategy-selection writer must not precede first strategy writer",
  );
  assert.ok(
    finalStrategySelectionWriterIndex < firstResourceModeWriterIndex,
    "[Source order] strategy selection must precede resource-mode arbitration",
  );
  assert.ok(
    firstResourceModeWriterIndex < firstProductionIndex,
    "[Source order] resource-mode arbitration must precede production",
  );
  assert.ok(
    firstProductionIndex < attackIndex,
    "[Source order] production capability must precede attack delivery",
  );
}

function validateHandoffWiring(repoRootPath, legacyPath) {
  assert.ok(
    fs.existsSync(legacyPath),
    "[Harness] legacy lifecycle regression validator is missing",
  );
  const legacySource = fs.readFileSync(legacyPath, "utf8");
  assert.ok(
    !legacySource.includes("ByzTeacher/ByzMetaTeacher.per"),
    "[Harness] legacy validator still defaults to the obsolete ByzTeacher controller path",
  );
  assert.ok(
    legacySource.includes("Basilisk") && legacySource.includes("Basilisk.per"),
    "[Harness] legacy validator does not default to Basilisk/Basilisk.per",
  );
  assert.ok(
    fs.existsSync(path.join(repoRootPath, "docs", "project", "VALIDATOR-HANDOFF.md")),
    "[Harness] validator handoff document is missing",
  );
}

const semanticDumpIndex = process.argv.indexOf("--dump-semantic-rules");
if (semanticDumpIndex !== -1) {
  const outputPath = process.argv[semanticDumpIndex + 1];
  assert.ok(
    outputPath,
    "[Semantic dump] --dump-semantic-rules requires an output path",
  );
  const semanticRules = parseStrictTopLevelForms(source).filter(
    (form) => form.head === "defrule",
  );
  fs.writeFileSync(outputPath, JSON.stringify(semanticRules), "utf8");
  console.log(
    JSON.stringify({
      status: "PASS",
      semanticRuleCount: semanticRules.length,
      outputPath,
    }),
  );
  process.exit(0);
}

validatePreprocessorStructure(source);
const parsedForms = parseStrictTopLevelForms(source);
validateBasiliskGoalNamespace(parsedForms);
validateParserGradeRuleStructure(source);
validateRuleStructure(source);
validateBalancedParens(source);
validateGoalFactSyntax(source);
validateBooleanArity(source);
const rules = extractRules(source);
assert.ok(rules.length > 0, "[Parser] no defrule forms found");
const engineLimitReport = validateEngineLimits(source, rules);
const identifierReport = validateIdentifiers(source, repoRoot);
const commandReport = validateAIRefCommandVocabulary(source, rules, repoRoot);
validateAIRefCommandSchema(source, rules, repoRoot);
validateAIRefTypedComparisonSyntax(source);
validateAIRefDucStateSafety(source);
validateBombardTrebuchetDucLifecycle(rules);
validateAIRefGoalOutputSafety(source);
validateAIRefDucSearchBounds(source);
validateLineHygiene(source);
validateRetryDoctrine(source);
validateAgeNarrationLatches(source, rules);
  validateStrategicNarration(source, rules);
validateLifecycleAnchors(source, rules);
validateOnagerLifecycle(rules);
validatePikemanLifecycle(rules);
validateRangedCounterLifecycle(rules);
validateCataphractResearchLifecycle(rules);
validateCastleStoneLifecycle(rules);
validateEliteVarangianResearchCapability(rules);
validateBarracksSquiresArsonLifecycle(rules);
validateBlacksmithResearchLifecycle(rules);
validateCastleCataphractImperialHandoff(rules);
validateAgeTransitionQueueGates(rules);
validateImperialPrerequisiteProviders(rules);
validateAgeBankPriority(rules);
validateFeudalEcoResearchPriority(rules, source);
validateEconomicResearchPackageIsolation(rules, source);
validateEngineActionContracts(rules, identifierReport.objectLinesByName);
validateScoutActionContracts(rules);
validateFarmEscrowContracts(rules);
validateEcoResearchDemandRemoval(rules);
validateMillPlacement(source, rules);
validateLateEcoTechnologyMaturity(rules);
validateScoutingLifecycle(source, rules);
validateVillagerHygiene(rules);
validateDerivedThreatStateOrdering(rules);
validateResourceModeArbiter(rules);
validateAttackContracts(rules);
validateAttackResultLifecycle(rules);
validateRushStallFailurePolicy(rules, source);
validateBoomEconomicLifecycle(rules, source);
validateBoomPaperReplay(rules, source);
validateAttackAllocationPolicy(rules);
validateFeudalCastleEconomyContract(rules);
validateFeudalFarmTransitionBudget(rules, source);
validateImperialSiegeExit(rules, source);
validateImperialSiegeAttackOrdering(rules);
validateTcScaledFarms(rules);
validateNoDuplicateRules(rules);
validateBackoffTimerUniqueness(rules);
validateStateCoverage(rules);
validateBasiliskPreemption(rules, source, repoRoot);
if (!contractOnly) {
  validatePreemptionReplay(repoRoot);
}
validateSourceOrder(rules);
if (!contractOnly) {
  validateHandoffWiring(repoRoot, legacyValidatorPath);

  const legacy = spawnSync(
    process.execPath,
    [legacyValidatorPath, controllerPath],
    {
      stdio: "inherit",
      cwd: repoRoot,
    },
  );

  assert.equal(
    legacy.status,
    0,
    `[Harness] repair-lifecycle-replay.js failed with exit code ${legacy.status}`,
  );
}

const controllerRelative = path.relative(repoRoot, controllerPath) || controllerPath;
console.log(JSON.stringify({
  status: "PASS",
  entrypoint: "validation/basilisk-validator.js",
  controller: controllerRelative,
  rules: rules.length,
  checks: [
    "balanced parentheses and string-safe top-level structure",
    "exact logical-operator arity",
    "DE rule/element/line/timer hard limits",
    "exact defrule => separator and action-section structure",
    "invalid identifier resolution for engine-facing typed slots",
    "AIRef command arity, parameter-family, type-prefix, and typed-operand schema contracts",
    "AIRef documented enum/value-family validation for symbolic Const slots",
    "AIRef retained-search DUC target-scope validation",
    "BBC DUC armed/target-loss lifecycle contract",
    "AIRef parameter-specific numeric range validation",
    "AIRef split typed-comparison syntax validation",
    "typed c:/g:/s: operand resolution and timer identifiers",
    "missing closing parenthesis diagnostics with source line",
    "rule-too-long diagnostics at the DE 32-element ceiling",
    "near-limit rule reporting at 30+ elements",
    "complex single-line defrule rejection above the 150-character community safety threshold",
    "line/tab hygiene",
    "persistent-demand bounded-backoff doctrine",
    "lifecycle anchors",
    "age-transition queue gates separate civilian bank ownership from engine research feasibility",
    "persistent Feudal eco demand, hold, and package-veto separation",
    "Castle eco persistent demand and military-package isolation",

    "engine-action can-* contracts",
    "fielded Scout witness for up-send-scout",
    "escrow-aware farm gate consistency",
    "derived threat/counter state ordering before package consumers",
    "queued/completed train witnesses tied to the trained line",
    "completed/pending build witnesses tied to the built building",
    "duplicate and out-of-range defconst diagnostics",
    "attack-now timer/idle/completion contracts",
    "repeated Feudal RUSH stall release and consecutive-failure replay",
    "Castle BOOM standing-floor maturity and military-capability arbitration",
    "Castle BOOM deterministic paper replay and economic milestone witnesses",
    "critical state writer/reader/action coverage",
    "pre-final-strategy one-pass action ban",
    "strategy -> resource-mode -> production -> attack source order",
    "live Thumb Ring resource-mode gate",
    "validator handoff wiring",
    "full repair-lifecycle-replay regression suite",
    "semantic lifecycle invariant self-test is available as validation/basilisk-validator-selftest.js",
  ],
  maxControllerLine: engineLimitReport.maxLineLength,
  maxRuleElements: engineLimitReport.worstElements,
  maxRuleIndex: engineLimitReport.worstRule,
  maxRuleHeadroom: engineLimitReport.maxRuleHeadroom,
  nearLimitRules: engineLimitReport.nearLimitRules,
  atLimitRules: engineLimitReport.atLimitRules,
  nearLimitThreshold: engineLimitReport.nearLimitThreshold,
  hardRuleElementLimit: engineLimitReport.hardRuleElementLimit,
  complexSingleLineThreshold: engineLimitReport.complexSingleLineThreshold,
  airefCommandCount: commandReport.commandCount,
  airefCommandsUsed: commandReport.usedCommandCount,
  airefCommandSourceBlobSha: commandReport.sourceBlobSha,
  airefCommandVersionCounts: commandReport.versionCounts,
  identifierSlots: identifierReport.checkedSlots,
  identifierSupplements: identifierReport.engineSupplements,
}, null, 2));
