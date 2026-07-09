"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { Color } from "@tiptap/extension-color";
import { TextStyle } from "@tiptap/extension-text-style";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";
import CharacterCount from "@tiptap/extension-character-count";
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, TextSelection } from "@tiptap/pm/state";
import { CellSelection } from "@tiptap/pm/tables";
import { saveAs } from "file-saver";
import * as htmlDocx from "html-docx-js-typescript";
import html2pdf from "html2pdf.js";
import CreateNoticeModal, { CreateNoticeFormValues } from "@/components/modals/CreateNoticeModal";
import { BankApi } from "@/src/services/BankApi";
import { message, Spin, Table as AntTable, Tooltip } from "antd";
import FontFamilyPicker from "./FontFamilyPicker";
import FontFamily from '@tiptap/extension-font-family'
import { IoMdArrowRoundBack } from "react-icons/io";
import { IoColorPaletteOutline } from "react-icons/io5";
import { AiOutlineTable } from "react-icons/ai";





// ─── Constants ────────────────────────────────────────────────────────────────
const LS_KEY = "notice_editor_draft";
const SAVE_API_URL = "/api/notices"; // ← Replace with your actual endpoint

// ─── Custom FontFamily Extension ──────────────────────────────────────────────
const FontFamilyExtension = Extension.create({
  name: "fontFamily",
  addGlobalAttributes() {
    return [
      {
        types: ["textStyle"],
        attributes: {
          fontFamily: {
            default: null,
            parseHTML: (el) => {
              const style = el.getAttribute("style") || "";
              const match = style.match(/font-family:\s*([^;]+)/i);
              return match ? match[1].trim().replace(/['"]/g, "") : null;
            },
            renderHTML: (attrs) => {
              if (!attrs.fontFamily) return {};
              const family = attrs.fontFamily.includes(" ")
                ? `"${attrs.fontFamily}"`
                : attrs.fontFamily;
              return {
                style: `font-family: ${family} !important`,
              };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setFontFamily: (fontFamily: string) => ({ commands }) => {
        return commands.setMark("textStyle", { fontFamily });
      },
    };
  },
});

// ─── FontSize extension ───────────────────────────────────────────────────────
const FontSize = Extension.create({
  name: "fontSize",
  addGlobalAttributes() {
    return [{
      types: ["textStyle"],
      attributes: {
        fontSize: {
          default: null,
          parseHTML: (el) => el.style.fontSize?.replace("pt", "") ?? null,
          renderHTML: (attrs) =>
            attrs.fontSize ? { style: `font-size: ${attrs.fontSize}pt` } : {},
        },
      },
    }];
  },
});

// ─── TableOnlyEdit: block editing outside table cells ────────────────────────
const TableOnlyEdit = Extension.create({
  name: "tableOnlyEdit",
  addProseMirrorPlugins() {
    return [new Plugin({
      key: new PluginKey("tableOnlyEdit"),
      props: {
        handleKeyDown(view, event) {
          const { $from } = view.state.selection;
          let inside = false;
          for (let d = $from.depth; d >= 0; d--) {
            const n = $from.node(d).type.name;
            if (n === "tableCell" || n === "tableHeader") { inside = true; break; }
          }
          const nav = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
            "Home", "End", "PageUp", "PageDown", "Tab"];
          if (nav.includes(event.key)) return false;
          if (!inside && (
            ["Backspace", "Delete", "Enter"].includes(event.key) ||
            (event.key.length === 1 && !event.ctrlKey && !event.metaKey)
          )) return true; // block
          return false;
        },
        handlePaste(view) {
          const { $from } = view.state.selection;
          for (let d = $from.depth; d >= 0; d--) {
            const n = $from.node(d).type.name;
            if (n === "tableCell" || n === "tableHeader") return false;
          }
          return true; // block outside
        },
      },
    })];
  },
});

// Helper to retrieve the actual grid column widths of a table by checking all cells/rows (handling merged cells)
function getTableColWidths(tableNode: any): { widths: number[], hasColwidth: boolean } {
  let numCols = 0;
  tableNode.forEach((row: any) => {
    let rowCols = 0;
    row.forEach((cell: any) => {
      rowCols += cell.attrs.colspan || 1;
    });
    if (rowCols > numCols) {
      numCols = rowCols;
    }
  });

  if (numCols === 0) {
    return { widths: [], hasColwidth: false };
  }

  const widths = new Array(numCols).fill(0);
  let hasColwidth = false;

  tableNode.forEach((row: any) => {
    let colIdx = 0;
    row.forEach((cell: any) => {
      const colspan = cell.attrs.colspan || 1;
      const colwidth = cell.attrs.colwidth;
      if (colwidth && colwidth.length === colspan) {
        hasColwidth = true;
        for (let i = 0; i < colspan; i++) {
          if (widths[colIdx + i] === 0 && colwidth[i] > 0) {
            widths[colIdx + i] = colwidth[i];
          }
        }
      }
      colIdx += colspan;
    });
  });

  const defaultColWidth = Math.floor(698 / numCols);
  for (let i = 0; i < numCols; i++) {
    if (widths[i] === 0) {
      widths[i] = defaultColWidth;
    }
  }

  return { widths, hasColwidth };
}

// Helper to adjust column widths to sum up to exactly targetSum while keeping all columns >= minWidth
function adjustWidthsToSum(widths: number[], targetSum: number, minWidth: number): number[] {
  const numCols = widths.length;
  if (numCols === 0) return [];

  // Ensure all values are integers and at least minWidth
  let result = widths.map(w => Math.max(minWidth, Math.round(w)));

  let currentSum = result.reduce((a, b) => a + b, 0);

  let attempts = 0;
  while (currentSum !== targetSum && attempts < 100) {
    attempts++;
    let diff = targetSum - currentSum;

    if (diff > 0) {
      // Increase width: add the difference to the first column
      result[0] += diff;
    } else {
      // Decrease width (diff is negative): subtract from columns that are greater than minWidth
      let distributed = false;
      for (let i = 0; i < numCols; i++) {
        const available = result[i] - minWidth;
        if (available > 0) {
          const toSubtract = Math.min(available, -diff);
          result[i] -= toSubtract;
          diff += toSubtract;
          if (diff === 0) {
            distributed = true;
            break;
          }
        }
      }
      if (!distributed) {
        // Force the remaining diff onto the first column
        result[0] = Math.max(1, result[0] + diff);
        break;
      }
    }
    currentSum = result.reduce((a, b) => a + b, 0);
  }

  return result;
}

function updateStyleString(existingStyle: string | null | undefined, property: string, value: string): string {
  if (!existingStyle) {
    return value ? `${property}: ${value};` : "";
  }
  const styles: Record<string, string> = {};
  existingStyle.split(";").forEach((part) => {
    const trimmed = part.trim();
    if (!trimmed) return;
    const colonIdx = trimmed.indexOf(":");
    if (colonIdx === -1) return;
    const key = trimmed.substring(0, colonIdx).trim().toLowerCase();
    const val = trimmed.substring(colonIdx + 1).trim();
    styles[key] = val;
  });

  if (value) {
    styles[property.toLowerCase()] = value;
  } else {
    delete styles[property.toLowerCase()];
  }

  return Object.entries(styles)
    .map(([k, v]) => `${k}: ${v}`)
    .join("; ") + ";";
}

// ─── TableWidthConstraint: prevent table from overflowing ────────────────────
// Sets minimum column width to 20. Resizing first/last columns adjusts the middle column.
// Keeps total table width at exactly 698px so it fits perfectly on A4 without overlapping outside.
const TableWidthConstraint = Extension.create({
  name: "tableWidthConstraint",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("tableWidthConstraint"),
        appendTransaction(transactions, oldState, newState) {
          let tr = newState.tr;
          let modified = false;

          // 1. Gather all tables and their original positions
          const tables: { node: any; pos: number }[] = [];
          newState.doc.descendants((node, pos) => {
            if (node.type.name === "table") {
              tables.push({ node, pos });
            }
          });

          // 2. Process each table sequentially using the active transaction document tr.doc
          for (const { pos } of tables) {
            // Resolve the node and position in the updated document tr.doc
            const resolvedPos = tr.doc.resolve(pos);
            const node = tr.doc.nodeAt(pos);
            if (!node || node.type.name !== "table") continue;

            // Determine if the table is nested, and find parent cell & parent table if so
            let parentCellNode: any = null;
            let parentTableNode: any = null;
            for (let d = resolvedPos.depth; d > 0; d--) {
              const name = resolvedPos.node(d).type.name;
              if (!parentCellNode && (name === "tableCell" || name === "tableHeader")) {
                parentCellNode = resolvedPos.node(d);
              }
              if (name === "table") {
                parentTableNode = resolvedPos.node(d);
                break;
              }
            }

            let maxTableWidth = 698; // Default for top-level table

            if (parentCellNode && parentTableNode) {
              // Calculate nested table width limit based on parent cell width
              const parentResult = getTableColWidths(parentTableNode);
              const parentTableWidths = parentResult.widths;

              let startCol = 0;
              let colspan = 1;
              let found = false;

              parentTableNode.forEach((row: any) => {
                if (found) return;
                let colIdx = 0;
                row.forEach((cell: any) => {
                  if (found) return;
                  const cellColspan = cell.attrs.colspan || 1;
                  if (cell === parentCellNode) {
                    startCol = colIdx;
                    colspan = cellColspan;
                    found = true;
                  }
                  colIdx += cellColspan;
                });
              });

              if (found) {
                const cellWidths = parentTableWidths.slice(startCol, startCol + colspan);
                const parentCellWidth = cellWidths.reduce((a, b) => a + b, 0);
                // With cell padding of 6px 10px, the inner content width is parentCellWidth - 20px
                // Subtracting another 2px for borders
                maxTableWidth = Math.max(40, parentCellWidth - 22);
              } else {
                maxTableWidth = 200; // sensible fallback
              }
            }

            const { widths: cellWidths, hasColwidth } = getTableColWidths(node);
            if (cellWidths.length === 0) continue;

            const minCellWidth = 20;
            const numCols = cellWidths.length;
            const defaultColWidth = Math.floor(maxTableWidth / numCols);

            let widths = cellWidths.map(w => w || defaultColWidth);

            // Get old column widths from oldState.doc
            let oldWidths: number[] = [];
            let oldHasColwidth = false;
            if (pos >= 0 && pos < oldState.doc.content.size) {
              try {
                const oldNode = oldState.doc.nodeAt(pos);
                if (oldNode && oldNode.type.name === "table") {
                  const oldResult = getTableColWidths(oldNode);
                  oldWidths = oldResult.widths;
                  oldHasColwidth = oldResult.hasColwidth;
                }
              } catch (e) {
                console.warn("Could not retrieve old node for table position", pos, e);
              }
            }

            if (oldHasColwidth && oldWidths.length === numCols) {
              // Find which column was resized
              let draggedIdx = -1;
              for (let i = 0; i < numCols; i++) {
                const oldW = oldWidths[i] || defaultColWidth;
                if (Math.abs(widths[i] - oldW) > 1) {
                  draggedIdx = i;
                  break;
                }
              }

              if (draggedIdx !== -1 && draggedIdx < numCols - 1) {
                for (let j = 0; j < numCols; j++) {
                  if (j !== draggedIdx && j !== draggedIdx + 1) {
                    widths[j] = oldWidths[j] || defaultColWidth;
                  }
                }

                widths[draggedIdx] = Math.max(minCellWidth, widths[draggedIdx]);

                const combinedWidth = (oldWidths[draggedIdx] || defaultColWidth) + (oldWidths[draggedIdx + 1] || defaultColWidth);
                widths[draggedIdx + 1] = combinedWidth - widths[draggedIdx];

                if (widths[draggedIdx + 1] < minCellWidth) {
                  widths[draggedIdx + 1] = minCellWidth;
                  widths[draggedIdx] = combinedWidth - minCellWidth;
                }
              }
            }

            widths = adjustWidthsToSum(widths, maxTableWidth, minCellWidth);

            // Apply normalized widths to all rows
            let currentRowPos = pos + 1;
            node.forEach((row) => {
              let currentCellPos = currentRowPos + 1;
              let colIdx = 0;
              row.forEach((cell) => {
                const colspan = cell.attrs.colspan || 1;
                const cellColWidths = widths.slice(colIdx, colIdx + colspan);
                colIdx += colspan;

                const currentColWidth = cell.attrs.colwidth;
                const needsUpdate = !currentColWidth ||
                  currentColWidth.length !== cellColWidths.length ||
                  currentColWidth.some((w: number, idx: number) => w !== cellColWidths[idx]);

                if (needsUpdate) {
                  tr.setNodeAttribute(currentCellPos, "colwidth", cellColWidths);
                  modified = true;
                }
                currentCellPos += cell.nodeSize;
              });
              currentRowPos += row.nodeSize;
            });

            // Apply overall table width style
            const finalTableWidth = widths.reduce((a, b) => a + b, 0);
            const targetStyle = `width: ${finalTableWidth}px;`;
            const currentTableStyle = node.attrs.style;
            if (currentTableStyle !== targetStyle) {
              tr.setNodeAttribute(pos, "style", targetStyle);
              modified = true;
            }
          }

          return modified ? tr : null;
        },
      }),
    ];
  },
});

// --- MultiCellSelection: enable click-drag and Shift+click multi-cell selection ---
const MultiCellSelection = Extension.create({
  name: "multiCellSelection",
  addProseMirrorPlugins() {
    // Helper: find the cell position that encloses a given doc position
    const findCellPos = (doc: any, pos: number): number => {
      try {
        const $pos = doc.resolve(pos);
        for (let d = $pos.depth; d >= 0; d--) {
          const name = $pos.node(d).type.name;
          if (name === "tableCell" || name === "tableHeader") {
            return $pos.start(d); // content start of the cell
          }
        }
      } catch (_) { /* ignore */ }
      return -1;
    };

    return [
      new Plugin({
        key: new PluginKey("multiCellSelection"),
        props: {
          handleDOMEvents: {
            mousedown(view, event) {
              if (event.button !== 0) return false;

              const startCoords = { left: event.clientX, top: event.clientY };
              const startPosResult = view.posAtCoords(startCoords);
              if (!startPosResult) return false;

              const anchorRawPos = startPosResult.pos;
              const anchorCellStart = findCellPos(view.state.doc, anchorRawPos);
              if (anchorCellStart === -1) return false; // click outside table

              // ── Shift+Click: extend selection from current cell ──────────
              if (event.shiftKey) {
                const currentSel = view.state.selection;
                let existingAnchorPos = -1;

                if (currentSel instanceof CellSelection) {
                  existingAnchorPos = (currentSel as any).$anchorCell.pos;
                } else {
                  // Find cell around current text cursor
                  existingAnchorPos = findCellPos(view.state.doc, currentSel.from);
                }

                if (existingAnchorPos !== -1) {
                  const headCellStart = findCellPos(view.state.doc, anchorRawPos);
                  if (headCellStart !== -1 && existingAnchorPos !== headCellStart) {
                    try {
                      const cellSel = CellSelection.create(
                        view.state.doc,
                        existingAnchorPos,
                        anchorRawPos
                      );
                      view.dispatch(view.state.tr.setSelection(cellSel));
                    } catch (_) { /* ignore */ }
                    event.preventDefault();
                    return true; // consume the event
                  }
                }
              }

              // ── Drag: select multiple cells ─────────────────────────────
              const startX = event.clientX;
              const startY = event.clientY;
              const THRESHOLD = 4; // px before switching to cell selection
              let hasCellSel = false;

              const onMove = (e: MouseEvent) => {
                // Require minimum drag distance to avoid accidental cell selection
                if (!hasCellSel) {
                  const dx = e.clientX - startX;
                  const dy = e.clientY - startY;
                  if (Math.sqrt(dx * dx + dy * dy) < THRESHOLD) return;
                }

                const moveResult = view.posAtCoords({ left: e.clientX, top: e.clientY });
                if (!moveResult) return;

                const headCellStart = findCellPos(view.state.doc, moveResult.pos);
                if (headCellStart === -1) return;

                // Only create CellSelection when head is in a DIFFERENT cell
                if (headCellStart === anchorCellStart) {
                  // If we were in a cell selection and moved back to anchor cell,
                  // revert to a text cursor inside the anchor cell
                  if (hasCellSel) {
                    const tr = view.state.tr;
                    const $pos = view.state.doc.resolve(anchorRawPos);
                    tr.setSelection(TextSelection.near($pos));
                    view.dispatch(tr);
                    hasCellSel = false;
                  }
                  return;
                }

                try {
                  const cellSel = CellSelection.create(
                    view.state.doc,
                    anchorRawPos,
                    moveResult.pos
                  );
                  view.dispatch(view.state.tr.setSelection(cellSel));
                  hasCellSel = true;
                  e.preventDefault();
                } catch (_) { /* ignore */ }
              };

              const onUp = () => {
                window.removeEventListener("mousemove", onMove);
                window.removeEventListener("mouseup", onUp);
              };

              window.addEventListener("mousemove", onMove);
              window.addEventListener("mouseup", onUp);

              return false; // let ProseMirror handle the initial click normally
            },
          },
        },
      }),
    ];
  },
});

// ─── Helper: does the HTML contain a table? ──────────────────────────────────
function hasTable(html: string): boolean {
  return /<table[\s>]/i.test(html);
}

// ─── A4 preview constants (must match PREVIEW_CSS exactly) ───────────────────
const PREVIEW_PAGE_WIDTH = 794;
const PREVIEW_PAGE_HEIGHT = 1123;
const PREVIEW_PAD_V = 48;
const PREVIEW_PAD_H = 48;
const PREVIEW_USABLE_HEIGHT = PREVIEW_PAGE_HEIGHT - PREVIEW_PAD_V * 2;

// ─── Split HTML into A4 pages ─────────────────────────────────────────────────



function splitHtmlIntoPages(html: string): string[] {
  if (!html || html === "<p></p>") return [];

  const USABLE_H = PREVIEW_USABLE_HEIGHT;
  const W = PREVIEW_PAGE_WIDTH - PREVIEW_PAD_H * 2;

  const wrap = document.createElement("div");
  wrap.style.cssText = [
    "position:fixed", "top:-99999px", "left:-99999px",
    `width:${W}px`, "box-sizing:border-box",
    "font-family:'Times New Roman',serif", "font-size:11pt",
    "line-height:1.6", "color:#111", "visibility:hidden",
    "pointer-events:none", "z-index:-9999",
  ].join(";");

  wrap.innerHTML = `
    <style>
      table { border-collapse: collapse; width: 698px !important; max-width: 698px !important; min-width: 698px !important; margin: 6px 0; table-layout: fixed !important; box-sizing: border-box !important; }
      table table { width: 100% !important; max-width: 100% !important; min-width: 0 !important; margin: 0 !important; }
      th, td { border: 1px solid #000000; padding: 6px 10px; font-weight: normal; vertical-align: top; box-sizing: border-box !important; }
      table p { margin: 0; }
      p { margin: 0 0 5px; }
      h1 { font-size: 13pt; margin: 8px 0 4px; font-weight: bold; }
      h2 { font-size: 11pt; margin: 7px 0 3px; font-weight: bold; }
      h3 { font-size: 10pt; margin: 6px 0 2px; font-weight: bold; }
      ul, ol { padding-left: 16px; margin: 4px 0; }
      li { margin-bottom: 2px; }
    </style>
    ${html}
  `;
  document.body.appendChild(wrap);

  const pages: string[] = [];
  let pageNodes: string[] = [];
  let accumulated = 0;

  const flushPage = () => {
    if (pageNodes.length) {
      pages.push(pageNodes.join(""));
      pageNodes = [];
      accumulated = 0;
    }
  };

  // ── Measure height of a full table with given tbody row(s) html ──────────
  const measureRowInTable = (rowHtml: string, colWidths: number[], theadHtml: string): number => {
    const testTable = document.createElement("table");
    testTable.style.cssText = `width:${W}px;border-collapse:collapse;position:absolute;top:-9999px;left:-9999px;table-layout:fixed;visibility:hidden;`;
    if (colWidths.length) {
      const cg = document.createElement("colgroup");
      colWidths.forEach(w => {
        const col = document.createElement("col");
        col.style.width = `${w}px`;
        cg.appendChild(col);
      });
      testTable.appendChild(cg);
    }
    if (theadHtml) {
      const thead = document.createElement("thead");
      thead.innerHTML = theadHtml;
      testTable.appendChild(thead);
    }
    const tbody = document.createElement("tbody");
    tbody.innerHTML = rowHtml;
    testTable.appendChild(tbody);
    wrap.appendChild(testTable);
    const h = Math.ceil(testTable.getBoundingClientRect().height || 20);
    wrap.removeChild(testTable);
    return h;
  };

  // ── Get column widths from a rendered table ──────────────────────────────
  const getColWidths = (table: HTMLElement): number[] => {
    const firstRow = table.querySelector("tr");
    if (!firstRow) return [];
    return Array.from(firstRow.cells).map(cell => cell.getBoundingClientRect().width);
  };

  // ── Extract words from any HTML content (preserves inline tags) ──────────
  const extractWords = (el: HTMLElement): string[] => {
    const words: string[] = [];
    const walk = (node: ChildNode) => {
      if (node.nodeType === Node.TEXT_NODE) {
        (node.textContent || "").split(/\s+/).filter(w => w.trim()).forEach(w => words.push(w));
      } else {
        Array.from((node as HTMLElement).childNodes).forEach(walk);
      }
    };
    Array.from(el.childNodes).forEach(walk);
    return words;
  };

  // ── Split an oversized table row into sub-rows, word by word per cell ────
  const splitOversizedRow = (
    row: HTMLTableRowElement,
    maxH: number,
    colWidths: number[],
    theadHtml: string
  ): string[] => {
    const cells = Array.from(row.cells);
    const numCols = cells.length;

    // Extract word tokens per cell
    const cellWords: string[][] = cells.map(cell => extractWords(cell));
    const consumed = new Array(numCols).fill(0);
    const resultRows: string[] = [];

    while (consumed.some((c, i) => c < cellWords[i].length)) {
      // Binary search per cell: how many words fit in maxH?
      const segCellHtml: string[] = new Array(numCols).fill("");
      let anyProgress = false;

      for (let c = 0; c < numCols; c++) {
        const words = cellWords[c];
        const remaining = words.slice(consumed[c]);
        if (remaining.length === 0) {
          segCellHtml[c] = (cells[c].cloneNode(false) as HTMLElement).outerHTML ?? `<td></td>`;
          continue;
        }

        // Binary search for max words that fit
        let lo = 1, hi = remaining.length, best = 1;
        while (lo <= hi) {
          const mid = Math.floor((lo + hi) / 2);
          const testCellEl = cells[c].cloneNode(false) as HTMLTableCellElement;
          testCellEl.innerHTML = remaining.slice(0, mid).join(" ");
          const testRowEl = row.cloneNode(false) as HTMLTableRowElement;
          testRowEl.appendChild(testCellEl);
          const h = measureRowInTable(testRowEl.outerHTML, colWidths, theadHtml);
          if (h <= maxH) { best = mid; lo = mid + 1; }
          else { hi = mid - 1; }
        }
        if (best < 1) best = 1; // always advance at least 1 word

        const segCellEl = cells[c].cloneNode(false) as HTMLTableCellElement;
        segCellEl.innerHTML = remaining.slice(0, best).join(" ");
        segCellHtml[c] = segCellEl.outerHTML;
        consumed[c] += best;
        anyProgress = true;
      }

      if (!anyProgress) break;

      const segRowEl = row.cloneNode(false) as HTMLTableRowElement;
      segRowEl.innerHTML = segCellHtml.join("");
      resultRows.push(segRowEl.outerHTML);
    }

    return resultRows;
  };

  // ── Split a non-table element that is taller than one page ──────────────
  const splitOversizedElement = (el: HTMLElement): void => {
    if (pageNodes.length > 0) flushPage();

    const words = extractWords(el);

    if (words.length === 0) {
      pageNodes.push(el.outerHTML);
      accumulated = el.getBoundingClientRect().height + 6;
      return;
    }

    const measureSeg = (toks: string[]): number => {
      const testEl = el.cloneNode(false) as HTMLElement;
      testEl.style.cssText += ";position:absolute;top:-9999px;left:-9999px;";
      testEl.innerHTML = toks.join(" ");
      wrap.appendChild(testEl);
      const h = Math.ceil(testEl.getBoundingClientRect().height || 0);
      wrap.removeChild(testEl);
      return h;
    };

    // Binary search for how many words fit per page
    let i = 0;
    while (i < words.length) {
      const remaining = words.slice(i);
      // Binary search: max words that fit on one page
      let lo = 1, hi = remaining.length, best = 1;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const h = measureSeg(remaining.slice(0, mid));
        if (h <= PREVIEW_USABLE_HEIGHT) { best = mid; lo = mid + 1; }
        else { hi = mid - 1; }
      }
      if (best < 1) best = 1;

      const emitEl = el.cloneNode(false) as HTMLElement;
      emitEl.innerHTML = remaining.slice(0, best).join(" ");
      pageNodes.push(emitEl.outerHTML);

      i += best;

      // If there are more words, flush this page and start a new one
      if (i < words.length) {
        flushPage();
      } else {
        accumulated = measureSeg(remaining.slice(0, best)) + 6;
      }
    }
  };

  const children = Array.from(wrap.children).filter(
    c => c.tagName !== "STYLE"
  ) as HTMLElement[];

  for (const child of children) {

    // ══ TABLE ═════════════════════════════════════════════════════════════
    if (child.tagName === "TABLE") {
      const tableH = child.getBoundingClientRect().height || child.offsetHeight || 0;
      const colWidths = getColWidths(child);

      // Case A: fits on current or next fresh page
      if (accumulated + tableH <= USABLE_H || tableH <= USABLE_H) {
        if (accumulated > 0 && accumulated + tableH > USABLE_H) flushPage();
        pageNodes.push(child.outerHTML);
        accumulated += tableH + 6;
        continue;
      }

      // Case B: taller than a full page — split row by row
      const theadRows = Array.from(child.querySelectorAll("thead tr")) as HTMLElement[];
      const theadHtml = theadRows.map(r => r.outerHTML).join("");

      let theadH = 0;
      if (theadRows.length) {
        const testTable = document.createElement("table");
        testTable.style.cssText = `width:${W}px;border-collapse:collapse;position:absolute;top:-9999px;left:-9999px;`;
        const thead = document.createElement("thead");
        thead.innerHTML = theadHtml;
        testTable.appendChild(thead);
        wrap.appendChild(testTable);
        theadH = Math.ceil(testTable.getBoundingClientRect().height || 0);
        wrap.removeChild(testTable);
      }

      const bodyRows = Array.from(child.querySelectorAll("tr")).filter(
        r => !r.closest("thead")
      ) as HTMLTableRowElement[];

      if (bodyRows.length === 0) {
        if (accumulated > 0 && accumulated + tableH > USABLE_H) flushPage();
        pageNodes.push(child.outerHTML);
        accumulated += tableH + 6;
        continue;
      }

      let pendingRows: string[] = [];
      let segH = accumulated + theadH;
      const maxRowH = USABLE_H - theadH;

      for (const row of bodyRows) {
        const rowH = measureRowInTable(row.outerHTML, colWidths, theadHtml);

        // ── Row taller than a full page: split word by word ────────────────
        if (rowH > maxRowH) {
          if (pendingRows.length > 0) {
            pageNodes.push(`<table style="border-collapse:collapse;width:100%;margin:6px 0">${theadHtml ? `<thead>${theadHtml}</thead>` : ""}<tbody>${pendingRows.join("")}</tbody></table>`);
            flushPage();
            pendingRows = [];
            segH = theadH;
          }

          const subRows = splitOversizedRow(row, maxRowH, colWidths, theadHtml);
          for (const subRowHtml of subRows) {
            const subH = measureRowInTable(subRowHtml, colWidths, theadHtml);
            if (segH + subH > USABLE_H && pendingRows.length > 0) {
              pageNodes.push(`<table style="border-collapse:collapse;width:100%;margin:6px 0">${theadHtml ? `<thead>${theadHtml}</thead>` : ""}<tbody>${pendingRows.join("")}</tbody></table>`);
              flushPage();
              pendingRows = [];
              segH = theadH;
            }
            pendingRows.push(subRowHtml);
            segH += subH;
          }
          continue;
        }

        // ── Normal row ─────────────────────────────────────────────────────
        if (pendingRows.length > 0 && segH + rowH > USABLE_H) {
          pageNodes.push(`<table style="border-collapse:collapse;width:100%;margin:6px 0">${theadHtml ? `<thead>${theadHtml}</thead>` : ""}<tbody>${pendingRows.join("")}</tbody></table>`);
          flushPage();
          pendingRows = [];
          segH = theadH;
        }
        pendingRows.push(row.outerHTML);
        segH += rowH;
      }

      if (pendingRows.length > 0) {
        pageNodes.push(`<table style="border-collapse:collapse;width:100%;margin:6px 0">${theadHtml ? `<thead>${theadHtml}</thead>` : ""}<tbody>${pendingRows.join("")}</tbody></table>`);
        accumulated = segH;
      }

      continue;
    }

    // ══ NON-TABLE ══════════════════════════════════════════════════════════
    const h = child.getBoundingClientRect().height || child.offsetHeight || 20;

    // Element taller than a full page — split word by word
    if (h > PREVIEW_USABLE_HEIGHT) {
      splitOversizedElement(child);
      continue;
    }

    // Normal page-break
    if (accumulated > 0 && accumulated + h > PREVIEW_USABLE_HEIGHT) {
      pages.push(pageNodes.join(""));
      pageNodes = [];
      accumulated = 0;
    }
    pageNodes.push(child.outerHTML);
    accumulated += h + 6;
  }

  if (pageNodes.length) pages.push(pageNodes.join(""));
  document.body.removeChild(wrap);
  return pages.length ? pages : [html];
}

const ToolBtn = ({
  active, onClick, title, children, disabled = false,
}: {
  active?: boolean; onClick: () => void; title: string;
  children: React.ReactNode; disabled?: boolean;
}) => (
  <Tooltip title={title}>
    <button
      onMouseDown={(e) => { e.preventDefault(); if (!disabled) onClick(); }}
      disabled={disabled}
      style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        width: 28, height: 28,
        border: `1px solid ${active ? "#1a56db" : "transparent"}`,
        borderRadius: 4,
        background: active ? "#ebf0ff" : "transparent",
        color: disabled ? "#bbb" : active ? "#1a56db" : "#374151",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: 13, fontWeight: 600,
        opacity: disabled ? 0.38 : 1,
        transition: "all .12s",
      }}
    >
      {children}
    </button>
  </Tooltip>
);

const Divider = () => (
  <div style={{ width: 1, height: 22, background: "#e5e7eb", margin: "0 4px" }} />
);

// ─── Preview CSS ──────────────────────────────────────────────────────────────
const PREVIEW_CSS = `
  .pc table { border-collapse: collapse; width: 694px !important; max-width: 694px !important; min-width: 694px !important; margin: 6px 0; table-layout: fixed !important; box-sizing: border-box !important; }
  .pc table table { width: 100% !important; max-width: 100% !important; min-width: 0 !important; margin: 0 !important; }
  .pc th, .pc td {
    border: 1px solid #000000;
    padding: 6px 10px;
    background: transparent;
    font-weight: normal;
    vertical-align: top;
    word-break: break-word;
    overflow-wrap: break-word;
    box-sizing: border-box !important;
  }
  .pc table p { margin: 0; }
  .pc p { margin: 0 0 5px; }
  .pc h1 { font-size: 13pt; margin: 8px 0 4px; font-weight: bold; }
  .pc h2 { font-size: 11pt; margin: 7px 0 3px; font-weight: bold; }
  .pc h3 { font-size: 10pt; margin: 6px 0 2px; font-weight: bold; }
  .pc ul, .pc ol { padding-left: 16px; margin: 4px 0; }
  .pc li { margin-bottom: 2px; }
  .pc hr { border: none; border-top: 1px solid #ccc; margin: 8px 0; }
  .pc blockquote { border-left: 2px solid #2b579a; padding-left: 8px; color: #444; font-style: italic; margin: 4px 0; }
  .pc img { max-width: 100%; height: auto; margin: 4px 0; }
  .pc mark { background: #fde68a; }
  .pc strong { font-weight: bold; }
  .pc em { font-style: italic; }
  .pc u { text-decoration: underline; }
  .pc s { text-decoration: line-through; }
`;

// const FONT_GROUPS: { label: string; fonts: string[] }[] = [
//   {
//     label: "Serif",
//     fonts: ["Times New Roman", "Georgia", "Garamond", "Palatino Linotype", "Book Antiqua", "Cambria", "Constantia", "Didot"],
//   },
//   {
//     label: "Sans-serif",
//     fonts: ["Arial", "Calibri", "Helvetica", "Verdana", "Tahoma", "Trebuchet MS", "Segoe UI", "Arial Black", "Impact"],
//   },
//   {
//     label: "Monospace",
//     fonts: ["Courier New", "Consolas", "Monaco", "Menlo", "Lucida Console"],
//   },
//   {
//     label: "Other",
//     fonts: ["Comic Sans MS", "Lucida Sans Unicode", "MS Sans Serif", "Optima"],
//   },
// ];

type CreateNoticeProps = {
  setActiveTab: (activeTab: string) => void; // adjust type if needed
  setTrigger: (trigger: number) => void;
  trigger: number;
  editTempalteData: any;
  setEditTempalteData: (editTempalteData: any) => void;
};

// ─── Main component ───────────────────────────────────────────────────────────
export default function CreateNotice({ setActiveTab, setTrigger, trigger, editTempalteData, setEditTempalteData }: CreateNoticeProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);

  const [fontSize, setFontSize] = useState("11");
  const [fontFamily, setFontFamily] = useState("Times New Roman");
  const [showTableMenu, setShowTableMenu] = useState(false);
  const [hoveredTableGrid, setHoveredTableGrid] = useState<{ row: number; col: number } | null>(null);
  const [wordCount, setWordCount] = useState(0);
  const [editorHtml, setEditorHtml] = useState("");
  const [tableInserted, setTableInserted] = useState(false);
  const [previewPages, setPreviewPages] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [showDownloadPopup, setShowDownloadPopup] = useState(false);
  const [showBorderMenu, setShowBorderMenu] = useState(false);
  const [currentBorderStyle, setCurrentBorderStyle] = useState<"all" | "none" | "outer" | "notop" | "nobottom" | "noleft" | "noright" | "">("");
  const [currentBorderWidth, setCurrentBorderWidth] = useState<number>(1);
  const [showCellBgMenu, setShowCellBgMenu] = useState(false);
  const [currentCellBg, setCurrentCellBg] = useState<string>("");
  const [pendingCellBg, setPendingCellBg] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<HTMLImageElement | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [triggerNotice, setTriggerNotice] = useState<any>(0);
  const [isLoading, setIsLoading] = useState(true);
  const resizeData = useRef<{
    img: HTMLImageElement;
    direction: string;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
  } | null>(null);

  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    const el = document.getElementById("editor-wrapper");

    const preventOuterScroll = (e: WheelEvent) => {
      if (!el) return;

      const target = e.target as HTMLElement;

      // ✅ allow scroll INSIDE editor
      if (el.contains(target)) {
        const scrollEl = el;

        const isAtTop = scrollEl.scrollTop === 0;
        const isAtBottom =
          scrollEl.scrollHeight - scrollEl.scrollTop === scrollEl.clientHeight;

        // 🚫 block ONLY when trying to scroll outside
        if (
          (e.deltaY < 0 && isAtTop) ||
          (e.deltaY > 0 && isAtBottom)
        ) {
          e.preventDefault();
        }

        return;
      }

      // 🚫 block outer scroll when mouse is inside editor
      e.preventDefault();
    };

    const handleEnter = () => {
      window.addEventListener("wheel", preventOuterScroll, {
        passive: false,
      });
    };

    const handleLeave = () => {
      window.removeEventListener("wheel", preventOuterScroll);
    };

    el?.addEventListener("mouseenter", handleEnter);
    el?.addEventListener("mouseleave", handleLeave);

    return () => {
      el?.removeEventListener("mouseenter", handleEnter);
      el?.removeEventListener("mouseleave", handleLeave);
      window.removeEventListener("wheel", preventOuterScroll);
    };
  }, []);



  const CustomTextStyle = TextStyle.extend({
    addAttributes() {
      return {
        ...(this.parent?.() ?? {}),
        fontFamily: {
          default: null,
          parseHTML: (element: HTMLElement) => {
            // ✅ Use computedStyle or inline style directly — browser already decodes entities
            const fromStyle = element.style.fontFamily;
            if (fromStyle) {
              // Strip surrounding quotes: "Brush Script MT" → Brush Script MT
              return fromStyle.replace(/^['"]|['"]$/g, '').trim();
            }

            // Fallback: parse raw attribute (handles &quot; edge cases)
            const raw = element.getAttribute('style') || '';
            const decoded = raw.replace(/&quot;/g, '"').replace(/&#39;/g, "'");
            const match = decoded.match(/font-family\s*:\s*([^;!]+)/i);
            if (!match) return null;
            return match[1].replace(/^['"]|['"]$/g, '').trim();
          },
          renderHTML: (attributes: { fontFamily?: string | null }) => {
            if (!attributes.fontFamily) return {};
            const family = attributes.fontFamily.includes(' ')
              ? `"${attributes.fontFamily}"`
              : attributes.fontFamily;
            return { style: `font-family: ${family} !important` };
          },
        },
      };
    },
  });

  // ─── Editor ──────────────────────────────────────────────────────────────────
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3, 4, 5, 6] } }),

      CustomTextStyle, // ✅ MUST come AFTER StarterKit

      TextAlign.configure({ types: ["heading", "paragraph", "tableCell"] }),
      Underline,
      Color,
      FontSize,

      Highlight.configure({ multicolor: true }),

      Table.extend({
        addAttributes() {
          return {
            ...(this.parent?.() || {}),
            style: {
              default: null,
              parseHTML: (element) => element.getAttribute('style'),
              renderHTML: (attributes) => {
                if (!attributes.style) return {}
                return { style: attributes.style }
              },
            },
          }
        },
      }).configure({ resizable: true, lastColumnResizable: false }),
      TableRow,

      TableHeader.extend({
        addAttributes() {
          return {
            ...(this.parent?.() || {}),
            style: {
              default: null,
              parseHTML: (element) => element.getAttribute('style'),
              renderHTML: (attributes) => {
                if (!attributes.style) return {}
                return { style: attributes.style }
              },
            },
          }
        },
      }),

      TableCell.extend({
        addAttributes() {
          return {
            ...(this.parent?.() || {}),
            style: {
              default: null,
              parseHTML: (element) => element.getAttribute('style'),
              renderHTML: (attributes) => {
                if (!attributes.style) return {}
                return { style: attributes.style }
              },
            },
          }
        },
      }),

      Image.extend({
        addAttributes() {
          return {
            ...(this.parent?.() || {}),
            width: {
              default: 'auto',
              parseHTML: (element) =>
                element.style.width || element.getAttribute('width') || 'auto',
              renderHTML: (attributes) => {
                if (!attributes.width || attributes.width === 'auto') return {}
                return { style: `width: ${attributes.width};` }
              },
            },
            height: {
              default: 'auto',
              parseHTML: (element) =>
                element.style.height || element.getAttribute('height') || 'auto',
              renderHTML: (attributes) => {
                if (!attributes.height || attributes.height === 'auto') return {}
                return { style: `height: ${attributes.height};` }
              },
            },
          }
        },
      }).configure({ inline: false, allowBase64: true }),

      Link.configure({ openOnClick: false }),
      CharacterCount,
      Placeholder.configure({
        placeholder: "Use ⊞ Insert Table in the toolbar to begin…",
      }),
      TableOnlyEdit,
      TableWidthConstraint,
      MultiCellSelection,
    ],
    content: "",
    immediatelyRender: false,

    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      setWordCount(editor.getText().split(/\s+/).filter(Boolean).length);
      setEditorHtml(html);
      setTableInserted(hasTable(html));

      // ✅ Sync font family from cursor position or first mark
      const { state } = editor;
      const attrs = editor.getAttributes('textStyle');
      if (attrs?.fontFamily) {
        const clean = attrs.fontFamily.replace(/^["']|["']$/g, '').trim();
        setFontFamily(clean);
      } else {
        // fallback: scan doc for first fontFamily mark
        state.doc.descendants((node) => {
          if (node.marks.length) {
            const mark = node.marks.find(m => m.type.name === 'textStyle');
            if (mark?.attrs?.fontFamily) {
              const clean = mark.attrs.fontFamily.replace(/^["']|["']$/g, '').trim();
              setFontFamily(clean);
              return false;
            }
          }
          return true;
        });
      }
    },

    // ✅ Also sync font when cursor moves
    onSelectionUpdate: ({ editor }) => {
      const attrs = editor.getAttributes('textStyle');
      if (attrs?.fontFamily) {
        const clean = attrs.fontFamily.replace(/^["']|["']$/g, '').trim();
        setFontFamily(clean);
      }
    },

  });


  // Load template content or draft on mount/update
  useEffect(() => {
    if (!editor) return;

    const loadContent = async () => {
      setIsLoading(true);

      if (editTempalteData) {
        // First check if there is already a notice_editor_draft in localStorage
        const savedDraft = localStorage.getItem(LS_KEY);
        if (savedDraft) {
          editor.commands.setContent(savedDraft, {
            emitUpdate: false,
            parseOptions: { preserveWhitespace: 'full' },
          });
          setEditorHtml(savedDraft);
          setTableInserted(hasTable(savedDraft));
          setIsLoading(false);
          return;
        }

        if (editTempalteData.html_presigned_url) {
          try {
            // Always fetch via proxy — never fall back to a direct GCS URL fetch.
            // A direct fetch of a private-bucket URL returns an XML AccessDeniedException
            // body that would be treated as valid HTML template content.
            const proxyUrl = `/api/proxy?url=${encodeURIComponent(editTempalteData.html_presigned_url)}`;
            const response = await fetch(proxyUrl);
            if (!response.ok) {
              console.error("Failed to fetch HTML template via proxy:", response.status);
              setIsLoading(false);
              return;
            }

            let htmlData = await response.text();
            // Fix escaped characters
            let cleaned = htmlData
              ?.replace(/\\r\\n/g, "")
              ?.replace(/\\"/g, '"');

            // Extract ONLY body content
            const match = cleaned.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
            const bodyContent = (match && match[1]) ? match[1] : "";

            editor.commands.setContent(bodyContent, {
              emitUpdate: false,
              parseOptions: { preserveWhitespace: 'full' },
            });
            setEditorHtml(bodyContent);
            setTableInserted(hasTable(bodyContent));
          } catch (error) {
            console.error("Failed to load template content:", error);
            message.error("Failed to load template content");
          }
        }
      } else {
        // Create Notice flow: load draft from localStorage
        const saved = localStorage.getItem(LS_KEY);
        if (saved) {
          editor.commands.setContent(saved, {
            emitUpdate: false,
            parseOptions: { preserveWhitespace: 'full' },
          });
          setEditorHtml(saved);
          setTableInserted(hasTable(saved));
        } else {
          editor.commands.setContent("", {
            emitUpdate: false,
          });
          setEditorHtml("");
          setTableInserted(false);
        }
      }

      setIsLoading(false);
    };

    loadContent();
  }, [editor, editTempalteData, trigger]);

  // Auto-save to localStorage every 5 seconds
  useEffect(() => {
    if (!editorHtml || editorHtml === "<p></p>") return;
    const timer = setInterval(() => {
      try {
        localStorage.setItem(LS_KEY, editorHtml);
        setLastSaved(new Date().toLocaleTimeString());
      } catch (_) { /* quota exceeded — ignore */ }
    }, 5000);
    return () => clearInterval(timer);
  }, [editorHtml]);

  // Re-compute A4 page split whenever content changes
  useEffect(() => {
    if (!editorHtml || editorHtml === "<p></p>") {
      setPreviewPages([]);
      return;
    }
    const id = requestAnimationFrame(() => {
      const pages = splitHtmlIntoPages(editorHtml);
      setPreviewPages(pages);
    });
    return () => cancelAnimationFrame(id);
  }, [editorHtml]);

  // ─── Table row vertical drag-to-resize ──────────────────────────────────────
  useEffect(() => {
    if (!editor) return;

    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    let currentDragHeight = 0;
    let targetRow: HTMLTableRowElement | null = null;
    let isInverted = false;
    let lastHoveredCell: HTMLTableCellElement | null = null;
    let activeHandleEl: HTMLDivElement | null = null;

    const BORDER_INSIDE = 5;
    const BORDER_OUTSIDE = 4;

    const editorDom = editor.view.dom as HTMLElement;

    // ── helpers ────────────────────────────────────────────────────────────────
    const checkBorder = (cell: HTMLTableCellElement, clientY: number) => {
      const r = cell.getBoundingClientRect();
      const toTop = clientY - r.top;
      const toBot = r.bottom - clientY;
      if (toBot >= -BORDER_OUTSIDE && toBot <= BORDER_INSIDE) return "bottom";
      if (toTop >= -BORDER_OUTSIDE && toTop <= BORDER_INSIDE) return "top";
      return null;
    };

    /** Scan all cells when mouse is slightly outside any cell */
    const scanCells = (clientX: number, clientY: number): HTMLTableCellElement | null => {
      const cells = editorDom.querySelectorAll("td, th");
      for (let i = 0; i < cells.length; i++) {
        const c = cells[i] as HTMLTableCellElement;
        const r = c.getBoundingClientRect();
        if (clientX >= r.left && clientX <= r.right) {
          const toTop = clientY - r.top;
          const toBot = r.bottom - clientY;
          if (
            (toTop >= -BORDER_OUTSIDE && toTop <= BORDER_INSIDE) ||
            (toBot >= -BORDER_OUTSIDE && toBot <= BORDER_INSIDE)
          ) return c;
        }
      }
      return null;
    };

    /** Show a blue resize-bar indicator on the targeted border */
    const showHandle = (cell: HTMLTableCellElement, edge: "top" | "bottom") => {
      hideHandle();
      const row = cell.closest("tr");
      if (!row) return;
      const bar = document.createElement("div");
      bar.className = `row-resize-handle ${edge} visible`;
      row.style.position = "relative";
      row.appendChild(bar);
      activeHandleEl = bar;
    };

    const hideHandle = () => {
      if (activeHandleEl) {
        activeHandleEl.remove();
        activeHandleEl = null;
      }
    };

    /** Get the max height a row can grow before overflowing the A4 page container */
    const getMaxRowHeight = (row: HTMLTableRowElement): number => {
      return 1000; // Allow rows to grow up to 1000px, safely below the A4 page height limit
    };

    // ── mousemove (hover detection) ───────────────────────────────────────────
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizing) return;

      const target = e.target as HTMLElement;
      if (target.classList.contains("column-resize-handle")) {
        document.body.classList.remove("is-hovering-row-border");
        hideHandle();
        if (lastHoveredCell) { lastHoveredCell.style.cursor = ""; lastHoveredCell = null; }
        return;
      }

      let cell = target.closest("td, th") as HTMLTableCellElement | null;
      if (!cell) cell = scanCells(e.clientX, e.clientY);

      if (!cell) {
        document.body.classList.remove("is-hovering-row-border");
        hideHandle();
        if (lastHoveredCell) { lastHoveredCell.style.cursor = ""; lastHoveredCell = null; }
        return;
      }

      if (lastHoveredCell && lastHoveredCell !== cell) lastHoveredCell.style.cursor = "";
      lastHoveredCell = cell;

      const edge = checkBorder(cell, e.clientY);
      if (edge) {
        cell.style.cursor = "row-resize";
        document.body.classList.add("is-hovering-row-border");
        showHandle(cell, edge);
      } else {
        cell.style.cursor = "";
        document.body.classList.remove("is-hovering-row-border");
        hideHandle();
      }
    };

    const handleMouseLeave = () => {
      document.body.classList.remove("is-hovering-row-border");
      hideHandle();
      if (lastHoveredCell) { lastHoveredCell.style.cursor = ""; lastHoveredCell = null; }
    };

    // ── mousedown (start drag) ────────────────────────────────────────────────
    const handleMouseDown = (e: MouseEvent) => {
      // Only process if event is within the editor
      if (!editorDom.contains(e.target as Node)) return;

      const target = e.target as HTMLElement;
      if (target.classList.contains("column-resize-handle")) return;

      let cell = target.closest("td, th") as HTMLTableCellElement | null;
      if (!cell) cell = scanCells(e.clientX, e.clientY);
      if (!cell) return;

      const edge = checkBorder(cell, e.clientY);
      if (!edge) return;

      const row = cell.closest("tr") as HTMLTableRowElement | null;
      if (!row) return;

      if (edge === "bottom") {
        targetRow = row;
        isInverted = false;
      } else {
        const prevRow = row.previousElementSibling as HTMLTableRowElement | null;
        if (prevRow) { targetRow = prevRow; isInverted = false; }
        else { targetRow = row; isInverted = true; }
      }

      isResizing = true;
      startY = e.clientY;
      startHeight = targetRow.offsetHeight;
      currentDragHeight = startHeight;


      // MUST use stopImmediatePropagation to prevent ProseMirror's table plugin
      // from intercepting and starting its own column resize
      e.preventDefault();
      e.stopImmediatePropagation();

      // Pause ProseMirror's MutationObserver so it doesn't revert our DOM changes
      try { (editor.view as any).domObserver?.stop?.(); } catch (_) { }

      hideHandle();
      document.body.classList.remove("is-hovering-row-border");
      document.body.classList.add("is-resizing-row");

      document.addEventListener("mousemove", handleMouseDrag, true);
      document.addEventListener("mouseup", handleMouseUp, true);
    };

    // ── mousemove (drag) ──────────────────────────────────────────────────────
    const handleMouseDrag = (e: MouseEvent) => {
      if (!isResizing || !targetRow) return;

      const dy = e.clientY - startY;
      const maxH = getMaxRowHeight(targetRow);
      const newHeight = Math.min(maxH, Math.max(30, startHeight + (isInverted ? -dy : dy)));
      currentDragHeight = newHeight;


      const cells = targetRow.querySelectorAll("td, th");
      cells.forEach(c => { (c as HTMLElement).style.height = `${newHeight}px`; });
      targetRow.style.height = `${newHeight}px`;

      e.preventDefault();
      e.stopImmediatePropagation();
    };

    // ── mouseup (finish drag + persist to ProseMirror) ────────────────────────
    const handleMouseUp = (e: MouseEvent) => {
      if (!isResizing || !targetRow || !editor) return;

      isResizing = false;
      document.body.classList.remove("is-resizing-row");


      // Clear temporary inline DOM styles FIRST
      if (targetRow) {
        targetRow.style.height = "";
        targetRow.querySelectorAll("td, th").forEach(c => { (c as HTMLElement).style.height = ""; });
      }

      // Resume ProseMirror's DOM observer BEFORE dispatching transaction
      try { (editor.view as any).domObserver?.start?.(); } catch (_) { }

      // Use the tracked height (not DOM reads, since we cleared inline styles)
      const finalHeight = `${currentDragHeight}px`;
      const hStyle = `height: ${finalHeight}`;

      const view = editor.view;
      try {
        const domPos = view.posAtDOM(targetRow!, 0);
        if (domPos !== undefined) {
          const tr = view.state.tr;
          const $pos = view.state.doc.resolve(domPos);

          let rowNode = null;
          let rowPos = -1;
          for (let d = $pos.depth; d > 0; d--) {
            if ($pos.node(d).type.name === "tableRow") {
              rowNode = $pos.node(d);
              rowPos = $pos.before(d);
              break;
            }
          }

          if (rowNode && rowPos !== -1) {
            let cur = rowPos + 1;
            rowNode.forEach((cellNode) => {
              const old = (cellNode.attrs.style || "").replace(/height\s*:\s*[^;]+;?/gi, "").trim();
              const ns = (old ? old + (old.endsWith(";") ? " " : "; ") : "") + hStyle + ";";
              tr.setNodeMarkup(cur, undefined, { ...cellNode.attrs, style: ns });
              cur += cellNode.nodeSize;
            });

            view.dispatch(tr);
          }
        }
      } catch (err) {
        console.error("[Row Resize] Error dispatching ProseMirror transaction:", err);
      }

      targetRow = null;
      if (lastHoveredCell) lastHoveredCell.style.cursor = "";

      document.removeEventListener("mousemove", handleMouseDrag, true);
      document.removeEventListener("mouseup", handleMouseUp, true);

      e.preventDefault();
      e.stopImmediatePropagation();
    };

    // ── attach listeners ──────────────────────────────────────────────────────
    // Register capture-phase handlers on document and editorDom to guarantee
    // they execute BEFORE ProseMirror's internal event handlers.
    editorDom.addEventListener("mousemove", handleMouseMove, true);
    document.addEventListener("mousedown", handleMouseDown, true);
    editorDom.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      editorDom.removeEventListener("mousemove", handleMouseMove, true);
      document.removeEventListener("mousedown", handleMouseDown, true);
      editorDom.removeEventListener("mouseleave", handleMouseLeave);
      document.removeEventListener("mousemove", handleMouseDrag, true);
      document.removeEventListener("mouseup", handleMouseUp, true);
      hideHandle();
      document.body.classList.remove("is-resizing-row", "is-hovering-row-border");
    };
  }, [editor]);


  // Handle Create Notice modal submission
  const handleCreateModalSubmit = useCallback(async (values: CreateNoticeFormValues) => {
    // Get the latest HTML directly from the editor to avoid stale state
    const currentHtml = editor?.getHTML() || "";

    if (!currentHtml || currentHtml === "<p></p>") {
      // console.warn("Editor is empty, cannot create notice");
      return;
    }

    const html = `<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <title>Notice_${new Date().toISOString().slice(0, 10)}</title>
        <style>
          @page { size: A4; margin: 10mm 10mm; }
          body {
            font-family: 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #111;
            max-width: 210mm;
            margin: 0 auto;
            padding: 10mm 10mm;
            background: #fff;
          }
          table { border-collapse: collapse; width: 100%; margin: 6px 0; table-layout: fixed; }
          th, td {
            border: 1px solid #000000;
            padding: 3px 5px;
            vertical-align: top;
            background: transparent;
            font-weight: normal;
            box-sizing: border-box !important;
          }
          table p { margin: 0; }
          p { margin: 0 0 8px; }
          h1 { font-size: 20pt; font-weight: bold; margin: 16px 0 8px; }
          h2 { font-size: 16pt; font-weight: bold; margin: 14px 0 6px; }
          h3 { font-size: 13pt; font-weight: bold; margin: 12px 0 4px; }
          ul, ol { padding-left: 24px; margin: 4px 0; }
          li { margin-bottom: 4px; }
          strong { font-weight: bold; }
          em { font-style: italic; }
          u { text-decoration: underline; }
          s { text-decoration: line-through; }
          mark { background: #fde68a; padding: 0 2px; border-radius: 2px; }
          a { color: #1a56db; text-decoration: underline; }
          blockquote {
            border-left: 3px solid #2b579a;
            margin: 8px 0;
            padding-left: 12px;
            color: #555;
            font-style: italic;
          }
          hr { border: none; border-top: 1px solid #999; margin: 12px 0; }
          img { max-width: 100%; height: auto; }
          [style*="text-align: left"]    { text-align: left; }
          [style*="text-align: center"]  { text-align: center; }
          [style*="text-align: right"]   { text-align: right; }
          [style*="text-align: justify"] { text-align: justify; }
          @media print {
            body { padding: 0; }
            table { page-break-inside: avoid; }
          }
        </style>
      </head>
        <header>
        <p>
        <img src=${values.headerImageUrl} alt="Header" style="width:809px; height:119px" />
        </p>
        </header>
      <body style="padding:0px">${currentHtml}</body> 
      <footer>
      <p style="margin:0 0 6px 0; white-space:pre-wrap; text-align:center">
        <img src=${values?.footerImageUrl} alt="Footer" style="width:69px; height:57px" />
      </p>  
      </footer>
          </html>`;

    // ✅ Create FormData
    const formData = new FormData();

    formData.append("template_string", html);
    formData.append("client_name", values?.clientName || "");
    formData.append("client_code", values?.clientCode || "");
    formData.append("template_type", values?.templateType || "");
    formData.append("header_image_name", values?.headerImgName || "");
    formData.append("footer_image_name", values?.footerImgName || "");

    if (editTempalteData) {
      try {
        let response: any = await BankApi.masterPutTemplate(editTempalteData?.id, formData);
        localStorage.removeItem(LS_KEY);
        setEditorHtml("")
        setTrigger(trigger + 1)
        setActiveTab("Notice details")
        setShowCreateModal(false);
        setEditTempalteData("")
        messageApi.success("Notice template Updated successfully.");
      } catch (error) { }

    } else {
      try {
        let response: any = await BankApi.masterPostTemplate(formData);
        localStorage.removeItem(LS_KEY);
        setEditorHtml("")
        setTrigger(trigger + 1)
        setActiveTab("Notice details")
        setShowCreateModal(false);
        messageApi.success("Notice template created successfully.");
      } catch (error) { }

    }

  }, [editor]);

  // Save Notice → download as PDF or Word
  const handleSaveNotice = useCallback(
    async (type: "pdf" | "word") => {
      if (!editorHtml || !tableInserted) return;

      setIsSaving(true);
      setSaveStatus("saving");

      try {
        if (type === "word") {
          const htmlContent = `<!DOCTYPE html>
            <html>
            <head>
              <meta charset="UTF-8">
              <style>
                body { font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #999; padding: 3px 5px; }
                table p { margin: 0; }
              </style>
            </head>
            <body>${editorHtml}</body>
            </html>`;
          const blob = await htmlDocx.asBlob(htmlContent);
          saveAs(blob as unknown as Blob, "document.docx");
        }

        if (type === "pdf") {
          const opt = {
            margin: [0.5, 0.5] as [number, number],
            filename: "document.pdf",
            image: { type: "jpeg" as const, quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { unit: "in", format: "a4", orientation: "portrait" as const },
          };
          const element = document.createElement("div");
          element.innerHTML = editorHtml;
          await html2pdf().set(opt).from(element).save();
        }
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 3000);
      } catch (err) {
        console.error("Download failed:", err);
        setSaveStatus("error");
        setTimeout(() => setSaveStatus("idle"), 3000);
      } finally {
        setIsSaving(false);
      }
    },
    [editorHtml, tableInserted]
  );

  const handleDownload = useCallback(() => {
    if (!editorHtml) return;
    setShowCreateModal(true);
  }, [editorHtml]);


  // ─── FONT-FAMILY FIX ──────────────────────────────────────────────────────────

  const handleFontFamily = useCallback((val: string) => {
    setFontFamily(val);
    if (!editor) return;
    editor.chain().focus().setMark('textStyle', { fontFamily: val }).run();
  }, [editor]);

  const handleFontSize = useCallback((val: string) => {
    setFontSize(val);
    editor?.chain().focus().setMark("textStyle", { fontSize: val }).run();
  }, [editor]);

  // Insert table
  const insertTable = (rows: number, cols: number) => {
    editor?.chain().focus().insertTable({ rows, cols, withHeaderRow: true }).run();
    setShowTableMenu(false);
  };

  // Insert image
  const handleImageInsert = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      editor?.chain().focus().setImage({ src: reader.result as string }).run();
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const handleImageClick = useCallback((e: React.MouseEvent<HTMLImageElement>) => {
    e.stopPropagation();
    const img = e.currentTarget;
    setSelectedImage(img);
  }, []);

  const handleResizeStart = useCallback((e: React.MouseEvent, direction: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!selectedImage) return;

    const img = selectedImage;
    const rect = img.getBoundingClientRect();

    resizeData.current = {
      img,
      direction,
      startX: e.clientX,
      startY: e.clientY,
      startWidth: rect.width,
      startHeight: rect.height,
    };
    setIsResizing(true);
  }, [selectedImage]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!resizeData.current || !editor) return;

    const { img, direction, startX, startY, startWidth, startHeight } = resizeData.current;
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;

    let newWidth = startWidth;
    let newHeight = startHeight;

    if (direction.includes('e')) {
      newWidth = Math.max(50, startWidth + deltaX);
    } else if (direction.includes('w')) {
      newWidth = Math.max(50, startWidth - deltaX);
    }

    if (direction.includes('s')) {
      newHeight = Math.max(30, startHeight + deltaY);
    } else if (direction.includes('n')) {
      newHeight = Math.max(30, startHeight - deltaY);
    }

    img.style.width = `${newWidth}px`;
    img.style.height = `${newHeight}px`;

    const view = editor.view;
    const { from, to } = view.state.selection;
    const tr = view.state.tr;

    view.state.doc.nodesBetween(from, to, (node, pos) => {
      if (node.type.name === 'image') {
        tr.setNodeMarkup(pos, undefined, {
          ...node.attrs,
          width: `${newWidth}px`,
          height: `${newHeight}px`
        });
        return false;
      }
      return true;
    });

    view.dispatch(tr);
  }, [editor]);

  const handleResizeEnd = useCallback(() => {
    resizeData.current = null;
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      window.addEventListener('mousemove', handleResizeMove);
      window.addEventListener('mouseup', handleResizeEnd);
      return () => {
        window.removeEventListener('mousemove', handleResizeMove);
        window.removeEventListener('mouseup', handleResizeEnd);
      };
    }
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName !== 'IMG' && !target.closest('.resize-handle')) {
        setSelectedImage(null);
      }
    };

    if (selectedImage) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [selectedImage]);

  const [pendingBorderStyle, setPendingBorderStyle] = useState<{
    style: "all" | "none" | "outer" | "notop" | "nobottom" | "noleft" | "noright";
    custom?: { top: boolean; bottom: boolean; left: boolean; right: boolean; innerH: boolean; innerV: boolean };
  } | null>(null);

  const applyBorderStyle = (style: "all" | "none" | "outer" | "notop" | "nobottom" | "noleft" | "noright") => {
    setCurrentBorderStyle(style);
    const customConfigs: Record<string, { top: boolean; bottom: boolean; left: boolean; right: boolean; innerH: boolean; innerV: boolean }> = {
      all: { top: true, bottom: true, left: true, right: true, innerH: true, innerV: true },
      none: { top: false, bottom: false, left: false, right: false, innerH: false, innerV: false },
      outer: { top: true, bottom: true, left: true, right: true, innerH: false, innerV: false },
      notop: { top: false, bottom: true, left: true, right: true, innerH: true, innerV: true },
      nobottom: { top: true, bottom: false, left: true, right: true, innerH: true, innerV: true },
      noleft: { top: true, bottom: true, left: false, right: true, innerH: true, innerV: true },
      noright: { top: true, bottom: true, left: true, right: false, innerH: true, innerV: true },
    };
    setPendingBorderStyle({ style, custom: customConfigs[style] });
  };

  const applyToSelection = () => {
    if (!pendingBorderStyle || !editor) return;

    const { style, custom } = pendingBorderStyle;

    let borderCSS = "";
    switch (style) {
      case "none":
        borderCSS = "border: none;";
        break;
      case "outer":
        borderCSS = "border: 1px solid #999;";
        break;
      case "all":
      default:
        borderCSS = "border: 1px solid #999;";
        break;
    }

    if (custom) {
      const sides = [];
      if (custom.top) sides.push(`border-top: ${currentBorderWidth}px solid #999`);
      else sides.push("border-top: none");
      if (custom.bottom) sides.push(`border-bottom: ${currentBorderWidth}px solid #999`);
      else sides.push("border-bottom: none");
      if (custom.left) sides.push(`border-left: ${currentBorderWidth}px solid #999`);
      else sides.push("border-left: none");
      if (custom.right) sides.push(`border-right: ${currentBorderWidth}px solid #999`);
      else sides.push("border-right: none");
      borderCSS = sides.join("; ") + ";";
    }

    const view = editor.view;
    const selection = view.state.selection;
    const doc = view.state.doc;

    const cellsToModify: number[] = [];

    // Handle CellSelection (multi-cell selection via mouse drag or Ctrl+click)
    if (selection instanceof CellSelection) {
      selection.forEachCell((node, pos) => {
        cellsToModify.push(pos);
      });
    } else {
      // Handle regular TextSelection — find enclosing cell(s)
      const { from, to } = selection;
      doc.nodesBetween(from, to, (node, pos) => {
        if (node.type.name === "tableCell" || node.type.name === "tableHeader") {
          cellsToModify.push(pos);
          return false;
        }
        return true;
      });
    }

    if (cellsToModify.length === 0) {
      setPendingBorderStyle(null);
      return;
    }

    const tr = view.state.tr;
    cellsToModify.forEach((pos) => {
      const node = doc.nodeAt(pos);
      if (node) {
        const attrs = { ...node.attrs, style: borderCSS };
        tr.setNodeMarkup(pos, undefined, attrs);
      }
    });

    if (selection instanceof CellSelection) {
      const anchorCellPos = selection.$anchorCell.pos;
      const resolved = tr.doc.resolve(anchorCellPos + 1);
      tr.setSelection(TextSelection.near(resolved));
    }

    view.dispatch(tr);
    setPendingBorderStyle(null);
    setCurrentBorderStyle("");
  };

  const applyToAllCells = () => {
    if (!pendingBorderStyle || !editor) return;

    const { style, custom } = pendingBorderStyle;

    let borderCSS = "";
    switch (style) {
      case "none":
        borderCSS = "border: none;";
        break;
      case "outer":
        borderCSS = "border: 1px solid #999;";
        break;
      case "all":
      default:
        borderCSS = "border: 1px solid #999;";
        break;
    }

    if (custom) {
      const sides = [];
      if (custom.top) sides.push(`border-top: ${currentBorderWidth}px solid #999`);
      else sides.push("border-top: none");
      if (custom.bottom) sides.push(`border-bottom: ${currentBorderWidth}px solid #999`);
      else sides.push("border-bottom: none");
      if (custom.left) sides.push(`border-left: ${currentBorderWidth}px solid #999`);
      else sides.push("border-left: none");
      if (custom.right) sides.push(`border-right: ${currentBorderWidth}px solid #999`);
      else sides.push("border-right: none");
      borderCSS = sides.join("; ") + ";";
    }

    const html = editor.getHTML();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const tables = doc.querySelectorAll("table");

    tables.forEach((table) => {
      const cells = table.querySelectorAll("td, th");
      cells.forEach((cell) => {
        cell.setAttribute("style", borderCSS);
      });
    });

    editor.commands.setContent(doc.body.innerHTML);
    setPendingBorderStyle(null);
    setCurrentBorderStyle("");
  };

  const applyCellBgColor = (color: string) => {
    setCurrentCellBg(color);
    setPendingCellBg(color);
  };

  const applyCellBgToSelection = () => {
    if (pendingCellBg === null || !editor) return;

    const view = editor.view;
    const selection = view.state.selection;
    const doc = view.state.doc;

    const cellsToModify: number[] = [];

    if (selection instanceof CellSelection) {
      selection.forEachCell((node, pos) => {
        cellsToModify.push(pos);
      });
    } else {
      const { from, to } = selection;
      doc.nodesBetween(from, to, (node, pos) => {
        if (node.type.name === "tableCell" || node.type.name === "tableHeader") {
          cellsToModify.push(pos);
          return false;
        }
        return true;
      });
    }

    if (cellsToModify.length === 0) {
      setPendingCellBg(null);
      return;
    }

    const tr = view.state.tr;
    cellsToModify.forEach((pos) => {
      const node = doc.nodeAt(pos);
      if (node) {
        const currentStyle = node.attrs.style || "";
        const updatedStyle = updateStyleString(currentStyle, "background-color", pendingCellBg);
        const attrs = { ...node.attrs, style: updatedStyle };
        tr.setNodeMarkup(pos, undefined, attrs);
      }
    });

    if (selection instanceof CellSelection) {
      const anchorCellPos = selection.$anchorCell.pos;
      const resolved = tr.doc.resolve(anchorCellPos + 1);
      tr.setSelection(TextSelection.near(resolved));
    }

    view.dispatch(tr);
    setPendingCellBg(null);
    setCurrentCellBg("");
  };

  const applyCellBgToAllCells = () => {
    if (pendingCellBg === null || !editor) return;

    const html = editor.getHTML();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const tables = doc.querySelectorAll("table");

    tables.forEach((table) => {
      const cells = table.querySelectorAll("td, th");
      cells.forEach((cell) => {
        const currentStyle = cell.getAttribute("style") || "";
        const updatedStyle = updateStyleString(currentStyle, "background-color", pendingCellBg);
        cell.setAttribute("style", updatedStyle);
      });
    });

    editor.commands.setContent(doc.body.innerHTML);
    setPendingCellBg(null);
    setCurrentCellBg("");
  };

  if (!editor) return null;

  // Show Ant Design table-style loading spinner on initial page load
  if (isLoading) {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        background: "#f0f2f5",
      }}>
        <Spin
          size="large"
          tip="Loading editor..."
          style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
        />
      </div>
    );
  }


  const tb = tableInserted;
  const canUndo = editor.can().undo();
  const canRedo = editor.can().redo();


  interface FontFamilyPickerProps {
    fontFamily: string;
    disabled?: boolean;
    onChange: (font: string) => void;
  }



  const handleBack = () => {
    setActiveTab("Notice details");
    if (editTempalteData) {
      setEditTempalteData("");
      localStorage.removeItem("notice_editor_draft");
    }
  }



  return (
    <>
      {contextHolder}
      <div
        id="editor-wrapper"
        style={{
          position: "fixed",
          top: 70,
          left: 35,
          right: 35,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          background: "#f0f2f5",
          fontFamily: "Segoe UI, sans-serif",
          overflow: "hidden",
          overscrollBehavior: "contain",
          zIndex: 90
        }}>

        {/* ── Top bar ──────────────────────────────────────────────────────── */}
        <div style={{
          background: "#2b579a", color: "#fff", padding: "8px 16px", fontSize: 13,
          fontWeight: 600, display: "flex", alignItems: "center",
          gap: 12, userSelect: "none", flexShrink: 0,
        }}>
          <button
            onClick={() => handleBack()}
            style={{
              background: "transparent",
              border: "none",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "4px 8px",
              borderRadius: 4,
              transition: "background 0.2s",
            }}
            onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.15)"}
            onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.background = "transparent"}
            title="Go Back"
          >
            <IoMdArrowRoundBack size={20} />
          </button>
          <span style={{ fontSize: 18 }}>📝</span>
          <span>Notice Editor</span>
          {lastSaved && (
            <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 4 }}>
              · Draft auto-saved at {lastSaved}
            </span>
          )}
          <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 4 }}>
            · {wordCount} words
          </span>

          {/* Action buttons on the right */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            {/* Download Notice */}
            <div style={{ position: "relative" }}>
              <button
                onClick={() => setShowDownloadPopup(v => !v)}
                disabled={!tableInserted || isSaving}
                style={{
                  padding: "6px 16px", borderRadius: 6, border: "1px solid #fff", fontSize: 12, fontWeight: 600,
                  cursor: (!tableInserted || isSaving) ? "not-allowed" : "pointer",
                  background: "transparent",
                  color: "#fff",
                  display: "flex", alignItems: "center", gap: 6,
                  opacity: (!tableInserted || isSaving) ? 0.6 : 1,
                  transition: "background .2s",
                }}
                onMouseEnter={e => {
                  if (tableInserted && !isSaving)
                    (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.15)";
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                }}
              >
                {saveStatus === "saving" ? "⏳ Saving…"
                  : saveStatus === "saved" ? "✅ Saved!"
                    : saveStatus === "error" ? "❌ Failed"
                      : "💾 Download Notice"}
              </button>

              {showDownloadPopup && (
                <>
                  <div
                    style={{
                      position: "fixed",
                      top: 0, left: 0, right: 0, bottom: 0,
                      zIndex: 998,
                    }}
                    onClick={() => setShowDownloadPopup(false)}
                  />
                  <div
                    style={{
                      position: "absolute",
                      top: "calc(100% + 8px)",
                      right: 0,
                      zIndex: 999,
                      background: "#fff",
                      border: "1px solid #d1d5db",
                      borderRadius: 8,
                      boxShadow: "0 8px 32px rgba(0,0,0,.15)",
                      padding: 8,
                      minWidth: 200,
                      color: "#374151",
                    }}
                  >
                    <p style={{ margin: "0 0 6px", fontSize: 11, color: "#6b7280", fontWeight: 600, padding: "4px 8px" }}>
                      Download as
                    </p>
                    <button
                      onClick={() => { handleSaveNotice("word"); setShowDownloadPopup(false); }}
                      disabled={isSaving}
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        border: "none",
                        borderRadius: 6,
                        background: "#f0f9ff",
                        color: "#1a56db",
                        fontSize: 13,
                        fontWeight: 500,
                        cursor: isSaving ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        transition: "background .15s",
                        opacity: isSaving ? 0.5 : 1,
                      }}
                      onMouseEnter={e => { if (!isSaving) (e.currentTarget as HTMLButtonElement).style.background = "#e0f2fe"; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "#f0f9ff"; }}
                    >
                      <span style={{ fontSize: 16 }}>📄</span>
                      <span>Word (.docx)</span>
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* Create/Update Notice */}
            <button
              onClick={handleDownload}
              disabled={!tableInserted}
              style={{
                padding: "6px 16px", borderRadius: 6,
                border: "none", fontSize: 12, fontWeight: 600,
                cursor: !tableInserted ? "not-allowed" : "pointer",
                background: !tableInserted ? "rgba(255,255,255,0.3)" : "#fff",
                color: !tableInserted ? "rgba(255,255,255,0.6)" : "#2b579a",
                display: "flex", alignItems: "center", gap: 6,
                transition: "background .15s, color .15s",
              }}
              onMouseEnter={e => {
                if (tableInserted) {
                  (e.currentTarget as HTMLButtonElement).style.background = "#f0f9ff";
                }
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  tableInserted ? "#fff" : "rgba(255,255,255,0.3)";
              }}
            >
              {editTempalteData ? "Update Notice" : "Create Notice"}
            </button>
          </div>
        </div>

        {/* ── Ribbon toolbar ───────────────────────────────────────────────── */}
        <div style={{
          background: "#fff", borderBottom: "1px solid #d1d5db", padding: "6px 12px",
          display: "flex", flexWrap: "wrap", gap: 2, alignItems: "center",
          flexShrink: 0, boxShadow: "0 1px 4px rgba(0,0,0,.07)",
        }}>

          {/* Undo / Redo */}
          <ToolBtn disabled={!tb || !canUndo} title="Undo (Ctrl+Z)"
            onClick={() => editor.chain().focus().undo().run()}>↩</ToolBtn>
          <ToolBtn disabled={!tb || !canRedo} title="Redo (Ctrl+Y)"
            onClick={() => editor.chain().focus().redo().run()}>↪</ToolBtn>
          <Divider />

          {/* Font family */}
          {/* <select value={fontFamily} disabled={!tb}
            onChange={(e) => handleFontFamily(e.target.value)}
            style={{
              height: 26, fontSize: 12, border: "1px solid #d1d5db", borderRadius: 4,
              padding: "0 6px", background: "#fff", width: 140,
              cursor: tb ? "pointer" : "not-allowed", opacity: tb ? 1 : 0.38,
              fontFamily: fontFamily,
            }}>
            {FONT_GROUPS.map(group => (
              <optgroup key={group.label} label={group.label}>
                {group.fonts.map(font => (
                  <option key={font} value={font} style={{ fontFamily: font}}>
                      {font}
                  </option>
                ))}
              </optgroup>
            ))}
          </select> */}
          <FontFamilyPicker
            fontFamily={fontFamily}
            disabled={!tb}
            onChange={handleFontFamily}
          />
          {/* Font size */}
          <select value={fontSize} disabled={!tb}
            onChange={(e) => handleFontSize(e.target.value)}
            style={{
              height: 26, fontSize: 12, border: "1px solid #d1d5db", borderRadius: 4,
              padding: "0 6px", background: "#fff", width: 56,
              cursor: tb ? "pointer" : "not-allowed", opacity: tb ? 1 : 0.38,
            }}>
            {[8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72].map(s =>
              <option key={s} value={String(s)}>{s}</option>)}
          </select>
          <Divider />

          {/* Heading style */}
          <select disabled={!tb}
            value={
              editor.isActive("heading", { level: 1 }) ? "1" :
                editor.isActive("heading", { level: 2 }) ? "2" :
                  editor.isActive("heading", { level: 3 }) ? "3" : "p"
            }
            onChange={(e) => {
              const val = e.target.value;
              if (val === "p") editor.chain().focus().setParagraph().run();
              else editor.chain().focus().toggleHeading({ level: parseInt(val) as 1 | 2 | 3 | 4 | 5 | 6 }).run();
            }}
            style={{
              height: 26, fontSize: 12, border: "1px solid #d1d5db", borderRadius: 4,
              padding: "0 6px", background: "#fff", width: 100,
              cursor: tb ? "pointer" : "not-allowed", opacity: tb ? 1 : 0.38,
            }}>
            <option value="p">Normal</option>
            <option value="1">Heading 1</option>
            <option value="2">Heading 2</option>
            <option value="3">Heading 3</option>
          </select>
          <Divider />

          {/* Bold / Italic / Underline / Strike */}
          <ToolBtn disabled={!tb} active={editor.isActive("bold")}
            onClick={() => editor.chain().focus().toggleBold().run()} title="Bold (Ctrl+B)">
            <strong>B</strong>
          </ToolBtn>
          <ToolBtn disabled={!tb} active={editor.isActive("italic")}
            onClick={() => editor.chain().focus().toggleItalic().run()} title="Italic (Ctrl+I)">
            <em>I</em>
          </ToolBtn>
          <ToolBtn disabled={!tb} active={editor.isActive("underline")}
            onClick={() => editor.chain().focus().toggleUnderline().run()} title="Underline (Ctrl+U)">
            <u>U</u>
          </ToolBtn>
          <ToolBtn disabled={!tb} active={editor.isActive("strike")}
            onClick={() => editor.chain().focus().toggleStrike().run()} title="Strikethrough">
            <s>S</s>
          </ToolBtn>
          <Divider />

          {/* Highlight */}
          <ToolBtn disabled={!tb} active={editor.isActive("highlight")}
            onClick={() => editor.chain().focus().toggleHighlight({ color: "#fde68a" }).run()}
            title="Highlight">
            <span style={{ background: "#fde68a", padding: "0 3px" }}>H</span>
          </ToolBtn>

          {/* Text color */}
          <ToolBtn
            disabled={!tb}
            active={editor.isActive("textStyle")}
            title="Text Color"
            onClick={() => { }}
          >
            <input
              type="color"
              value={editor.getAttributes("textStyle").color || "#000000"}
              disabled={!tb}
              onChange={(e) =>
                editor.chain().focus().setColor(e.target.value).run()
              }
              style={{
                width: 28,
                height: 28,
                border: "1px solid #d1d5db",
                borderRadius: 4,
                cursor: tb ? "pointer" : "not-allowed",
                padding: 2,
                opacity: tb ? 1 : 0.38,
                background: "transparent",
              }}
            />
          </ToolBtn>

          {/* <input type="color" defaultValue="#000000" disabled={!tb}
            title="Text Color"
            onChange={(e) => editor?.chain().focus().setColor(e.target.value).run()}
            style={{
              width: 28, height: 28, border: "1px solid #d1d5db", borderRadius: 4,
              cursor: tb ? "pointer" : "not-allowed", padding: 2, opacity: tb ? 1 : 0.38,
            }} /> */}
          <Divider />

          {/* Alignment */}
          {([
            { align: "left", icon: "⬅", label: "Align Left" },
            { align: "center", icon: "↔", label: "Center" },
            { align: "right", icon: "➡", label: "Align Right" },
            { align: "justify", icon: "⇔", label: "Justify" },
          ] as const).map(({ align, icon, label }) => (
            <ToolBtn key={align} disabled={!tb}
              active={editor.isActive({ textAlign: align })}
              onClick={() => editor.chain().focus().setTextAlign(align).run()}
              title={label}>
              <span style={{ fontSize: 14 }}>{icon}</span>
            </ToolBtn>
          ))}
          <Divider />

          {/* Lists */}
          <ToolBtn disabled={!tb} active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()} title="Bullet List">
            •≡
          </ToolBtn>
          <ToolBtn disabled={!tb} active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()} title="Numbered List">
            1≡
          </ToolBtn>
          <Divider />

          {/* Indent */}
          <ToolBtn disabled={!tb || !editor.can().sinkListItem("listItem")}
            onClick={() => editor.chain().focus().sinkListItem("listItem").run()}
            title="Increase Indent">→|</ToolBtn>
          <ToolBtn disabled={!tb || !editor.can().liftListItem("listItem")}
            onClick={() => editor.chain().focus().liftListItem("listItem").run()}
            title="Decrease Indent">|←</ToolBtn>
          <Divider />

          {/* Insert Table — ALWAYS enabled */}
          <div style={{ position: "relative" }}>
            <ToolBtn onClick={() => setShowTableMenu(v => !v)} title="Insert Table">
              {/* ⊞ */}
              <AiOutlineTable size={18} />
            </ToolBtn>
            {showTableMenu && (
              <div
                style={{
                  position: "absolute", top: 32, left: 0, zIndex: 999,
                  background: "#fff", border: "1px solid #d1d5db", borderRadius: 6,
                  boxShadow: "0 4px 16px rgba(0,0,0,.12)", padding: 10,
                }}
                onMouseLeave={() => {
                  setShowTableMenu(false);
                  setHoveredTableGrid(null);
                }}
              >
                <p style={{ margin: "0 0 6px", fontSize: 11, color: "#6b7280", fontWeight: 600 }}>
                  Insert Table
                </p>
                <div 
                  style={{ display: "grid", gridTemplateColumns: "repeat(6, 22px)", gap: 2 }}
                  onMouseLeave={() => setHoveredTableGrid(null)}
                >
                  {Array.from({ length: 36 }).map((_, i) => {
                    const row = Math.floor(i / 6) + 1;
                    const col = (i % 6) + 1;
                    const isHighlighted = hoveredTableGrid
                      ? row <= hoveredTableGrid.row && col <= hoveredTableGrid.col
                      : false;
                    return (
                      <div key={i} onClick={() => insertTable(row, col)} title={`${row}×${col}`}
                        style={{
                          width: 22, height: 22, border: "1px solid #e5e7eb", borderRadius: 3,
                          cursor: "pointer", 
                          background: isHighlighted ? "#bfdbfe" : "#f9fafb", 
                          transition: "background .1s",
                        }}
                        onMouseEnter={() => setHoveredTableGrid({ row, col })}
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Table row/col controls */}
          {tb && editor.isActive("table") && (<>
            <ToolBtn onClick={() => editor.chain().focus().addRowAfter().run()} title="Add Row">+R</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().addColumnAfter().run()} title="Add Col">+C</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().deleteRow().run()} title="Delete Row">–R</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().deleteColumn().run()} title="Delete Col">–C</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().deleteTable().run()} title="Delete Table">🗑</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().mergeCells().run()} title="Merge Cells">⊕</ToolBtn>
            <ToolBtn onClick={() => editor.chain().focus().splitCell().run()} title="Split Cell">⊖</ToolBtn>
          </>)}

          {/* Border controls dropdown */}
          {tb && (
            <div style={{ position: "relative" }}>
              <ToolBtn
                active={showBorderMenu}
                onClick={() => setShowBorderMenu(v => !v)}
                title="Border Options"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ display: "block" }}>
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18M3 15h18M9 3v18M15 3v18" strokeDasharray="2 3" strokeWidth="1.5" />
                </svg>
              </ToolBtn>
              {showBorderMenu && (
                <>
                  <div
                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 998 }}
                    onClick={() => setShowBorderMenu(false)}
                  />
                  <div
                    style={{
                      position: "absolute", top: 32, left: 0, zIndex: 999,
                      background: "#fff", border: "1px solid #d1d5db", borderRadius: 6,
                      boxShadow: "0 4px 16px rgba(0,0,0,.12)", padding: 8, minWidth: 180,
                    }}
                  >
                    <p style={{ margin: "0 0 6px", fontSize: 10, color: "#6b7280", fontWeight: 600, textTransform: "uppercase" }}>
                      Borders
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4, marginBottom: 8 }}>
                      <button
                        onClick={() => { applyBorderStyle("all"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "all" ? "2px solid #1a56db" : "1px solid #d1d5db",
                          borderRadius: 4, background: currentBorderStyle === "all" ? "#ebf0ff" : "#fff",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="All Borders"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><rect x="2" y="2" width="20" height="16" fill="none" stroke="#374151" strokeWidth="1.5" /><line x1="2" y1="10" x2="22" y2="10" stroke="#374151" strokeWidth="1" /><line x1="12" y1="2" x2="12" y2="18" stroke="#374151" strokeWidth="1" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("none"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "none" ? "2px solid #1a56db" : "1px solid #d1d5db",
                          borderRadius: 4, background: currentBorderStyle === "none" ? "#ebf0ff" : "#fff",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="No Borders"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><rect x="2" y="2" width="20" height="16" fill="none" stroke="#d1d5db" strokeWidth="1" strokeDasharray="3,2" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("outer"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "outer" ? "2px solid #1a56db" : "1px solid #d1d5db",
                          borderRadius: 4, background: currentBorderStyle === "outer" ? "#ebf0ff" : "#fff",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="Outer Borders"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><rect x="2" y="2" width="20" height="16" fill="none" stroke="#374151" strokeWidth="2" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("notop"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "notop" ? "2px solid #1a56db" : "1px solid #d1d5db",
                          borderRadius: 4, background: currentBorderStyle === "notop" ? "#ebf0ff" : "#fff",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="No Top Border"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><path d="M2 10 L22 10 M12 2 L12 18 M2 18 L22 18" fill="none" stroke="#374151" strokeWidth="1.5" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("nobottom"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "nobottom" ? "2px solid #1a56db" : "1px solid #d1d5db", borderRadius: 4,
                          background: currentBorderStyle === "nobottom" ? "#ebf0ff" : "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="No Bottom Border"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><path d="M2 2 L22 2 M12 2 L12 18 M2 10 L22 10" fill="none" stroke="#374151" strokeWidth="1.5" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("noleft"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "noleft" ? "2px solid #1a56db" : "1px solid #d1d5db", borderRadius: 4,
                          background: currentBorderStyle === "noleft" ? "#ebf0ff" : "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="No Left Border"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><path d="M2 2 L22 2 M22 2 L22 18 M2 18 L22 18 M12 2 L12 18" fill="none" stroke="#374151" strokeWidth="1.5" /></svg>
                      </button>
                      <button
                        onClick={() => { applyBorderStyle("noright"); }}
                        style={{
                          width: 48, height: 40, border: currentBorderStyle === "noright" ? "2px solid #1a56db" : "1px solid #d1d5db", borderRadius: 4,
                          background: currentBorderStyle === "noright" ? "#ebf0ff" : "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                        title="No Right Border"
                      >
                        <svg width="24" height="20" viewBox="0 0 24 20"><path d="M2 2 L22 2 M2 2 L2 18 M2 18 L22 18 M12 2 L12 18" fill="none" stroke="#374151" strokeWidth="1.5" /></svg>
                      </button>
                    </div>

                    <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 6 }}>
                      <p style={{ margin: "0 0 4px", fontSize: 10, color: "#6b7280", fontWeight: 600 }}>Apply to</p>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          onClick={() => { applyToSelection(); setShowBorderMenu(false); }}
                          disabled={!pendingBorderStyle}
                          style={{
                            flex: 1, padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: 4,
                            background: !pendingBorderStyle ? "#f3f4f6" : "#fff",
                            color: !pendingBorderStyle ? "#9ca3af" : "#374151",
                            fontSize: 11,
                            cursor: !pendingBorderStyle ? "not-allowed" : "pointer",
                          }}
                        >
                          Selected Cells
                        </button>
                        <button
                          onClick={() => { applyToAllCells(); setShowBorderMenu(false); }}
                          disabled={!pendingBorderStyle}
                          style={{
                            flex: 1, padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: 4,
                            background: !pendingBorderStyle ? "#f3f4f6" : "#fff",
                            color: !pendingBorderStyle ? "#9ca3af" : "#374151",
                            fontSize: 11,
                            cursor: !pendingBorderStyle ? "not-allowed" : "pointer",
                          }}
                        >
                          Entire Table
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Cell background controls dropdown */}
          {tb && (
            <div style={{ position: "relative" }}>
              <ToolBtn
                active={showCellBgMenu}
                onClick={() => setShowCellBgMenu(v => !v)}
                title="Cell Background Color"
              >
                {/* 🎨 */}
                <IoColorPaletteOutline size={18} />
              </ToolBtn>
              {showCellBgMenu && (
                <>
                  <div
                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 998 }}
                    onClick={() => setShowCellBgMenu(false)}
                  />
                  <div
                    style={{
                      position: "absolute", top: 32, left: 0, zIndex: 999,
                      background: "#fff", border: "1px solid #d1d5db", borderRadius: 6,
                      boxShadow: "0 4px 16px rgba(0,0,0,.12)", padding: 8, minWidth: 180,
                    }}
                  >
                    <p style={{ margin: "0 0 6px", fontSize: 10, color: "#6b7280", fontWeight: 600, textTransform: "uppercase" }}>
                      Cell Background
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 4, marginBottom: 8 }}>
                      {[
                        { color: "", label: "None", border: "1px solid #e5e7eb", bg: "#ffffff" },
                        { color: "#d1d5db", label: "Gray", border: "none", bg: "#d1d5db" },
                        { color: "#93c5fd", label: "Blue", border: "none", bg: "#93c5fd" },
                        { color: "#fca5a5", label: "Red", border: "none", bg: "#fca5a5" },
                        { color: "#86efac", label: "Green", border: "none", bg: "#86efac" },
                        { color: "#fde047", label: "Yellow", border: "none", bg: "#fde047" },
                        { color: "#d8b4fe", label: "Purple", border: "none", bg: "#d8b4fe" },
                        { color: "#fdba74", label: "Orange", border: "none", bg: "#fdba74" },
                        { color: "#67e8f9", label: "Cyan", border: "none", bg: "#67e8f9" },
                      ].map((item) => (
                        <button
                          key={item.color}
                          onClick={() => applyCellBgColor(item.color)}
                          style={{
                            width: 28, height: 28,
                            border: (pendingCellBg !== null && pendingCellBg === item.color) ? "2px solid #1a56db" : item.border,
                            borderRadius: 4, background: item.bg,
                            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                          }}
                          title={item.label}
                        >
                          {item.color === "" && <span style={{ fontSize: 10, color: "#ef4444" }}>❌</span>}
                        </button>
                      ))}

                      {/* Custom color picker */}
                      <div style={{ position: "relative", width: 28, height: 28 }}>
                        <button
                          style={{
                            width: 28,
                            height: 28,
                            borderRadius: 4,
                            border: (pendingCellBg !== null && !["", "#d1d5db", "#93c5fd", "#fca5a5", "#86efac", "#fde047", "#d8b4fe", "#fdba74", "#67e8f9"].includes(pendingCellBg))
                              ? "2px solid #1a56db"
                              : "1px solid #d1d5db",
                            background: (pendingCellBg !== null && !["", "#d1d5db", "#93c5fd", "#fca5a5", "#86efac", "#fde047", "#d8b4fe", "#fdba74", "#67e8f9"].includes(pendingCellBg))
                              ? pendingCellBg
                              : "linear-gradient(135deg, #ff007f 0%, #7f00ff 50%, #00f0ff 100%)",
                            cursor: "pointer",
                            padding: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          title="Custom Color"
                        >
                          {(pendingCellBg === null || ["", "#d1d5db", "#93c5fd", "#fca5a5", "#86efac", "#fde047", "#d8b4fe", "#fdba74", "#67e8f9"].includes(pendingCellBg)) && (
                            <span style={{ fontSize: 14, color: "#fff", fontWeight: "bold", textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>+</span>
                          )}
                        </button>
                        <input
                          type="color"
                          value={pendingCellBg && pendingCellBg !== "" ? pendingCellBg : "#ffffff"}
                          onChange={(e) => applyCellBgColor(e.target.value)}
                          style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            height: "100%",
                            opacity: 0,
                            cursor: "pointer",
                          }}
                          title="Custom Color"
                        />
                      </div>
                    </div>

                    <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 6 }}>
                      <p style={{ margin: "0 0 4px", fontSize: 10, color: "#6b7280", fontWeight: 600 }}>Apply to</p>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          onClick={() => { applyCellBgToSelection(); setShowCellBgMenu(false); }}
                          disabled={pendingCellBg === null}
                          style={{
                            flex: 1, padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: 4,
                            background: pendingCellBg === null ? "#f3f4f6" : "#fff",
                            color: pendingCellBg === null ? "#9ca3af" : "#374151",
                            fontSize: 11,
                            cursor: pendingCellBg === null ? "not-allowed" : "pointer",
                          }}
                        >
                          Selected Cells
                        </button>
                        <button
                          onClick={() => { applyCellBgToAllCells(); setShowCellBgMenu(false); }}
                          disabled={pendingCellBg === null}
                          style={{
                            flex: 1, padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: 4,
                            background: pendingCellBg === null ? "#f3f4f6" : "#fff",
                            color: pendingCellBg === null ? "#9ca3af" : "#374151",
                            fontSize: 11,
                            cursor: pendingCellBg === null ? "not-allowed" : "pointer",
                          }}
                        >
                          Entire Table
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
          <Divider />

          {/* Image */}
          <ToolBtn disabled={!tb} onClick={() => imageInputRef.current?.click()} title="Insert Image">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ display: "block" }}>
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </ToolBtn>
          <input ref={imageInputRef} type="file" accept="image/*"
            style={{ display: "none" }} onChange={handleImageInsert} />

          {/* HR / Blockquote / Clear */}
          <ToolBtn disabled={!tb}
            onClick={() => editor.chain().focus().setHorizontalRule().run()} title="Horizontal Rule">—</ToolBtn>
          <ToolBtn disabled={!tb} active={editor.isActive("blockquote")}
            onClick={() => editor.chain().focus().toggleBlockquote().run()} title="Blockquote">❝</ToolBtn>
          <ToolBtn disabled={!tb}
            onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
            title="Clear Formatting">✗</ToolBtn>

          {/* Image resize handles overlay */}
          {selectedImage && !isResizing && (
            <div style={{ position: "relative" }}>
              <style>{`
              .resize-overlay {
                position: fixed;
                z-index: 9999;
                pointer-events: none;
              }
              .resize-handle {
                position: absolute;
                width: 10px;
                height: 10px;
                background: #1a56db;
                border: 2px solid #fff;
                border-radius: 2px;
                cursor: pointer;
                pointer-events: all;
              }
            `}</style>
              <div
                className="resize-overlay"
                style={{
                  left: selectedImage.getBoundingClientRect().left,
                  top: selectedImage.getBoundingClientRect().top,
                  width: selectedImage.getBoundingClientRect().width,
                  height: selectedImage.getBoundingClientRect().height,
                }}
              >
                <div className="resize-handle" style={{ top: -5, left: -5, cursor: 'nw-resize' }} onMouseDown={(e) => handleResizeStart(e, 'nw')} />
                <div className="resize-handle" style={{ top: -5, right: -5, cursor: 'ne-resize' }} onMouseDown={(e) => handleResizeStart(e, 'ne')} />
                <div className="resize-handle" style={{ bottom: -5, left: -5, cursor: 'sw-resize' }} onMouseDown={(e) => handleResizeStart(e, 'sw')} />
                <div className="resize-handle" style={{ bottom: -5, right: -5, cursor: 'se-resize' }} onMouseDown={(e) => handleResizeStart(e, 'se')} />
                <div className="resize-handle" style={{ top: '50%', left: -5, transform: 'translateY(-50%)', cursor: 'w-resize' }} onMouseDown={(e) => handleResizeStart(e, 'w')} />
                <div className="resize-handle" style={{ top: '50%', right: -5, transform: 'translateY(-50%)', cursor: 'e-resize' }} onMouseDown={(e) => handleResizeStart(e, 'e')} />
                <div className="resize-handle" style={{ top: -5, left: '50%', transform: 'translateX(-50%)', cursor: 'n-resize' }} onMouseDown={(e) => handleResizeStart(e, 'n')} />
                <div className="resize-handle" style={{ bottom: -5, left: '50%', transform: 'translateX(-50%)', cursor: 's-resize' }} onMouseDown={(e) => handleResizeStart(e, 's')} />
              </div>
            </div>
          )}
        </div>

        {/* ── Main layout: 60% editor | 40% preview ────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "60% 40%", flex: 1, overflow: "hidden" }}>

          {/* ─── LEFT: Editor column ───────────────────────────────────────── */}
          <div style={{
            borderRight: "1px solid #d1d5db",
            display: "flex", flexDirection: "column",
            overflow: "hidden", background: "#e8eaed",
          }}>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>

              {!tableInserted && (
                <div style={{
                  background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 6,
                  padding: "8px 14px", marginBottom: 12, fontSize: 12, color: "#92400e",
                  display: "flex", alignItems: "center", gap: 8,
                }}>
                  <span>⊞</span>
                  <span>
                    Click <strong>Insert Table</strong> (⊞) in the toolbar to start.
                    All formatting tools unlock once a table is added.
                  </span>
                </div>
              )}

              {/* A4 white page */}
              <div style={{
                background: "#fff", minHeight: "297mm", width: "210mm",
                maxWidth: "100%", margin: "0 auto", padding: "10mm 10mm",
                boxShadow: "0 2px 12px rgba(0,0,0,.15)", borderRadius: 2,
                boxSizing: "border-box", overflow: "hidden",
              }}>

                <style>{`
                .tiptap-editor { outline: none; font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; color: #111; width: 100%; max-width: 100%; box-sizing: border-box; overflow: hidden; }
                .tiptap-editor p { margin: 0 0 8px; }
                .tiptap-editor h1 { font-size: 20pt; font-weight: bold; margin: 16px 0 8px; }
                .tiptap-editor h2 { font-size: 16pt; font-weight: bold; margin: 14px 0 6px; }
                .tiptap-editor h3 { font-size: 13pt; font-weight: bold; margin: 12px 0 4px; }
                .tiptap-editor .ProseMirror table,
                .tiptap-editor table { border-collapse: collapse; width: 694px !important; max-width: 694px !important; min-width: 694px !important; margin: 6px 0; table-layout: fixed !important; box-sizing: border-box !important; }
                .tiptap-editor .ProseMirror table table,
                .tiptap-editor table table { width: 100% !important; max-width: 100% !important; min-width: 0 !important; margin: 0 !important; }
                .tiptap-editor .tableWrapper { width: 100% !important; max-width: 100% !important; overflow: visible !important; }
                .tiptap-editor table p { margin: 0; }
                .tiptap-editor th,
                .tiptap-editor td {
                  padding: 6px 10px;
                  vertical-align: top; background: transparent; font-weight: normal;
                  word-break: break-word;
                  overflow-wrap: break-word;
                  overflow: hidden;
                  box-sizing: border-box !important;
                }
                .tiptap-editor th:not([style*="border"]),
                .tiptap-editor td:not([style*="border"]) {
                  border: 1px solid #000000;
                }
                .tiptap-editor ul { padding-left: 24px; }
                .tiptap-editor ol { padding-left: 24px; }
                .tiptap-editor li { margin-bottom: 4px; }
                .tiptap-editor blockquote { border-left: 3px solid #2b579a; margin: 8px 0; padding-left: 12px; color: #555; font-style: italic; }
                .tiptap-editor hr { border: none; border-top: 1px solid #999; margin: 12px 0; }
                .tiptap-editor img { max-width: 100%; height: auto; margin: 8px 0; cursor: pointer; }
                .tiptap-editor img.selected {
                  outline: 2px solid #1a56db;
                  outline-offset: 2px;
                }
                .tiptap-editor mark { background: #fde68a; padding: 0 2px; border-radius: 2px; }
                .tiptap-editor a { color: #1a56db; text-decoration: underline; }
                .tiptap-editor .is-editor-empty:before { content: attr(data-placeholder); color: #aaa; pointer-events: none; float: left; height: 0; }
                .tiptap-editor table td,
                .tiptap-editor table th {
                  position: relative;
                  cursor: text;
                }
                /* Tiptap CellSelection visual highlight */
                .tiptap-editor td.selectedCell,
                .tiptap-editor th.selectedCell {
                  background: rgba(200, 200, 255, 0.4) !important;
                  outline: 2px solid #1a56db;
                  outline-offset: -2px;
                }
                .tiptap-editor .column-resize-handle,
                .column-resize-handle {
                  position: absolute !important;
                  right: 0;
                  top: 0;
                  bottom: 0;
                  width: 2px;
                  background: transparent;
                  cursor: ew-resize !important;
                  z-index: 20;
                  pointer-events: auto;
                }
                .tiptap-editor .column-resize-handle:hover,
                .column-resize-handle:hover {
                  background: #2b579a;
                }
                .tiptap-editor.resize-cursor,
                .resize-cursor {
                  cursor: ew-resize !important;
                }
                /* Row resize: active drag */
                body.is-resizing-row,
                body.is-resizing-row * {
                  cursor: row-resize !important;
                  user-select: none !important;
                }
                /* Row resize: hover indicator */
                body.is-hovering-row-border,
                body.is-hovering-row-border .tiptap-editor,
                body.is-hovering-row-border .tiptap-editor * {
                  cursor: row-resize !important;
                }
                /* Row resize handle bar */
                .row-resize-handle {
                  position: absolute;
                  left: 0;
                  right: 0;
                  height: 4px;
                  background: #2b579a;
                  opacity: 0;
                  z-index: 30;
                  pointer-events: none;
                  transition: opacity 0.15s;
                }
                .row-resize-handle.visible {
                  opacity: 1;
                }
                .row-resize-handle.bottom {
                  bottom: -2px;
                }
                .row-resize-handle.top {
                  top: -2px;
                }
              `}</style>
                <EditorContent
                  editor={editor}
                  className="tiptap-editor"
                  onClick={(e) => {
                    const target = e.target as HTMLElement;
                    if (target.tagName === 'IMG') {
                      target.classList.add('selected');
                      setSelectedImage(target as HTMLImageElement);
                    } else {
                      const editorEl = editor.view.dom;
                      editorEl.querySelectorAll('img.selected').forEach(img => img.classList.remove('selected'));
                    }
                  }}
                />
              </div>

            </div>
          </div>

          {/* ─── RIGHT: Preview ───────────────────────────────────────────── */}
          <div style={{
            overflowY: "auto", overflowX: "hidden", background: "#525659",
            padding: "24px 0",
            display: "flex", flexDirection: "column",
            alignItems: "center", gap: 0,
          }}>
            <div style={{
              color: "#d1d5db", fontSize: 11, letterSpacing: 1,
              textTransform: "uppercase", fontWeight: 600,
              alignSelf: "flex-start", marginLeft: 20, marginBottom: 16,
            }}>
              📄 Page Preview
            </div>

            <style>{PREVIEW_CSS}</style>

            {previewPages.length === 0 ? (
              <div style={{
                width: Math.round(PREVIEW_PAGE_WIDTH * 0.45),
                height: Math.round(PREVIEW_PAGE_HEIGHT * 0.45),
                margin: "0 auto",
                position: "relative",
                marginBottom: 20,
                flexShrink: 0
              }}>
                <div style={{
                  background: "#fff",
                  width: PREVIEW_PAGE_WIDTH,
                  height: PREVIEW_PAGE_HEIGHT,
                  transform: "scale(0.45)",
                  transformOrigin: "top left",
                  borderRadius: 2,
                  boxShadow: "0 4px 24px rgba(0,0,0,.5)",
                  display: "flex", alignItems: "center",
                  justifyContent: "center", color: "#ccc", fontSize: 20,
                  flexDirection: "column", gap: 10,
                  position: "absolute",
                  top: 0,
                  left: 0,
                }}>
                  <span style={{ fontSize: 48 }}>📄</span>
                  <span>No content yet</span>
                </div>
              </div>
            ) : (
              previewPages.map((pageHtml, idx) => (
                <div
                  key={idx}
                  style={{
                    width: Math.round(PREVIEW_PAGE_WIDTH * 0.45),
                    height: Math.round(PREVIEW_PAGE_HEIGHT * 0.45),
                    margin: "0 auto",
                    position: "relative",
                    marginBottom: 20,
                    flexShrink: 0
                  }}
                >
                  <div
                    style={{
                      background: "#fff",
                      width: PREVIEW_PAGE_WIDTH,
                      height: PREVIEW_PAGE_HEIGHT,
                      transform: "scale(0.45)",
                      transformOrigin: "top left",
                      padding: `${PREVIEW_PAD_V}px ${PREVIEW_PAD_H}px`,
                      boxSizing: "border-box",
                      overflow: "hidden",
                      boxShadow: "0 2px 18px rgba(0,0,0,.5)",
                      position: "absolute",
                      top: 0,
                      left: 0,
                      borderRadius: 2,
                    }}
                  >
                    <div className="pc" dangerouslySetInnerHTML={{ __html: pageHtml }} />
                    <div style={{
                      position: "absolute", bottom: 28, right: 36,
                      fontSize: "8pt", color: "#bbb", userSelect: "none",
                    }}>
                      {idx + 1} / {previewPages.length}
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Stats strip */}
            <div style={{
              background: "#3a3d40", borderRadius: 6, padding: "10px 16px",
              color: "#d1d5db", fontSize: 11, display: "flex", gap: 24,
              width: "calc(100% - 40px)", marginTop: 8, flexShrink: 0,
              boxSizing: "border-box"
            }}>
              <div>
                <div style={{ color: "#9ca3af", fontSize: 10 }}>WORDS</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#fff" }}>{wordCount}</div>
              </div>
              <div>
                <div style={{ color: "#9ca3af", fontSize: 10 }}>CHARACTERS</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#fff" }}>
                  {editor.storage.characterCount?.characters() ?? 0}
                </div>
              </div>
              <div>
                <div style={{ color: "#9ca3af", fontSize: 10 }}>PAGES</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#fff" }}>
                  {previewPages.length || 1}
                </div>
              </div>
            </div>
          </div>
        </div>


      </div>

      {/* Create Notice Modal */}
      <CreateNoticeModal
        visible={showCreateModal}
        onCancel={() => setShowCreateModal(false)}
        onSubmit={handleCreateModalSubmit}
        editTempalteData={editTempalteData}
      />
    </>
  );
}