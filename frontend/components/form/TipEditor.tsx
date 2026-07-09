"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { TextStyle } from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import { FontSize } from "./FontSize";
import { Underline as UnderlineExtension } from "@tiptap/extension-underline";
import { Tooltip } from 'antd';

import { useEffect } from "react";

interface Props {
  value?: string;
  onChange?: (value: string) => void;
}

export default function TiptapEditor({ value = "", onChange }: Props) {

  const editor = useEditor({
    extensions: [
      StarterKit,
      TextStyle,
      FontSize,
      FontSize.configure({
      types: ["textStyle"],
    }),
      Underline,
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
    ],

    content: value || "<p></p>",

    editorProps: {
      attributes: {
        class:
          "min-h-[150px] focus:outline-none",
      },
    },

    onUpdate({ editor }) {
      const html = editor.getHTML();
      onChange?.(html);
    },

    immediatelyRender: false,
  });


  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value?.replace(/<ins[^>]*>/g, '<u>')?.replace(/<\/ins>/g, '</u>') || "<p></p>");
    }
  }, [value, editor]);

  if (!editor) return null;
  

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow duration-200" style={{ height: ["",null,undefined].includes(value) ? '200px' : '350px', display: 'flex', flexDirection: 'column' }}>

      {/* Toolbar */}
      <div className="flex gap-2 border-b border-gray-100 bg-gray-50/50 p-2 flex-wrap rounded-t-lg sticky top-0 z-10" style={{ backgroundColor: 'white' }}>

<button
  onClick={() => editor.chain().focus().toggleBold().run()}
  className="toolbar-btn bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded px-3 py-1 text-sm font-semibold transition-colors"
>
  <Tooltip title="Bold">
    B
  </Tooltip>
</button>

<button
  onClick={() => editor.chain().focus().toggleItalic().run()}
  className="toolbar-btn bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded px-3 py-1 text-sm font-semibold italic transition-colors"
>
  <Tooltip title="Italic">
    I
  </Tooltip>
</button>

<button
  onClick={() => editor.chain().focus().toggleUnderline().run()}
  className="toolbar-btn bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded px-3 py-1 text-sm font-semibold transition-colors"
>
  <Tooltip title="Underline">
    U
  </Tooltip>
</button>

        {/* Font Size H1-H3 Styles */}
<button
  onClick={() => {
        const currentSize = editor.getAttributes("textStyle").fontSize;
        if (currentSize === "32px") {
          editor.chain().focus().setFontSize("14px").run();
        } else {
          editor.chain().focus().setFontSize("32px").run();
        }
  }}
  className="toolbar-btn bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded px-3 py-1 text-sm font-bold text-blue-700 transition-colors"
>
  <Tooltip title="Font Size H1">
    H1
  </Tooltip>
</button>

<button
 onClick={() => {
      const currentSize = editor.getAttributes("textStyle").fontSize;
      if (currentSize === "26px") {
        editor.chain().focus().setFontSize("14px").run();
      } else {
        editor.chain().focus().setFontSize("26px").run();
      }
 }}
  className="toolbar-btn bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded px-3 py-1 text-sm font-bold text-blue-700 transition-colors"
>
  <Tooltip title="Font Size H2">
    H2
  </Tooltip>
</button>

<button
onClick={() => {
      const currentSize = editor.getAttributes("textStyle").fontSize;
      if (currentSize === "20px") {
        editor.chain().focus().setFontSize("14px").run();
      } else {
        editor.chain().focus().setFontSize("20px").run();
      }
}}
  className="toolbar-btn bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded px-3 py-1 text-sm font-bold text-blue-700 transition-colors"
>
  <Tooltip title="Font Size H3">
    H3
  </Tooltip>
</button>

        {/* Lists */}
<button
  onClick={() => editor.chain().focus().toggleBulletList().run()}
  className="toolbar-btn bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded px-3 py-1 text-sm transition-colors font-bold"
>
  <Tooltip title="Bullet List">
    •
  </Tooltip>
</button>

<button
  onClick={() => editor.chain().focus().toggleOrderedList().run()}
  className="toolbar-btn bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded px-3 py-1 text-sm transition-colors font-bold"
>
  <Tooltip title="Numbered List">
    123
  </Tooltip>
</button>

        {/* Alignment */}
<button
  onClick={() => editor.chain().focus().setTextAlign("left").run()}
  className="toolbar-btn bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded px-3 py-1 text-sm transition-colors font-bold"
>
  <Tooltip title="Align Left">
    ←
  </Tooltip>
</button>

<button
  onClick={() => editor.chain().focus().setTextAlign("center").run()}
  className="toolbar-btn bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded px-3 py-1 text-sm transition-colors font-bold"
>
  <Tooltip title="Align Center">
    ↔
  </Tooltip>
</button>

<button
  onClick={() => editor.chain().focus().setTextAlign("right").run()}
  className="toolbar-btn bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded px-3 py-1 text-sm transition-colors font-bold"
>
  <Tooltip title="Align Right">
    →
  </Tooltip>
</button>

      </div>

      {/* Editor */}

      <EditorContent
        editor={editor}
        className={`p-1 min-h-[350px] focus:outline-none overflow-auto ProseMirror`}
        style={{
          lineHeight: '1.6',
          color: '#374151',
          border: "none",
          flex: '1',
          maxHeight: 'calc(100% - 60px)'
        }}
      />

    </div>
  );
}