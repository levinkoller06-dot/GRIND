export type ChatImage = { mime_type: "image/jpeg"; data: string; preview: string };

/** Verkleinert ein Foto auf max. `maxSize` px und gibt es als JPEG (base64) zurück. */
export async function prepareImage(file: File, maxSize = 1024): Promise<ChatImage> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxSize / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  const preview = canvas.toDataURL("image/jpeg", 0.8);
  return { mime_type: "image/jpeg", data: preview.split(",")[1], preview };
}
