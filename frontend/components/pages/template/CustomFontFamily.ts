import { Extension } from "@tiptap/core";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    fontFamily: {
      setFontFamily: (fontFamily: string) => ReturnType;
      unsetFontFamily: () => ReturnType;
    };
  }
}

export const CustomFontFamily = Extension.create({
  name: "fontFamily",

  addGlobalAttributes() {
    return [
      {
        types: ["textStyle"],
        attributes: {
          fontFamily: {
            default: null,
            parseHTML: element => element.style.fontFamily,
            renderHTML: attributes => {
              if (!attributes.fontFamily) {
                return {};
              }

              // Quote font names that contain spaces
              const fontFamily = attributes.fontFamily.includes(' ') 
                ? `"${attributes.fontFamily}"` 
                : attributes.fontFamily;

              return {
                style: `font-family: ${fontFamily}`,
              };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontFamily:
        (family: string) =>
        ({ chain, state }) => {
          const { from, to } = state.selection;
          const currentFontSize = state.selection.$from.marks().find(m => m.type.name === 'textStyle')?.attrs.fontSize;
          
          // Preserve existing fontSize while setting fontFamily
          return chain()
            .setMark("textStyle", { fontSize: currentFontSize || null, fontFamily: family })
            .run();
        },
    };
  },
});
