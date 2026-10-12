"use client";

import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { python } from "@codemirror/lang-python";
import { tags as t } from "@lezer/highlight";
import { Prec, type Extension } from "@codemirror/state";
import { Decoration, EditorView, MatchDecorator, ViewPlugin, keymap, type DecorationSet, type ViewUpdate } from "@codemirror/view";
import CodeMirror from "@uiw/react-codemirror";
import { useMemo, useRef } from "react";

// Highlights ____ blanks the learner has to fill in.
const blankMatcher = new MatchDecorator({ regexp: /_{3,}/g, decoration: Decoration.mark({ class: "cm-blank" }) });
const blanks = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    constructor(view: EditorView) {
      this.decorations = blankMatcher.createDeco(view);
    }
    update(u: ViewUpdate) {
      this.decorations = blankMatcher.updateDeco(u, this.decorations);
    }
  },
  { decorations: (v) => v.decorations },
);

const theme = EditorView.theme(
  {
    "&": { backgroundColor: "var(--c-code-bg)", color: "var(--c-code-text)", height: "100%", fontSize: "14px" },
    ".cm-content": { fontFamily: "var(--font-mono)", caretColor: "var(--c-code-text)" },
    ".cm-gutters": { backgroundColor: "var(--c-code-bg)", color: "var(--c-code-muted)", border: "none" },
    ".cm-activeLine, .cm-activeLineGutter": { backgroundColor: "var(--c-code-surface)" },
    "&.cm-focused .cm-cursor": { borderLeftColor: "var(--c-code-text)" },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection": { backgroundColor: "color-mix(in srgb, var(--c-accent) 40%, transparent) !important" },
    ".cm-blank": { backgroundColor: "var(--c-xp-soft)", color: "var(--c-xp)", borderRadius: "3px" },
    ".cm-scroller": { overflow: "auto" },
  },
  { dark: true },
);

const highlight = syntaxHighlighting(
  HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.definitionKeyword, t.operatorKeyword, t.moduleKeyword], color: "var(--c-code-keyword)" },
    { tag: [t.string, t.special(t.string)], color: "var(--c-code-string)" },
    { tag: [t.number, t.bool, t.null], color: "var(--c-code-number)" },
    { tag: t.comment, color: "var(--c-code-comment)", fontStyle: "italic" },
    { tag: [t.function(t.variableName), t.function(t.propertyName), t.definition(t.function(t.variableName))], color: "var(--c-code-function)" },
  ]),
);

export function CodeEditor({
  value,
  onChange,
  onRun,
  onSubmit,
  readOnly,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  onRun?: () => void;
  onSubmit?: () => void;
  readOnly?: boolean;
  label: string;
}) {
  // Handlers live in refs so the editor is not reconfigured on every render.
  const handlers = useRef({ onRun, onSubmit });
  handlers.current = { onRun, onSubmit };
  const extensions = useMemo<Extension[]>(
    () => [
      python(),
      blanks,
      theme,
      highlight,
      EditorView.contentAttributes.of({ "aria-label": label }),
      Prec.highest(
        keymap.of([
          { key: "Shift-Mod-Enter", run: () => (handlers.current.onSubmit?.(), true) },
          { key: "Mod-Enter", run: () => (handlers.current.onRun?.(), true) },
        ]),
      ),
    ],
    [label],
  );
  return (
    <CodeMirror
      value={value}
      onChange={onChange}
      extensions={extensions}
      readOnly={readOnly}
      theme="none"
      height="100%"
      className="h-full"
      basicSetup={{ foldGutter: false, syntaxHighlighting: false, highlightActiveLine: true, autocompletion: true, tabSize: 4 }}
    />
  );
}
