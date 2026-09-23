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
  let depth = 0;
  let line = 1;
  for (const ch of sanitizeStructure(text)) {
    if (ch === "(") depth += 1;
    if (ch === ")") depth -= 1;
    assert.ok(depth >= 0, `[Parser] unexpected closing parenthesis near line ${line}`);
    if (ch === "\n") line += 1;
  }
  assert.equal(
    depth,
    0,
    `[Missing closing parenthesis] controller ends with ${depth} unmatched opening parenthesis`,
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

  const engineSupplements = new Set(["ri-logistica"]);
  for (const value of engineSupplements) universalValues.add(value);

  const identifierSource = sanitizeStructure(sourceText);
  const failures = [];
  const check = (regex, family, label) => {
    for (const match of identifierSource.matchAll(regex)) {
      const token = match[1];
      if (/^-?\d+$/.test(token)) continue;
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
      known.tech.has(match[1]) || universalValues.has(match[1]),
      `[Invalid identifier] technology-like symbol '${match[1]}' at line ${identifierSource.slice(0, match.index).split("\n").length} is not resolvable`,
    );
  }

  if (failures.length > 0) {
    const detail = failures
      .slice(0, 12)
      .map(({ label, token, line }) => label + " '" + token + "' at line " + line)
      .join("; ");
    const suffix = failures.length > 12 ? "; plus " + (failures.length - 12) + " more" : "";
    assert.fail(
      "[Invalid identifier] " + failures.length + " unresolved engine identifier(s): " + detail + suffix,
    );
  }

  return {
    checkedSlots: "build/train/research/goal/strategic-number plus typed c:/g:/s: operands and timers",
    engineSupplements: [...engineSupplements],
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
  for (const entry of objectInventory.objects ?? []) {
    for (const value of [entry.ai_name, entry.line, entry.name]) {
      if (typeof value !== "string") continue;
      for (const raw of value.split(",")) {
        const token = raw.trim().split(/\s+/)[0];
        if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(token)) objects.add(token);
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
    classes,
    parameterValues,
    strictParameterValues,
  };
}


function documentedParameterValue(parameterName, value, families) {
  if (!value || /^-?\d+$/.test(value) || value.startsWith('"')) return true;
  if (families.defconsts.has(value)) return true;
  if (value.startsWith("g:") || value.startsWith("s:") || value.startsWith("c:")) {
    return false;
  }
  const strictValues = families.strictParameterValues.get(parameterName);
  return !strictValues || strictValues.has(value);
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

    if (expression.args.some((arg) => arg && typeof arg === "object")) {
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
    if (expression.args.length !== parameters.length) {
      reportFailure(
        "command-arity-mismatch",
        expression,
        null,
        command.name +
          " expects " +
          parameters.length +
          " arguments, got " +
          expression.args.length,
      );
      return;
    }

    for (let index = 0; index < parameters.length; index += 1) {
      const parameter = parameters[index];
      const parameterName = parameter.name;
      const value = expression.args[index];

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
        !documentedParameterValue(parameterName, value, families)
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

      if (
        expectedFamily === "object" &&
        isSymbolicSchemaValue(value) &&
        !families.defconsts.has(value) &&
        !families.objects.has(value)
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

validateRuleStructure(source);
validateBalancedParens(source);
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
validateLifecycleAnchors(source, rules);
validateEngineActionContracts(rules, identifierReport.objectLinesByName);
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
    "engine-action can-* contracts",
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
