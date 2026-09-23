#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
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
      if (ch === "\n") {
        result += "\n";
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
    const headMatch = form.match(/^\(\s*([A-Za-z][A-Za-z0-9_-]*)/);
    assert.ok(
      headMatch,
      `[Top-level syntax] could not identify form head near source offset ${cursor}`,
    );

    const head = headMatch[1];
    assert.ok(
      head === "defconst" || head === "defrule",
      `[Top-level syntax] unsupported top-level form '${head}' near source offset ${cursor}`,
    );

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
    object: path.join(repoRootPath, "extracted", "inventories", "airef-object-inventory.json"),
    tech: path.join(repoRootPath, "extracted", "inventories", "airef-tech-inventory.json"),
    strategicNumber: path.join(repoRootPath, "extracted", "inventories", "airef-strategic-number-inventory.json"),
    class: path.join(repoRootPath, "extracted", "inventories", "airef-class-inventory.json"),
    valueFamily: path.join(repoRootPath, "extracted", "inventories", "airef-value-family-inventory.json"),
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
  const engineSupplements = new Set(["siege-tower", "ri-logistica"]);
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
    "extracted",
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
    "extracted",
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
    "extracted",
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
    "extracted",
    "inventories",
    "airef-strategic-number-inventory.json",
  );
  const techPath = path.join(
    repoRootPath,
    "extracted",
    "inventories",
    "airef-tech-inventory.json",
  );
  const objectPath = path.join(
    repoRootPath,
    "extracted",
    "inventories",
    "airef-object-inventory.json",
  );
  const classPath = path.join(
    repoRootPath,
    "extracted",
    "inventories",
    "airef-class-inventory.json",
  );
  const valueFamilyPath = path.join(
    repoRootPath,
    "extracted",
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

function validateDoubleBitAxeLifecycle(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");

  const demandWriter = rules.find(
    (rule) =>
      rule.includes("(goal bt-double-bit-axe-demand-goal 0)") &&
      rule.includes("(set-goal bt-double-bit-axe-demand-goal 1)"),
  );
  assert.ok(
    demandWriter,
    "[DBA lifecycle] Double-Bit Axe demand writer is missing",
  );
  const demandText = normalize(demandWriter);
  for (const prerequisite of [
    "(current-age == feudal-age)",
    "(food-amount >= bt-double-bit-axe-food-buffer)",
    "(wood-amount >= bt-double-bit-axe-wood-buffer)",
    "(up-research-status c: ri-double-bit-axe == research-available)",
  ]) {
    assert.ok(
      demandText.includes(prerequisite),
      "[DBA lifecycle] demand writer is missing prerequisite: " + prerequisite,
    );
  }

  const releaseRules = rules.filter(
    (rule) =>
      rule.includes("(goal bt-double-bit-axe-demand-goal 1)") &&
      rule.includes("(set-goal bt-double-bit-axe-demand-goal 0)"),
  );
  assert.ok(
    releaseRules.length > 0,
    "[DBA lifecycle] demand release rule is missing",
  );

  for (const releaseRule of releaseRules) {
    const releaseText = normalize(releaseRule);
    assert.ok(
      !releaseText.includes("(can-research-with-escrow castle-age)"),
      "[DBA lifecycle] Castle feasibility must not clear Double-Bit Axe demand before execution",
    );
    assert.ok(
      releaseText.includes("(not (food-amount >= bt-double-bit-axe-food-buffer))"),
      "[DBA lifecycle] demand release must preserve the configured food buffer",
    );
    assert.ok(
      releaseText.includes("(not (wood-amount >= bt-double-bit-axe-wood-buffer))"),
      "[DBA lifecycle] demand release must preserve the configured wood buffer",
    );
    assert.ok(
      releaseText.includes("(up-research-status c: ri-double-bit-axe >= research-pending)"),
      "[DBA lifecycle] demand release must clear an already-pending/researching DBA",
    );
  }

  const executor = rules.find(
    (rule) =>
      rule.includes("(goal bt-double-bit-axe-demand-goal 1)") &&
      rule.includes("(research ri-double-bit-axe)"),
  );
  assert.ok(
    executor,
    "[DBA lifecycle] Double-Bit Axe research executor is missing",
  );
  const executorText = normalize(executor);
  for (const witness of [
    "(current-age == feudal-age)",
    "(can-research-with-escrow ri-double-bit-axe)",
    "(goal bt-research-lumber-camp-claim-goal 0)",
  ]) {
    assert.ok(
      executorText.includes(witness),
      "[DBA lifecycle] executor is missing witness: " + witness,
    );
  }
}

function validateLateEcoTechnologyMaturity(rules) {
  const normalize = (rule) => rule.replace(/\s+/g, " ");

  const cropRotationExecutor = rules.find(
    (rule) =>
      rule.includes("(research ri-crop-rotation)") &&
      rule.includes("(set-goal bt-research-mill-claim-goal ri-crop-rotation)"),
  );
  assert.ok(
    cropRotationExecutor,
    "[Late-eco lifecycle] Crop Rotation research executor is missing",
  );
  const cropText = normalize(cropRotationExecutor);
  for (const witness of [
    "(current-age >= imperial-age)",
    "(building-type-count farm >= bt-crop-rotation-farm-threshold)",
    "(can-research-with-escrow ri-crop-rotation)",
  ]) {
    assert.ok(
      cropText.includes(witness),
      "[Late-eco lifecycle] Crop Rotation executor is missing maturity witness: " + witness,
    );
  }

  const twoManDemandWriter = rules.find(
    (rule) =>
      rule.includes("(set-goal bt-two-man-saw-demand-goal 1)"),
  );
  assert.ok(
    twoManDemandWriter,
    "[Late-eco lifecycle] Two-Man Saw demand writer is missing",
  );
  const twoManDemandText = normalize(twoManDemandWriter);
  for (const witness of [
    "(current-age >= imperial-age)",
    "(unit-type-count villager >= bt-two-man-saw-villagers)",
    "(unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)",
    "(goal strategy-goal bt-strategy-boom)",
    "(research-available ri-two-man-saw)",
  ]) {
    assert.ok(
      twoManDemandText.includes(witness),
      "[Late-eco lifecycle] Two-Man Saw demand writer is missing maturity witness: " + witness,
    );
  }

  const twoManExecutor = rules.find(
    (rule) =>
      rule.includes("(goal bt-two-man-saw-demand-goal 1)") &&
      rule.includes("(research ri-two-man-saw)"),
  );
  assert.ok(
    twoManExecutor,
    "[Late-eco lifecycle] Two-Man Saw research executor is missing",
  );
  const twoManExecutorText = normalize(twoManExecutor);
  for (const witness of [
    "(current-age >= imperial-age)",
    "(unit-type-count villager >= bt-two-man-saw-villagers)",
    "(unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)",
    "(goal strategy-goal bt-strategy-boom)",
    "(not (goal bt-cataphract-demand-goal 1))",
    "(can-research-with-escrow ri-two-man-saw)",
  ]) {
    assert.ok(
      twoManExecutorText.includes(witness),
      "[Late-eco lifecycle] Two-Man Saw executor is missing maturity witness: " + witness,
    );
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

  const house = requireRule("(housing-headroom <= 5)", "preemptive housing rule");
  assert.ok(house.includes("(up-pending-objects c: house == 0)"), "[Villager hygiene] housing rule must stay pending-safe");
  assert.ok(house.includes("(can-build house)"), "[Villager hygiene] housing rule must use engine build feasibility");
  assert.ok(
    rules.some(
      (rule) =>
        rule.includes("(building-type-count-total lumber-camp >= 1)") &&
        rule.includes("(up-set-placement-data my-player-number lumber-camp c: 6)") &&
        rule.includes("(up-build place-control 0 c: house)"),
    ),
    "[Villager hygiene] lumber-local house placement rule is missing",
  );

  for (const resource of ["wood", "gold", "stone"]) {
    const campType = resource === "wood" ? "lumber-camp" : "mining-camp";
    const rule = requireRule(
      "(dropsite-min-distance " + resource + " > 8)",
      resource + " dropsite refresh",
    );
    assert.ok(
      rule.includes("(resource-found " + resource + ")"),
      "[Villager hygiene] " + resource + " refresh must require a found resource",
    );
    assert.ok(
      rule.includes("(up-pending-objects c: " + campType + " == 0)"),
      "[Villager hygiene] " + resource + " refresh must be pending-safe",
    );
    assert.ok(
      rule.includes("(can-build " + campType + ")"),
      "[Villager hygiene] " + resource + " refresh must use engine build feasibility",
    );
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
    "bt-spear-counter-level-goal",
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
    fs.existsSync(path.join(repoRootPath, "validation", "VALIDATOR-HANDOFF.md")),
    "[Harness] validator handoff document is missing",
  );
}

function ruleIndex(rules, ...needles) {
  const index = rules.findIndex((rule) =>
    needles.every((needle) => renderRule(rule).includes(needle)),
  );
  assert.notEqual(index, -1, `[Source order] rule not found: ${needles.join(" | ")}`);
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

function validateFeudalEcoResearchPriority(rules, sourceText) {
  const forbidden = [
    "(goal bt-research-cavalry-counter-package-goal 0)",
    "(goal bt-research-ranged-counter-package-goal 0)",
    "(goal bt-research-cataphract-package-goal 0)",
    "(goal bt-research-siege-package-goal 0)",
    "(goal bt-research-monk-package-goal 0)",
  ];

  const horseDemandWriter = rules.find(
    (rule) =>
      rule.includes("(goal bt-horse-collar-demand-goal 0)") &&
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(up-research-status c: ri-horse-collar == research-available)") &&
      rule.includes("(building-type-count mill >= 1)") &&
      rule.includes("(set-goal bt-horse-collar-demand-goal 1)"),
  );
  assert.ok(
    horseDemandWriter,
    "[Feudal eco] persistent Horse Collar demand writer is missing",
  );

  assert.ok(
    sourceText.includes("(defconst bt-horse-collar-demand-goal 698)"),
    "[Feudal eco] persistent Horse Collar demand goal constant is missing",
  );

  const horseExecutor = rules.find(
    (rule) =>
      rule.includes("(goal bt-horse-collar-demand-goal 1)") &&
      rule.includes("(research ri-horse-collar)"),
  );
  assert.ok(
    horseExecutor,
    "[Feudal eco] Horse Collar executor is missing",
  );
  for (const witness of [
    "(current-age == feudal-age)",
    "(can-research-with-escrow ri-horse-collar)",
    "(goal bt-research-mill-claim-goal 0)",
  ]) {
    assert.ok(
      horseExecutor.includes(witness),
      "[Feudal eco] Horse Collar executor is missing witness: " + witness,
    );
  }
  for (const veto of forbidden) {
    assert.ok(
      !horseExecutor.includes(veto),
      "[Feudal eco] Horse Collar executor still contains unrelated package veto: " + veto,
    );
  }

  const dbaExecutor = rules.find(
    (rule) =>
      rule.includes("(goal bt-double-bit-axe-demand-goal 1)") &&
      rule.includes("(research ri-double-bit-axe)"),
  );
  assert.ok(
    dbaExecutor,
    "[Feudal eco] Double-Bit Axe executor is missing",
  );
  for (const veto of forbidden) {
    assert.ok(
      !dbaExecutor.includes(veto),
      "[Feudal eco] Double-Bit Axe executor still contains unrelated package veto: " + veto,
    );
  }

  const horseHold = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal bt-horse-collar-demand-goal 1)") &&
      rule.includes("(set-goal bt-feudal-eco-hold-goal 1)"),
  );
  assert.ok(
    horseHold,
    "[Feudal eco] persistent Horse Collar hold rule is missing",
  );
  for (const veto of forbidden) {
    assert.ok(
      !horseHold.includes(veto),
      "[Feudal eco] Horse Collar hold rule still contains unrelated package veto: " + veto,
    );
  }

  const dbaHold = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(goal bt-double-bit-axe-demand-goal 1)") &&
      rule.includes("(set-goal bt-feudal-eco-hold-goal 1)"),
  );
  assert.ok(
    dbaHold,
    "[Feudal eco] persistent Double-Bit Axe hold rule is missing",
  );

  const dbaImmediateHold = rules.find(
    (rule) =>
      rule.includes("(current-age == feudal-age)") &&
      rule.includes("(up-research-status c: ri-double-bit-axe == research-available)") &&
      rule.includes("(can-research-with-escrow ri-double-bit-axe)") &&
      rule.includes("(set-goal bt-feudal-eco-hold-goal 1)"),
  );
  assert.ok(
    dbaImmediateHold,
    "[Feudal eco] first-pass Double-Bit Axe hold rule is missing",
  );
  for (const veto of forbidden) {
    assert.ok(
      !dbaHold.includes(veto),
      "[Feudal eco] Double-Bit Axe hold rule still contains unrelated package veto: " + veto,
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
  const economicExecutors = [
    ["ri-heavy-plow", "bt-heavy-plow-demand-goal"],
    ["ri-gold-mining", "bt-gold-mining-demand-goal"],
    ["ri-wheel-barrow", "bt-wheelbarrow-demand-goal"],
    ["ri-hand-cart", "bt-hand-cart-demand-goal"],
    ["ri-bow-saw", "bt-bow-saw-demand-goal"],
    ["ri-gold-shaft-mining", "bt-gold-shaft-mining-demand-goal"],
  ];

  assert.ok(
    sourceText.includes("(defconst bt-heavy-plow-demand-goal 699)"),
    "[Castle eco] persistent Heavy Plow demand goal constant is missing",
  );

  const heavyPlowDemand = rules.find(
    (rule) =>
      rule.includes("(goal bt-heavy-plow-demand-goal 0)") &&
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(up-research-status c: ri-horse-collar >= research-complete)") &&
      rule.includes("(building-type-count-total farm >= bt-mill-second-farm-threshold-1tc)") &&
      rule.includes("(up-research-status c: ri-heavy-plow == research-available)") &&
      rule.includes("(set-goal bt-heavy-plow-demand-goal 1)"),
  );
  assert.ok(
    heavyPlowDemand,
    "[Castle eco] persistent Heavy Plow demand writer is missing",
  );

  const heavyPlowCompletion = rules.find(
    (rule) =>
      rule.includes("(goal bt-research-mill-claim-goal ri-heavy-plow)") &&
      rule.includes("(up-research-status c: ri-heavy-plow == research-complete)") &&
      rule.includes("(set-goal bt-heavy-plow-demand-goal 0)"),
  );
  assert.ok(
    heavyPlowCompletion,
    "[Castle eco] Heavy Plow completion must clear persistent demand",
  );

  for (const [tech, demandGoal] of economicExecutors) {
    const executor = rules.find(
      (rule) =>
        rule.includes("(goal " + demandGoal + " 1)") &&
        rule.includes("(research " + tech + ")"),
    );
    assert.ok(
      executor,
      "[Castle eco] executor is missing for " + tech,
    );
    assert.ok(
      executor.includes("(can-research-with-escrow " + tech + ")"),
      "[Castle eco] executor lost engine-native feasibility gate for " + tech,
    );
    for (const veto of forbidden) {
      assert.ok(
        !executor.includes(veto),
        "[Castle eco] " + tech + " executor still depends on unrelated military package veto: " + veto,
      );
    }
  }
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
      rule.includes("(goal bt-castle-cataphract-demand-goal 0)") &&
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

  const imperialExecutor = rules.find(
    (rule) =>
      rule.includes("(current-age == castle-age)") &&
      rule.includes("(goal bt-castle-cataphract-demand-goal 0)") &&
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

function validateSourceOrder(rules) {
  const firstStrategyWriterIndex = ruleIndex(rules, "(set-goal strategy-goal");
  const finalStrategyWriterIndex = Math.max(
    ...rules
      .map((rule, index) =>
        rule.includes("(set-goal strategy-goal") ? index : -1,
      )
      .filter((index) => index >= 0),
  );
  const resourceModeResetIndex = ruleIndex(
    rules,
    "(true)",
    "(set-goal bt-resource-mode-goal 0)",
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

  for (let index = 0; index < finalStrategyWriterIndex; index += 1) {
    const rule = rules[index];
    if (
      !rule.includes("(goal strategy-goal") &&
      !rule.includes("(not (goal strategy-goal")
    ) {
      continue;
    }
    assert.ok(
      !/(^|\s)\((build|train|research|attack-now)\b/.test(rule),
      `[One-pass latency] strategy reader at rule ${index} before final strategy writer issues an engine action`,
    );
  }

  assert.ok(
    finalStrategyWriterIndex >= firstStrategyWriterIndex,
    "[Source order] final strategy writer must not precede first strategy writer",
  );
  assert.ok(
    finalStrategyWriterIndex < resourceModeResetIndex,
    "[Source order] final strategy writer must precede resource-mode arbitration",
  );
  assert.ok(
    resourceModeResetIndex < firstProductionIndex,
    "[Source order] resource-mode arbitration must precede production",
  );
  assert.ok(
    firstProductionIndex < attackIndex,
    "[Source order] production capability must precede attack delivery",
  );
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

function validateStrategicNarration(sourceText, rules) {
  for (const symbol of [
    "bt-debug-verbosity-goal",
    "bt-debug-last-opening-goal",
    "bt-debug-last-threat-goal",
    "bt-debug-last-resource-mode-goal",
    "bt-debug-last-unit-goal",
    "bt-debug-last-strategy-goal",
    "bt-debug-last-castle-block-goal",
    "bt-debug-last-age-event-goal",
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

  const chatRules = rules.filter((rule) =>
    rule.includes('(chat-local-to-self "BASILISK |'),
  );
  assert.ok(
    chatRules.length >= 80,
    "[Narration] expected a complete strategic narration layer",
  );

  for (const rule of chatRules) {
    assert.ok(
      rule.includes("(up-compare-goal bt-debug-verbosity-goal"),
      "[Narration] every diagnostic chat action must be verbosity-gated",
    );
    assert.ok(
      rule.includes("(up-compare-goal bt-debug-last-"),
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
    "BASILISK | STRATEGY | CASTLE-POWER",
    "BASILISK | THREAT | confirmed pressure.",
    "BASILISK | RESOURCE | CASTLE-BANK",
    "BASILISK | COMPOSITION | CROSSBOW",
    "BASILISK | AGE | Castle blocked: engine feasibility.",
    "BASILISK | AGE | Castle ready to research.",
    "BASILISK | AGE | Castle complete.",
    "BASILISK | ECO | Horse Collar: demand active.",
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

  const firstStrategyWriter = Math.max(
    ...rules
      .map((rule, index) =>
        rule.includes("(set-goal strategy-goal bt-strategy-") ? index : -1,
      )
      .filter((index) => index >= 0),
  );
  const firstStrategyNarrator = ruleIndex(
    rules,
    '(chat-local-to-self "BASILISK | STRATEGY | FLUSH',
  );
  assert.ok(
    firstStrategyNarrator > firstStrategyWriter,
    "[Narration] strategy narration must observe finalized strategy state",
  );

  const firstResourceWriter = Math.max(
    ...rules
      .map((rule, index) =>
        rule.includes("(set-goal bt-resource-mode-goal") ? index : -1,
      )
      .filter((index) => index >= 0),
  );
  const firstResourceNarrator = ruleIndex(
    rules,
    '(chat-local-to-self "BASILISK | RESOURCE | DARK',
  );
  assert.ok(
    firstResourceNarrator > firstResourceWriter,
    "[Narration] resource-mode narration must observe finalized resource arbitration",
  );

  const firstUnitWriter = Math.max(
    ...rules
      .map((rule, index) =>
        rule.includes("(set-goal unit-goal") ? index : -1,
      )
      .filter((index) => index >= 0),
  );
  const firstUnitNarrator = ruleIndex(
    rules,
    '(chat-local-to-self "BASILISK | COMPOSITION | MIX',
  );
  assert.ok(
    firstUnitNarrator > firstUnitWriter,
    "[Narration] composition narration must observe finalized unit-goal selection",
  );

  assert.ok(
    !chatRules.some((rule) =>
      rule.includes("(true)") &&
      rule.includes("(chat-local-to-self"),
    ),
    "[Narration] unconditional diagnostic chat rule would spam every evaluation pass",
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
    "Castle-power expiry",
    "(goal strategy-goal bt-strategy-castle-power)",
    "(current-age >= imperial-age)",
    "(set-goal strategy-goal bt-strategy-boom)",
  );
}

validatePreprocessorStructure(source);
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
validateAIRefGoalOutputSafety(source);
validateAIRefDucSearchBounds(source);
validateLineHygiene(source);
validateRetryDoctrine(source);
validateStrategicNarration(source, rules);
validateLifecycleAnchors(source, rules);
validateCastleCataphractImperialHandoff(rules);
validateAgeTransitionQueueGates(rules);
validateFeudalEcoResearchPriority(rules, sourceText);
validateEconomicResearchPackageIsolation(rules, sourceText);
validateEngineActionContracts(rules, identifierReport.objectLinesByName);
validateScoutActionContracts(rules);
validateFarmEscrowContracts(rules);
validateDoubleBitAxeLifecycle(rules);
validateLateEcoTechnologyMaturity(rules);
validateScoutingLifecycle(source, rules);
validateVillagerHygiene(rules);
validateDerivedThreatStateOrdering(rules);
validateAttackContracts(rules);
validateStateCoverage(rules);
validateSourceOrder(rules);
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
    "critical state writer/reader/action coverage",
    "pre-final-strategy one-pass action ban",
    "strategy -> resource-mode -> production -> attack source order",
    "live Thumb Ring resource-mode gate",
    "validator handoff wiring",
    "full repair-lifecycle-replay regression suite",
    "validator mutation self-test is available as validation/basilisk-validator-selftest.js",
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
