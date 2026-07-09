// "use client"

// import React, { useState, useRef, useEffect, useCallback } from 'react';
// import draftToHtml from 'draftjs-to-html';
// import htmlToDraft from 'html-to-draftjs';
// import { Editor } from 'react-draft-wysiwyg';
// import 'react-draft-wysiwyg/dist/react-draft-wysiwyg.css';
// import { EditorState, ContentState, convertToRaw, convertFromHTML, convertFromRaw } from 'draft-js';

// interface RichTextWordEditorProps {
//   value?: string;
//   onChange?: (value: string) => void;
//   placeholder?: string;
//   disabled?: boolean;
//   applicationNumber?: string;
//   title?: string;
//   desData?: string;
// }

// const RichTextWordEditor: React.FC<RichTextWordEditorProps> = ({
//   value = '',
//   onChange,
//   placeholder = 'Enter description here...',
//   disabled = false,
//   applicationNumber,
//   title = 'Description of Schedule Property',
//   desData = ""
// }) => {
//   const [loading, setLoading] = useState(false);
//   const [editorState, setEditorState] = useState(() => EditorState.createEmpty());
//   const editorRef = useRef<any>(null);


//   const lastValueRef = useRef<string | null>(null);

//   useEffect(() => {
//     if (value !== lastValueRef.current) {
//       lastValueRef.current = value;

//       if (value) {
//         const blocksFromHTML = htmlToDraft(value);
//         const contentState = ContentState.createFromBlockArray(
//           blocksFromHTML.contentBlocks,
//           blocksFromHTML.entityMap
//         );

//         setEditorState(EditorState.createWithContent(contentState));
//       } else {
//         setEditorState(EditorState.createEmpty());
//       }
//     }
//   }, [desData]);


//   // Debounced onChange to prevent performance issues and backspace problems
//   const debouncedOnChange = useCallback(
//     (newEditorState: EditorState) => {
//       if (onChange) {
//         const contentState = newEditorState.getCurrentContent();
//         const rawContentState = convertToRaw(contentState);
//         const htmlContent = draftToHtml(rawContentState);
//         onChange(htmlContent);
//       }
//     },
//     [onChange]
//   );

//   const handleEditState = (newEditorState: EditorState) => {
//     setEditorState(newEditorState);
//     debouncedOnChange(newEditorState);
//   }

//   const editorToolbar = {
//     options: ['inline', 'blockType', 'list', 'textAlign', 'colorPicker', 'history'],
//     inline: {
//       inDropdown: false,
//       className: undefined,
//       component: undefined,
//       dropdownClassName: undefined,
//       options: ['bold', 'italic', 'underline', 'strikethrough'],
//       bold: { className: 'border-0' },
//       italic: { className: 'border-0' },
//       underline: { className: 'border-0' },
//       strikethrough: { className: 'border-0' },
//     },
//     blockType: {
//       inDropdown: true,
//       options: ['Normal', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'Blockquote'],
//     },
//     list: {
//       inDropdown: false,
//       options: ['unordered', 'ordered'],
//     },
//     textAlign: {
//       inDropdown: true,
//       options: ['left', 'center', 'right', 'justify'],
//     },
//     colorPicker: {
//       className: undefined,
//       component: undefined,
//       popupClassName: undefined,
//       colors: ['rgb(97,189,109)', 'rgb(26,188,156)', 'rgb(85,85,85)', 'rgb(46,125,50)', 'rgb(29,78,216)', 'rgb(211,47,47)', 'rgb(0,0,0)'],
//     },
//     history: {
//       inDropdown: false,
//       options: ['undo', 'redo'],
//     },
//   };

//   return (
//     <div className="rich-text-word-editor-container">
//       <div className="border rounded-lg border-gray-300 bg-white">
//         <div>
//           {!disabled ? (
//             <Editor
//               ref={editorRef}
//               editorState={editorState}
//               onEditorStateChange={handleEditState}
//               toolbar={editorToolbar}
//               wrapperClassName="wrapper-class"
//               editorClassName="editor-class min-h-[100px] max-h-[400px] overflow-auto px-3"
//               toolbarClassName="toolbar-class !border-b !z-[0]  !border-b-gray-300 !rounded-tl-lg !rounded-tr-lg !bg-transparent"
//               placeholder={placeholder}
//             />
//           ) : (
//             <div
//               className="editor-class min-h-[100px] max-h-[400px] overflow-auto p-3"
//               dangerouslySetInnerHTML={{ __html: value }}
//             />
//           )}
//         </div>
//       </div>
//     </div>
//   );
// };

// export default RichTextWordEditor;