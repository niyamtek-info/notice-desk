export async function addCommunicationLog(
  applicationId: string,
  channel: string,
  recipient: string,
  message: string,
  status: string = "success"
) {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/communication/applications/${applicationId}/communication-log`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel, recipient, message, status }),
      }
    );

    if (!res.ok) {
      console.error("❌ Communication log API failed:", await res.text());
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error("❌ Failed to add communication log:", err);
    return null;
  }
}