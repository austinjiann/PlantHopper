import { NextRequest, NextResponse } from "next/server";

async function fetchBase64(url: string): Promise<string | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const buffer = Buffer.from(await res.arrayBuffer());
    return `data:image/jpeg;base64,${buffer.toString("base64")}`;
  } catch {
    return null;
  }
}

export async function POST(req: NextRequest) {
  try {
    const { plantId, species, soilMoisture, wateringFrequency, imageUrl } = await req.json();
    if (!plantId) {
      return NextResponse.json({ tips: [] }, { status: 200 });
    }

    const imageBase64 = imageUrl ? await fetchBase64(imageUrl) : null;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ tips: [] }, { status: 200 });
    }

    const prompt = `You are a plant care assistant.
Return exactly TWO tips, one sentence each, specific to the plant.
Use species if given; otherwise infer from the image cautiously.
Reference provided soil moisture (%) and watering frequency when helpful.
No preludes; output just two lines starting with "- ". If confidence is low, respond with NO_TIPS.

Species: ${species ?? "Unknown"}
Soil moisture: ${soilMoisture ?? "Unknown"}%
Watering frequency: ${wateringFrequency ?? "Unknown"}`;

    const body: any = {
      contents: [
        {
          parts: [
            { text: prompt },
            ...(imageBase64 ? [{ inlineData: { mimeType: "image/jpeg", data: imageBase64.split(",")[1] } }] : [])
          ]
        }
      ]
    };

    const resp = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + encodeURIComponent(apiKey), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!resp.ok) {
      return NextResponse.json({ tips: [] }, { status: 200 });
    }
    const data = await resp.json();
    const text: string = data?.candidates?.[0]?.content?.parts?.map((p: any) => p?.text).join("\n") ?? "";

    if (!text || /\bNO_TIPS\b/i.test(text)) {
      return NextResponse.json({ tips: [] }, { status: 200 });
    }

    // Extract up to 2 bullets; enforce one sentence per tip
    const lines = text
      .split(/\n+/)
      .map((l: string) => l.replace(/^[-•\*]\s*/, "").trim())
      .filter(Boolean)
      .slice(0, 2)
      .map((l: string) => {
        const m = l.match(/.*?[\.\!\?](\s|$)/);
        return (m ? m[0] : l).trim();
      });

    return NextResponse.json({ tips: lines }, { status: 200 });
  } catch (e) {
    return NextResponse.json({ tips: [] }, { status: 200 });
  }
}


