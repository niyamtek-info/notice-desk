/**
 * Compresses a base64 image string by resizing it and adjusting quality.
 * @param base64Str The original base64 string (including data:image/...;base64, prefix)
 * @param maxWidth The maximum width of the output image (default: 1024px)
 * @param quality The JPEG quality from 0 to 1 (default: 0.7)
 * @returns A promise that resolves to the compressed base64 string
 */
export const compressBase64Image = (
    base64Str: string,
    maxWidth = 1024,
    quality = 0.7
): Promise<string> => {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.src = base64Str;
        img.onload = () => {
            const canvas = document.createElement("canvas");
            let width = img.width;
            let height = img.height;

            if (width > maxWidth) {
                height = Math.round((height * maxWidth) / width);
                width = maxWidth;
            }

            canvas.width = width;
            canvas.height = height;

            const ctx = canvas.getContext("2d");
            if (!ctx) {
                reject(new Error("Could not get canvas context"));
                return;
            }

            ctx.drawImage(img, 0, 0, width, height);

            // Compress to JPEG with specified quality
            const compressedDataUrl = canvas.toDataURL("image/jpeg", quality);
            resolve(compressedDataUrl);
        };
        img.onerror = (err) => {
            reject(err);
        };
    });
};
