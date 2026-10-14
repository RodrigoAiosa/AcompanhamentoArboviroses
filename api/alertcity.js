/**
 * Proxy para a API pública do InfoDengue (Fiocruz).
 *
 * O navegador não consegue chamar info.dengue.mat.br diretamente em todos os
 * casos (CORS), então o index.html consulta /api/alertcity e esta função
 * repassa a requisição, valida os parâmetros e devolve o JSON com cache de 6h
 * na CDN da Vercel.
 *
 * Documentação da API: https://info.dengue.mat.br/services/api/doc
 */
const BASE_URL = "https://info.dengue.mat.br/api/alertcity";
const DOENCAS = new Set(["dengue", "chikungunya", "zika"]);

module.exports = async (req, res) => {
  const q = req.query || {};
  const geocode = String(q.geocode || "");
  const doenca = String(q.disease || "dengue");
  const anoAtual = new Date().getFullYear();
  const anoInicio = parseInt(q.ey_start, 10) || anoAtual - 1;
  const anoFim = parseInt(q.ey_end, 10) || anoAtual;

  if (!/^\d{7}$/.test(geocode)) {
    return res.status(400).json({ erro: "geocode inválido (use o código IBGE de 7 dígitos)" });
  }
  if (!DOENCAS.has(doenca)) {
    return res.status(400).json({ erro: "doença inválida (dengue, chikungunya ou zika)" });
  }
  if (anoInicio < 2010 || anoFim > anoAtual + 1 || anoInicio > anoFim) {
    return res.status(400).json({ erro: "período inválido" });
  }

  const params = new URLSearchParams({
    geocode,
    disease: doenca,
    format: "json",
    ew_start: "1",
    ew_end: "52",
    ey_start: String(anoInicio),
    ey_end: String(anoFim),
  });

  let ultimoErro = null;
  for (let tentativa = 0; tentativa < 2; tentativa++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      const resp = await fetch(`${BASE_URL}?${params}`, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (compatible; PainelArboviroses/1.0; +https://acompanhamentoarboviroses.vercel.app)",
          Accept: "application/json",
        },
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!resp.ok) {
        ultimoErro = `HTTP ${resp.status}`;
        if (resp.status === 429 || resp.status >= 500) {
          await new Promise((r) => setTimeout(r, 600 * (tentativa + 1)));
          continue;
        }
        return res.status(resp.status).json({ erro: ultimoErro });
      }

      const texto = await resp.text();
      let dados;
      try {
        dados = JSON.parse(texto || "[]");
      } catch {
        // A API responde texto quando não há série para o município/doença.
        dados = [];
      }

      res.setHeader("Cache-Control", "public, s-maxage=21600, stale-while-revalidate=86400");
      return res.status(200).json(Array.isArray(dados) ? dados : []);
    } catch (e) {
      ultimoErro = e.name === "AbortError" ? "timeout" : "erro de conexão";
      await new Promise((r) => setTimeout(r, 600 * (tentativa + 1)));
    }
  }

  return res.status(502).json({ erro: ultimoErro || "falha ao consultar o InfoDengue" });
};
