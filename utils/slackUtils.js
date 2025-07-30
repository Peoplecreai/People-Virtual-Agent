// Normalizador de Slack ID equivalente al de tu Python
export function normalizeSlackId(value) {
  if (!value) return "";
  let v = String(value).trim();

  // <@U…|alias>
  if (v.startsWith("<@") && v.endsWith(">")) {
    v = v.slice(2, -1);
    if (v.includes("|")) v = v.split("|")[0];
  }

  // URL -> último segmento
  if (v.startsWith("https://")) {
    const parts = v.replace(/\/$/, "").split("/");
    v = parts[parts.length - 1];
  }

  // 'T……-U……' (como en tu sheet)
  if (v.includes("T05NRU10WAW-")) {
    const rest = v.split("T05NRU10WAW-")[1];
    if (rest) v = rest.trim();
  }
  if (v.includes("-")) {
    // split en el primer '-'
    const split = v.split("-", 2);
    if (split.length === 2 && split[1].startsWith("U")) v = split[1];
  }

  // Si queda algo como 'Txxx Uxxx' o 'xxxUxxxx', toma desde la U
  const uPos = v.indexOf("U");
  if (uPos > 0) v = v.slice(uPos);

  // Quita cualquier espacio sobrante
  return v.trim();
}

export async function getSlackName(slackId) {
  try {
    const { app } = await import('../src/app.js');
    const sid = normalizeSlackId(slackId);
    const { user } = await app.client.users.info({ user: slackId });
    const profile = user.profile || {};
    return profile.display_name || profile.real_name;
  } catch (error) {
    console.error(`Failed to fetch Slack profile: ${error.message}`);
    return null;
  }
}
