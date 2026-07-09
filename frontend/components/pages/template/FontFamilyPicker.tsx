import { useState, useRef, useEffect } from "react";

// Google Fonts URL mapping for fonts not guaranteed on all systems
const GOOGLE_FONTS_URL =
  "https://fonts.googleapis.com/css2?family=EB+Garamond&family=Libre+Baskerville&family=Palatino+Linotype&family=Book+Antiqua&family=Cambria&family=Constantia&family=Calibri&family=Trebuchet+MS&family=Segoe+UI&family=Courier+Prime&family=Cousine&family=Menlo&family=Lucida+Console&family=Comic+Sans+MS&family=Optima&display=swap";

// Map font names to CSS font-family stacks (with web-safe fallbacks)
const FONT_STACK: Record<string, string> = {
  // Serif
  "Times New Roman": "'Times New Roman', Times, serif",
  "Georgia": "Georgia, 'Libre Baskerville', serif",
  "Garamond": "Garamond, serif",
  "Palatino": "'Palatino Linotype', Palatino, serif",
  "Cambria": "Cambria, serif",
  "Didot": "Didot, serif",
  "Baskerville": "Baskerville, serif",
  "Playfair Display": "'Playfair Display', serif",
  "Merriweather": "'Merriweather', serif",
  "Libre Baskerville": "'Libre Baskerville', serif",
  "Lora": "'Lora', serif",
  "PT Serif": "'PT Serif', serif",

  // Sans-serif
  "Arial": "Arial, Helvetica, sans-serif",
  "Helvetica": "Helvetica, Arial, sans-serif",
  "Verdana": "Verdana, Geneva, sans-serif",
  "Tahoma": "Tahoma, Geneva, sans-serif",
  "Trebuchet MS": "'Trebuchet MS', Helvetica, sans-serif",
  "Segoe UI": "'Segoe UI', Tahoma, sans-serif",
  "Calibri": "Calibri, sans-serif",

  // Google Fonts (IMPORTANT: must import)
  "Roboto": "'Roboto', sans-serif",
  "Open Sans": "'Open Sans', sans-serif",
  "Lato": "'Lato', sans-serif",
  "Poppins": "'Poppins', sans-serif",
  "Inter": "'Inter', sans-serif",
  "Montserrat": "'Montserrat', sans-serif",
  "Nunito": "'Nunito', sans-serif",
  "Raleway": "'Raleway', sans-serif",
  "Ubuntu": "'Ubuntu', sans-serif",
  "Work Sans": "'Work Sans', sans-serif",
  "Fira Sans": "'Fira Sans', sans-serif",
  "Source Sans Pro": "'Source Sans Pro', sans-serif",
  "Quicksand": "'Quicksand', sans-serif",
  "Rubik": "'Rubik', sans-serif",

  // Monospace
  "Courier New": "'Courier New', Courier, monospace",
  "Consolas": "Consolas, monospace",
  "Monaco": "Monaco, monospace",
  "Lucida Console": "'Lucida Console', Monaco, monospace",
  "Fira Code": "'Fira Code', monospace",
  "Source Code Pro": "'Source Code Pro', monospace",
  "JetBrains Mono": "'JetBrains Mono', monospace",
  "Inconsolata": "'Inconsolata', monospace",

  // Stylish / Cursive
  "Comic Sans MS": "'Comic Sans MS', cursive",
  "Brush Script MT": "'Brush Script MT', cursive",
  "Pacifico": "'Pacifico', cursive",
  "Dancing Script": "'Dancing Script', cursive",
  "Lobster": "'Lobster', cursive",
  "Great Vibes": "'Great Vibes', cursive",
  "Satisfy": "'Satisfy', cursive",
  "Caveat": "'Caveat', cursive",
};

const FONT_GROUPS: { label: string; fonts: string[] }[] = [
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
  {
    label: "Serif",
    fonts: [
      "Times New Roman",
      "Georgia",
      "Garamond",
      "Palatino",
      "Cambria",
      "Didot",
      "Baskerville",
      "Playfair Display",
      "Merriweather",
      "Libre Baskerville",
      "Lora",
      "PT Serif",
    ],
  },
  {
    label: "Sans-serif",
    fonts: [
      "Arial",
      "Helvetica",
      "Verdana",
      "Tahoma",
      "Trebuchet MS",
      "Segoe UI",
      "Calibri",

      // Google Fonts (must import)
      "Roboto",
      "Open Sans",
      "Lato",
      "Poppins",
      "Inter",
      "Montserrat",
      "Nunito",
      "Raleway",
      "Ubuntu",
      "Work Sans",
      "Fira Sans",
      "Source Sans Pro",
      "Quicksand",
      "Rubik",
    ],
  },
  {
    label: "Monospace",
    fonts: [
      "Courier New",
      "Consolas",
      "Monaco",
      "Lucida Console",
      "Fira Code",
      "Source Code Pro",
      "JetBrains Mono",
      "Inconsolata",
    ],
  },
  {
    label: "Stylish",
    fonts: [
      "Comic Sans MS",
      "Brush Script MT",
      "Pacifico",
      "Dancing Script",
      "Lobster",
      "Great Vibes",
      "Satisfy",
      "Caveat",
    ],
  },
];

interface FontFamilyPickerProps {
  fontFamily: string;
  disabled?: boolean;
  onChange: (font: string) => void;
}

export default function FontFamilyPicker({ fontFamily, disabled = false, onChange }: FontFamilyPickerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Inject Google Fonts <link> once into document <head>
  useEffect(() => {
    const id = "font-picker-gfonts";
    if (document.getElementById(id)) return;
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = GOOGLE_FONTS_URL;
    document.head.appendChild(link);
  }, []);

  // Close on outside click (capture phase so stopPropagation inside dropdown doesn't block it)
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler, true);
    return () => document.removeEventListener("mousedown", handler, true);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  const stack = (font: string) => FONT_STACK[font] ?? font;

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block", width: 140 }}>

      {/* Trigger button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((o) => !o)}
        style={{
          width: "100%", height: 26, fontSize: 12,
          border: "1px solid #d1d5db", borderRadius: 4,
          padding: "0 22px 0 6px", background: "#fff",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.38 : 1,
          textAlign: "left", whiteSpace: "nowrap",
          overflow: "hidden", textOverflow: "ellipsis",
          position: "relative", boxSizing: "border-box", outline: "none",
        }}
      >
        {/* fontFamily applied on inner span so it actually renders */}
        <span style={{ fontFamily: stack(fontFamily), fontSize: 12 }}>{fontFamily}</span>
        <svg style={{ position: "absolute", right: 5, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
          width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 3.5L5 6.5L8 3.5" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          onScroll={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            position: "absolute", top: "calc(100% + 2px)", left: 0, zIndex: 9999,
            background: "#fff", border: "1px solid #d1d5db", borderRadius: 4,
            boxShadow: "0 4px 12px rgba(0,0,0,0.12)", width: 200,
            maxHeight: 280, overflowY: "auto",
          }}
        >
          {FONT_GROUPS.map((group) => (
            <div key={group.label}>
              <div style={{
                padding: "5px 8px 3px", fontSize: 12, fontWeight: 700,
                color: "#2B579A", textTransform: "uppercase", letterSpacing: "0.05em",
                fontFamily: "system-ui, sans-serif", borderTop: "1px solid #f3f4f6", marginTop: 2,
              }}>
                {group.label}
              </div>

              {group.fonts.map((font) => {
                const isSelected = font === fontFamily;
                return (
                  <div
                    key={font}
                    ref={(el) => {
                        if (el) {
                        // Sets font-family with !important directly on the DOM node
                        el.style.setProperty("font-family", stack(font), "important");
                        }
                    }}
                    onClick={() => { onChange(font); setOpen(false); }}
                    style={{
                      padding: "5px 10px", fontSize: 13,
                      cursor: "pointer",
                      background: isSelected ? "#eff6ff" : "transparent",
                      color: isSelected ? "#1d4ed8" : "#111827",
                      fontWeight: isSelected ? 600 : 400,
                    }}
                    onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "#f9fafb"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = isSelected ? "#eff6ff" : "transparent"; }}
                  >
                    {font}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}